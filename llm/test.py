import torch
import asyncio
import hashlib
import os
import re
import json
import threading
import tempfile
import numpy as np
import sounddevice as sd
import soundfile as sf
from difflib import SequenceMatcher
from faster_whisper import WhisperModel
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
import edge_tts

# --- CONFIGURATION ---
MODEL_ID = "Qwen/Qwen3.5-4B"
VOICE = "th-TH-PremwadeeNeural"
FAQ_FILE = "qa_data.json"
TTS_CACHE_DIR = "tts_cache"
FAQ_THRESHOLD = 0.75
SAMPLE_RATE = 16000
WHISPER_MODEL = "small"   # small / medium / large-v3

os.makedirs(TTS_CACHE_DIR, exist_ok=True)

# ตัด thinking block ของ Qwen3 (<think>...</think>)
THINK_RE = re.compile(r'<think>.*?</think>', re.DOTALL)

print("[*] กำลังโหลดระบบ...")

# --- LOAD FAQ ---
def load_faq(path: str) -> list[dict]:
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("faqs", [])

def build_faq_context(faqs: list[dict]) -> str:
    """สร้าง text สรุป FAQ ทั้งหมดให้ LLM อ่าน"""
    lines = []
    for i, item in enumerate(faqs, 1):
        q_sample = item["questions"][0]
        lines.append(f"{i}. คำถาม: {q_sample}\n   คำตอบ: {item['answer']}")
    return "\n".join(lines)

def find_faq_answer(user_input: str, faqs: list[dict]) -> str | None:
    """Fuzzy match — คืนคำตอบถ้าคล้ายเกิน threshold"""
    user_clean = user_input.strip().lower()
    best_score = 0.0
    best_answer = None
    for item in faqs:
        for q in item["questions"]:
            score = SequenceMatcher(None, user_clean, q.strip().lower()).ratio()
            if score > best_score:
                best_score = score
                best_answer = item["answer"]
    if best_score >= FAQ_THRESHOLD:
        print(f"[FAQ] ตรงกับคำถามที่ตั้งไว้ (score={best_score:.2f})")
        return best_answer
    return None

# --- VOICE INPUT (Push-to-Talk) ---
def record_voice() -> str | None:
    input("\033[93m[กด Enter เพื่อเริ่มพูด...]\033[0m")
    print("\033[91m[กำลังฟัง...] กด Enter เพื่อหยุดพูด\033[0m", flush=True)

    audio_chunks = []
    stop_event = threading.Event()

    def audio_callback(indata, _frames, _time_info, _status):
        if not stop_event.is_set():
            audio_chunks.append(indata.copy())

    stream = sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="float32", callback=audio_callback)
    stream.start()
    input()
    stop_event.set()
    stream.stop()
    stream.close()

    if not audio_chunks:
        return None

    audio_data = np.concatenate(audio_chunks, axis=0).flatten()
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_path = tmp.name
    sf.write(tmp_path, audio_data, SAMPLE_RATE)

    print("[*] กำลังถอดเสียงเป็นข้อความ...")
    segments, _ = whisper_model.transcribe(
        tmp_path, language="th", beam_size=5,
        vad_filter=True, vad_parameters={"min_silence_duration_ms": 500}
    )
    os.unlink(tmp_path)

    text = " ".join(seg.text for seg in segments).strip()
    return text if text else None

# --- LLM GENERATE (ตัด thinking ก่อน return) ---
def llm_generate(messages: list[dict]) -> str:
    # enable_thinking=False บอก Qwen3 ไม่ต้องคิดออกมา (ถ้า model รองรับ)
    try:
        input_text = tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True, enable_thinking=False
        )
    except TypeError:
        input_text = tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )

    inputs = tokenizer([input_text], return_tensors="pt").to(model.device)

    with torch.no_grad():
        output_ids = model.generate(
            **inputs,
            max_new_tokens=512,
            do_sample=True,
            temperature=0.7,
            top_p=0.9,
            repetition_penalty=1.1,
            pad_token_id=tokenizer.eos_token_id
        )

    response_ids = output_ids[0][len(inputs.input_ids[0]):]

    # decode โดยไม่ skip special tokens เพื่อให้ regex เห็น <think>...</think>
    full_response = tokenizer.decode(response_ids, skip_special_tokens=False)

    # ตัด thinking block ออก
    answer = THINK_RE.sub('', full_response)
    # ตัด special tokens ที่เหลือ เช่น <|im_end|> <|endoftext|>
    answer = re.sub(r'<\|[^|]+\|>', '', answer).strip()

    print(f"\033[92mAI: \033[0m{answer}")
    return answer

# --- TTS ---
def _tts_cache_path(text: str) -> str:
    key = hashlib.md5(text.encode("utf-8")).hexdigest()
    return os.path.join(TTS_CACHE_DIR, f"{key}.mp3")

async def _tts_generate(text: str, out_path: str) -> bool:
    """สร้างไฟล์เสียง คืน True ถ้าสำเร็จ"""
    for attempt in range(3):
        try:
            communicate = edge_tts.Communicate(text, VOICE, boundary="WordBoundary")
            await communicate.save(out_path)
            return True
        except edge_tts.exceptions.NoAudioReceived:
            if attempt < 2:
                await asyncio.sleep(1.5 * (attempt + 1))
    return False

