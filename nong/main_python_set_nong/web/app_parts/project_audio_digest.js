// SHA-256 fallback for local HTTP/LAN where WebCrypto is not a secure context.
// Used only for file identity; no keys, passwords or transport authentication.
class StudioAudioDigest {
  static portable(bytes) {
    const primes = [];
    for (let n = 2; primes.length < 64; n++) if (!primes.some(p => p * p <= n && n % p === 0)) primes.push(n);
    const fraction = x => Math.floor((x - Math.floor(x)) * 4294967296) >>> 0;
    const state = primes.slice(0, 8).map(p => fraction(Math.sqrt(p)));
    const constants = primes.map(p => fraction(Math.cbrt(p)));
    const size = Math.ceil((bytes.length + 9) / 64) * 64, padded = new Uint8Array(size);
    padded.set(bytes); padded[bytes.length] = 128;
    const view = new DataView(padded.buffer), bitLength = bytes.length * 8;
    view.setUint32(size - 8, Math.floor(bitLength / 4294967296)); view.setUint32(size - 4, bitLength >>> 0);
    const rotate = (x, n) => (x >>> n) | (x << (32 - n)), words = new Uint32Array(64);
    for (let offset = 0; offset < size; offset += 64) {
      for (let i = 0; i < 16; i++) words[i] = view.getUint32(offset + i * 4);
      for (let i = 16; i < 64; i++) {
        const a = words[i - 15], b = words[i - 2];
        words[i] = (words[i - 16] + (rotate(a, 7) ^ rotate(a, 18) ^ (a >>> 3)) + words[i - 7] + (rotate(b, 17) ^ rotate(b, 19) ^ (b >>> 10))) >>> 0;
      }
      let [a, b, c, d, e, f, g, h] = state;
      for (let i = 0; i < 64; i++) {
        const t1 = (h + (rotate(e, 6) ^ rotate(e, 11) ^ rotate(e, 25)) + ((e & f) ^ (~e & g)) + constants[i] + words[i]) >>> 0;
        const t2 = ((rotate(a, 2) ^ rotate(a, 13) ^ rotate(a, 22)) + ((a & b) ^ (a & c) ^ (b & c))) >>> 0;
        h = g; g = f; f = e; e = (d + t1) >>> 0; d = c; c = b; b = a; a = (t1 + t2) >>> 0;
      }
      [a, b, c, d, e, f, g, h].forEach((x, i) => { state[i] = (state[i] + x) >>> 0; });
    }
    return state.map(x => x.toString(16).padStart(8, '0')).join('');
  }
  static async sha256(bytes) {
    if (window.crypto && crypto.subtle) return Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', bytes)), b => b.toString(16).padStart(2, '0')).join('');
    return this.portable(bytes);
  }
}
