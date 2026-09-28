"""An RS485 reply never holds loop() while it goes out on the wire.

Measured on nong 67, 2026-09-21, with PERF?: the hub polled the board's status
over the RS485 dongle, and every poll froze loop() for 116 ms - a 1.3 KB INFO
reply at 115200 baud, sent inline by RS485Bus::send, which waits in
Serial2.flush() until the last bit is out. loop() drives the 50 Hz servo
frames, so a moving arm stopped for six frames at every poll (135 ms gap seen).

The fix keeps the wire timing that check_rs485_turnaround guards, and moves
only the waiting: send() puts a copy on a queue and returns; a task of its own
(rs485tx) takes lines off in order and calls sendNow(), which is the old body.

What this holds:
  * send() never touches Serial2 or flush() itself when the queue exists;
  * the queue is created and the task started in begin();
  * the task calls sendNow and frees the copy;
  * a full queue waits a bounded time, never portMAX_DELAY - a stuck bus
    must not freeze the loop the fix exists to protect.
"""
import re

import qc as F

AREA = "connection"
TITLE = "an RS485 reply does not freeze the servo loop"


def _body(code, sig):
    m = re.search(re.escape(sig) + r"[^)]*\)\s*\{", code)
    if not m:
        return ""
    i, depth = m.end(), 1
    while i < len(code) and depth:
        depth += (code[i] == "{") - (code[i] == "}")
        i += 1
    return code[m.end():i]


def run(t):
    code = (F.FIRMWARE / "src" / "core" / "RS485Bus.cpp").read_text(encoding="utf-8")
    code = re.sub(r"//.*", "", code)

    send = _body(code, "void RS485Bus::send(")
    t.ok(send, "RS485Bus::send exists")
    t.ok("xQueueSend" in send, "send() queues the line")
    t.ok("Serial2" not in send.split("xQueueSend")[-1] and "flush" not in send,
         "send() never writes or waits on the wire itself",
         "that wait is the 116 ms freeze measured on nong 67")
    t.ok(send.count("sendNow(") ==
         len(re.findall(r"if \(!txq_\)\s*\{\s*sendNow\(", send)),
         "send() calls the blocking writer only when there is no queue",
         "an unguarded sendNow in send() is the inline wait again")
    t.ok("portMAX_DELAY" not in send,
         "a full queue waits a bounded time",
         "portMAX_DELAY would freeze loop() whenever the bus is stuck")

    begin = _body(code, "void RS485Bus::begin(")
    t.ok("xQueueCreate" in begin and "xTaskCreate" in begin,
         "begin() creates the queue and starts the sender task")

    now = _body(code, "void RS485Bus::sendNow(")
    t.ok("Serial2.flush" not in now and "uart_wait_tx_done" in now,
         "the wire wait sleeps (uart_wait_tx_done), it does not spin",
         "Serial2.flush() in core 2.0.17 busy-waits on tx idle: moved to a "
         "task it still ate the CPU for 116 ms - measured on nong 67")
    t.ok(re.search(r"setTxBufferSize\(\s*\d+\s*\);\s*Serial2\.begin", begin),
         "a TX ring buffer is set, before begin()",
         "after begin() the call is ignored and print() waits for FIFO room")
    t.ok(re.search(r'xTaskCreatePinnedToCore\(txTask, "rs485tx", \d+, this, 1,', begin),
         "the sender task runs at loop()'s priority, not above it",
         "above it, any wait that spins starves the servo frames")

    # Both found by the Codex review 2026-09-21.
    t.ok("vQueueDelete(txq_)" in begin and "txq_ = nullptr" in begin,
         "if the sender task cannot start, the queue goes and send() blocks as before",
         "a queue with no task behind it swallows every frame without a word")
    router = (F.FIRMWARE / "src" / "core" / "CommandRouter.cpp").read_text(encoding="utf-8")
    main = (F.FIRMWARE / "src" / "main.cpp").read_text(encoding="utf-8")
    reboot = router[router.index('LOGF(sys, "rebooting...")'):]
    reboot = reboot[:reboot.index("ESP.restart()")]
    t.ok("beforeReboot()" in reboot and "rs485.drain(" in main,
         "a reboot first lets queued RS485 replies leave",
         "FWEND's OK is queued, not sent; a restart that does not wait cuts it off")

    task = _body(code, "void RS485Bus::txTask(")
    t.ok("sendNow(" in task and "delete" in task,
         "the task sends each line with sendNow and frees the copy",
         "without the delete every reply leaks its String")