async def prebuild_faq_audio(faqs: list[dict]):
    """Sync cache กับ FAQ ปัจจุบัน: generate ที่ขาด, ลบที่เกิน"""
    print("[TTS] กำลัง sync เสียง FAQ...")

    # hash ของทุก answer ที่ควรมี
    valid_filenames = set()
    for item in faqs:
        answer = item["answer"]
        cache_path = _tts_cache_path(answer)
        valid_filenames.add(os.path.basename(cache_path))

    # ลบไฟล์ที่ไม่มีใน FAQ แล้ว
    for fname in os.listdir(TTS_CACHE_DIR):
        if fname.endswith(".mp3") and fname not in valid_filenames:
            os.remove(os.path.join(TTS_CACHE_DIR, fname))
            print(f"[TTS] ลบ cache เก่า: {fname}")

    # generate เฉพาะที่ยังไม่มี
    for item in faqs:
        answer = item["answer"]
        cache_path = _tts_cache_path(answer)
        if os.path.exists(cache_path):
            print(f"[TTS] ใช้ cache: {answer[:35]}...")
            continue
        ok = await _tts_generate(answer, cache_path)
        if ok:
            print(f"[TTS] สร้างใหม่: {answer[:35]}...")
        else:
            print(f"[TTS] ไม่สามารถสร้างเสียงได้: {answer[:35]}...")
    print("[TTS] sync เสร็จสิ้น\n")

async def say_text(text: str):
    clean = THINK_RE.sub('', text)
    clean = re.sub(r'[*#_`]', '', clean).strip()
    if not clean:
        return

    cache_path = _tts_cache_path(clean)
    if os.path.exists(cache_path):
        os.system(f"mpg123 -q {cache_path} > /dev/null 2>&1")
        return

    print("[TTS] กำลังสร้างเสียงตอบกลับ...")
    ok = await _tts_generate(clean, cache_path)
    if ok:
        os.system(f"mpg123 -q {cache_path} > /dev/null 2>&1")
    else:
        print("[TTS] ไม่สามารถสร้างเสียงได้ในขณะนี้ (ข้ามการพูด)")

# --- LOAD MODELS ---
print("[*] กำลังโหลด Whisper STT...")
whisper_model = WhisperModel(
    WHISPER_MODEL,
    device="cuda" if torch.cuda.is_available() else "cpu",
    compute_type="float16" if torch.cuda.is_available() else "int8"
)

print("[*] กำลังโหลด Qwen LLM...")
quant_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_compute_dtype=torch.float16,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_use_double_quant=True
)
tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, trust_remote_code=True)
model = AutoModelForCausalLM.from_pretrained(
    MODEL_ID,
    quantization_config=quant_config,
    device_map="auto",
    trust_remote_code=True
)

# --- MAIN ---
def main():
    print("\n" + "="*50)
    print("  Voice AI - พูดคุยด้วยเสียง (FAQ + LLM)")
    print("  Ctrl+C เพื่อปิดโปรแกรม")
    print("="*50 + "\n")

    faqs = load_faq(FAQ_FILE)
    faq_context = build_faq_context(faqs)
    print(f"[*] โหลด FAQ สำเร็จ: {len(faqs)} หมวดหมู่คำถาม\n")

    asyncio.run(prebuild_faq_audio(faqs))

    history = []

    while True:
        user_msg = record_voice()
        if user_msg is None:
            print("[!] ไม่ได้ยินเสียง กรุณาลองใหม่\n")
            continue

        print(f"\033[94mคุณพูดว่า: {user_msg}\033[0m")

        if user_msg.strip() in ['exit', 'quit', 'ออก', 'ปิด']:
            print("[*] ปิดโปรแกรม")
            break

        # 1) Fuzzy match ก่อน — เร็วที่สุด
        faq_answer = find_faq_answer(user_msg, faqs)
        if faq_answer:
            print(f"\033[92mAI (FAQ): {faq_answer}\033[0m\n")
            asyncio.run(say_text(faq_answer))
            history += [{"role": "user", "content": user_msg},
                        {"role": "assistant", "content": faq_answer}]
            continue

        # 2) ให้ LLM อ่าน FAQ แล้วหาคำตอบที่ใกล้เคียง
        #    ถ้าไม่มีใน FAQ ให้ตอบเองตามปกติ
        system_with_faq = (
            "คุณคือผู้ช่วยอัจฉริยะ ตอบเป็นภาษาไทย สั้นกระชับ\n\n"
            "ข้อมูล FAQ ที่มีอยู่:\n"
            f"{faq_context}\n\n"
            "ถ้าคำถามเกี่ยวข้องกับ FAQ ข้างต้น ให้ตอบตาม FAQ นั้นโดยตรง "
            "ถ้าไม่เกี่ยวข้องกับ FAQ เลย ให้ตอบตามความรู้ของคุณตามปกติ"
        )

        messages = [{"role": "system", "content": system_with_faq}]
        messages += history
        messages.append({"role": "user", "content": user_msg})

        answer = llm_generate(messages)

        history += [{"role": "user", "content": user_msg},
                    {"role": "assistant", "content": answer}]
        asyncio.run(say_text(answer))
        print()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[!] ปิดโปรแกรม")
    except Exception as e:
        print(f"\n[!] เกิดข้อผิดพลาด: {e}")
        raise
