// Host harness for firmware/src/core/SeqScan.h (check_seq_stream).
// argv: <file> <bytes per read>. Prints COUNT, HEADER, every ITEM (escaped),
// the largest item and sizeof(SeqScan), for the check to compare.
#include "core/SeqScan.h"
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <sstream>

struct FileSource : SeqSource {
    std::string data;
    size_t chunk = 512;
    long reads = 0;
    int read(uint32_t off, uint8_t* buf, size_t len) override {
        reads++;
        if (off >= data.size()) return 0;
        size_t n = len < chunk ? len : chunk;   // a short read, like a slow card
        if (n > data.size() - off) n = data.size() - off;
        for (size_t i = 0; i < n; i++) buf[i] = (uint8_t)data[off + i];
        return (int)n;
    }
};

static std::string esc(const std::string& s) {
    std::string o;
    for (char c : s) {
        if (c == '\n') o += "\\n"; else if (c == '\\') o += "\\\\"; else o += c;
    }
    return o;
}

int main(int argc, char** argv) {
    if (argc < 3) return 2;
    FileSource src;
    std::ifstream f(argv[1], std::ios::binary);
    std::stringstream ss;
    ss << f.rdbuf();
    src.data = ss.str();
    src.chunk = (size_t)atoi(argv[2]);
    SeqScan scan;
    std::string header, err, item;
    if (!scan.index(src, header, err)) { printf("ERR %s\n", err.c_str()); return 0; }
    printf("COUNT %zu\n", scan.count());
    printf("HEADER %s\n", esc(header).c_str());
    size_t biggest = 0, seen = 0;
    while (scan.next(src, item)) {
        printf("ITEM %s\n", esc(item).c_str());
        if (item.size() > biggest) biggest = item.size();
        seen++;
    }
    printf("FAILED %d\n", scan.failed() ? 1 : 0);
    scan.rewind();
    printf("REWIND %d\n", scan.next(src, item) ? 1 : 0);
    printf("FIRST %s\n", esc(item).c_str());
    printf("SEEN %zu\nBIGGEST %zu\nSIZEOF %zu\nREADS %ld\n", seen, biggest, sizeof(SeqScan), src.reads);
    return 0;
}
