#pragma once
// Reads a block-style sequence file ONE STEP AT A TIME, so the board never
// holds a whole show in memory. Pure C++ (no Arduino), so QC compiles and runs
// it on the PC (check_seq_stream).
//
// Why (lab 2026-10-28, nong 67): MOVE of a 30 KB show (447 poses) parsed the
// whole file into one JsonDocument inside the web request; the board reset
// (reset=CRASH) and 2 KB files played fine. Now MOVE only scans the lines once
// (header keys + where the steps are) and each step is parsed when it is due.
//
//   name: x          <- header lines (any top-level key, before or after steps)
//   steps:
//     - pose: "..."  <- one item = the dash line + the lines indented under it
//       wait: 100
#include <stddef.h>
#include <stdint.h>
#include <string>

// Where the bytes come from: the SD card, or a sequence held in RAM.
struct SeqSource {
    virtual ~SeqSource() {}
    // up to len bytes at off; 0 past the end, -1 on a read error
    virtual int read(uint32_t off, uint8_t* buf, size_t len) = 0;
};

class SeqScan {
public:
    static const size_t BUF = 512;        // one SD read per refill
    static const size_t MAX_LINE = 1024;  // a pose line is ~70 chars

    // One pass over the file. header gets every line outside `steps:`.
    bool index(SeqSource& src, std::string& header, std::string& err) {
        reset();
        header.clear();
        bool inSteps = false, sawSteps = false;
        std::string s;
        uint32_t at = 0;
        for (;;) {
            int r = line(src, at, s);
            if (r < 0) { err = r == -2 ? "a line is too long" : "read error"; return false; }
            if (r == 0) break;
            int ind = indentOf(s);
            bool blank = isBlank(s, ind);
            if (inSteps) {
                if (blank) continue;
                if (indent_ < 0 && isDash(s, ind)) { indent_ = ind; count_++; continue; }
                if (indent_ >= 0 && ind > indent_) continue;
                if (indent_ >= 0 && ind == indent_ && isDash(s, ind)) { count_++; continue; }
                if (ind > 0) { err = "steps: is not a list of - items"; return false; }
                inSteps = false;                  // a top-level key ends the list
                end_ = at;
            }
            if (!blank && ind == 0 && isStepsKey(s)) {
                if (sawSteps) { err = "two steps: lists"; return false; }
                size_t i = 6;
                while (i < s.size() && s[i] == ' ') i++;
                if (i < s.size() && s[i] != '#') {
                    // flow style `steps: [...]`: nothing here writes it, and
                    // reading it would mean parsing the whole list at once again
                    err = "steps must be one - item per line";
                    return false;
                }
                sawSteps = inSteps = true;
                start_ = pos_;
                continue;
            }
            header += s;
            header += '\n';
        }
        if (inSteps) end_ = pos_;
        if (!sawSteps) { err = "no steps"; return false; }
        cur_ = start_;
        return true;
    }

    // The next step's text, dedented ("- pose: ...\n  wait: 1\n").
    // false at the end of the list (or on a read error: see failed()).
    bool next(SeqSource& src, std::string& item) {
        item.clear();
        failed_ = false;
        if (cur_ >= end_ || indent_ < 0) return false;
        seek(cur_);
        bool started = false;
        std::string s;
        uint32_t at = 0;
        for (;;) {
            int r = line(src, at, s);
            if (r < 0) { failed_ = true; return false; }
            if (r == 0 || at >= end_) { cur_ = end_; break; }
            int ind = indentOf(s);
            if (isBlank(s, ind)) continue;
            if (ind == indent_ && isDash(s, ind)) {
                if (started) { cur_ = at; break; }
                started = true;
            }
            if (!started) continue;
            item.append(s, (size_t)indent_, std::string::npos);
            item += '\n';
        }
        return started;
    }

    void rewind() { cur_ = start_; }
    size_t count() const { return count_; }
    bool failed() const { return failed_; }

private:
    uint8_t buf_[BUF];
    uint32_t bufOff_ = 0;
    size_t bufLen_ = 0;
    uint32_t pos_ = 0;
    uint32_t start_ = 0, end_ = 0, cur_ = 0;
    int indent_ = -1;
    size_t count_ = 0;
    bool failed_ = false;

    void reset() {
        bufOff_ = 0; bufLen_ = 0; pos_ = 0;
        start_ = end_ = cur_ = 0; indent_ = -1; count_ = 0; failed_ = false;
    }
    // keep the buffer when the offset is inside it: most steps need no read
    void seek(uint32_t off) { pos_ = off; }

    // 1 = a line (s, starting at byte at), 0 = end of file, -1 read error,
    // -2 line longer than MAX_LINE
    int line(SeqSource& src, uint32_t& at, std::string& s) {
        at = pos_;
        s.clear();
        for (;;) {
            if (bufLen_ == 0 || pos_ < bufOff_ || pos_ >= bufOff_ + bufLen_) {
                int n = src.read(pos_, buf_, BUF);
                if (n < 0) return -1;
                if (n == 0) { bufLen_ = 0; return pos_ > at ? 1 : 0; }
                bufOff_ = pos_;
                bufLen_ = (size_t)n;
            }
            char c = (char)buf_[pos_ - bufOff_];
            pos_++;
            if (c == '\n') return 1;
            if (c == '\r') continue;
            if (s.size() >= MAX_LINE) return -2;
            s += c;
        }
    }
    static int indentOf(const std::string& s) {
        int i = 0;
        while (i < (int)s.size() && s[i] == ' ') i++;
        return i;
    }
    static bool isBlank(const std::string& s, int ind) {
        return ind >= (int)s.size() || s[ind] == '#';
    }
    static bool isDash(const std::string& s, int ind) {
        return s[ind] == '-' && (ind + 1 == (int)s.size() || s[ind + 1] == ' ');
    }
    static bool isStepsKey(const std::string& s) {
        return s.compare(0, 6, "steps:") == 0;
    }
};

// A sequence held in RAM (FBEGIN/FEND text): same scanner, no card.
struct SeqTextSource : SeqSource {
    const char* text = nullptr;
    size_t len = 0;
    int read(uint32_t off, uint8_t* buf, size_t n) override {
        if (off >= len) return 0;
        if (n > len - off) n = len - off;
        for (size_t i = 0; i < n; i++) buf[i] = (uint8_t)text[off + i];
        return (int)n;
    }
};
