"""BADAPPLE.DAT: the data of the demo for the RAM disk (docs/format.md), standard library only.

Layout (offsets in the file; the file lies from 10000h of the RAM disk, block 8):
   0: 'BADAPPL1'
   8: video offset (3 B, 256-aligned), 11: video length (3 B)
  14: music offset (3 B, 256-aligned), 17: music length (3 B)
The video stream (tools/vcodec.py) is placed so that no frame crosses a 32 KB boundary of the stream (the
ring buffer of the program): before such a frame comes FFh and the frame starts at the next boundary.

Usage: python tools/mkdat.py [--video build/video.bin] [--music build/music.bin] [--out build/BADAPPLE.DAT]
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import vfmt  # noqa: E402

RING = 0x8000
MAX_DAT = (1016 - 8) * 4096        # blocks 8..1015 of the RAM disk


def pack_video(stream):
    out = bytearray()
    pos = 0
    nframes = 0
    while stream[pos]:
        end = vfmt.body_end(stream, pos + 1)
        frame = stream[pos:end]
        assert len(frame) < 4096, f'frame {nframes}: {len(frame)} B'
        rest = RING - len(out) % RING
        if rest < len(frame) + 1:          # +1: room for the end marker after the last frame
            out.append(0xFF)
            out += bytes(rest - 1)
        out += frame
        pos = end
        nframes += 1
    out.append(0)
    return out, nframes


def align(b, n=256):
    return b + bytes(-len(b) % n)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--video', default=os.path.join(ROOT, 'build', 'video.bin'))
    ap.add_argument('--music')
    ap.add_argument('--out', default=os.path.join(ROOT, 'build', 'BADAPPLE.DAT'))
    a = ap.parse_args()
    video, nframes = pack_video(open(a.video, 'rb').read())
    music = open(a.music, 'rb').read() if a.music else b''
    hdr = bytearray(b'BADAPPL1')
    v_off = 256
    m_off = v_off + len(align(bytes(video)))
    for v in (v_off, len(video), m_off, len(music)):
        hdr += v.to_bytes(3, 'little')
    dat = align(bytes(hdr)) + align(bytes(video)) + align(music)
    if len(dat) > MAX_DAT:
        sys.exit(f'BADAPPLE.DAT {len(dat)} B > {MAX_DAT} B')
    open(a.out, 'wb').write(dat)
    print(f'{a.out}: {len(dat)} B ({100 * len(dat) / MAX_DAT:.1f} % of the RAM disk), '
          f'video {len(video)} B {nframes} frames, music {len(music)} B')


if __name__ == '__main__':
    main()
