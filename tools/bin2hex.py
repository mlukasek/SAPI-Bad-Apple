"""Binary image (the RAM disk, 4 MB) -> Intel HEX for loading into ZRD-1V: before every 64 KB an extended linear
address record (:02000004XXXXCC), data in records of 32 B (all of them, also empty areas), :00000001FF at the
end, CRLF. The same format as the RAM disk images of the author (work/ukazka_RAM_disku).

Usage: python tools/bin2hex.py [IN.bin [OUT.hex]]   (default build/ramdisk.bin -> build/ramdisk.hex)
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RECORD = 32


def record(addr, rtype, data):
    b = bytes([len(data), addr >> 8, addr & 0xFF, rtype]) + data
    return ':' + b.hex().upper() + f'{(-sum(b)) & 0xFF:02X}'


def to_hex(data):
    lines = []
    for seg in range(0, len(data), 0x10000):
        lines.append(record(0, 4, (seg >> 16).to_bytes(2, 'big')))
        for a in range(seg, min(seg + 0x10000, len(data)), RECORD):
            lines.append(record(a & 0xFFFF, 0, data[a:a + RECORD]))
    lines.append(record(0, 1, b''))
    return '\r\n'.join(lines) + '\r\n'


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'build', 'ramdisk.bin')
    dst = sys.argv[2] if len(sys.argv) > 2 else os.path.splitext(src)[0] + '.hex'
    data = open(src, 'rb').read()
    open(dst, 'w', newline='').write(to_hex(data))
    print(f'{dst}: {len(data)} B in {(len(data) + 0xFFFF) // 0x10000} parts of 64 KB')


if __name__ == '__main__':
    main()
