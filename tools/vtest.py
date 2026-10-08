"""Check the Z80 video decoder (sapi/video.asm + sapi/gen/vdec.asm) in the Z80 model against the reference
decoder of tools/vcodec.py: every frame of the stream is decoded by both, the pages must be equal; the measured
T-states (with the waits of CGA-1V measured on the real HW) are compared with the cycle model of the encoder.

Usage: python tools/vtest.py [--frames N] [--stream build/video.bin]
       (without --stream the first N frames are encoded first; build/vtest.com is assembled by build.cmd)
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, 'z80'))
import vcodec  # noqa: E402
import vfmt  # noqa: E402
from sapi import SapiV, CGA_WAIT_HW  # noqa: E402

FRAME = 0x4000


def frame_cycles(body):
    """Cycle model of the encoder for a body (without reading from the RAM disk)."""
    pos = 0
    cyc = 0
    while True:
        k = vfmt.OPS[body[pos]][0]
        if k == 'END':
            return cyc + vcodec.op_cost(body[pos:pos + 1])
        if k == 'CLR':
            cyc += vcodec.clr_cost(body[pos + 3])
            pos += 5
            continue
        n = {'TRACKA': 3, 'TRACKR': 2, 'MX': 2}.get(k, 1)
        cyc += vcodec.op_cost(body[pos:pos + n])
        pos += n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--frames', type=int, default=200)
    ap.add_argument('--stream')
    ap.add_argument('--nowait', action='store_true', help='without the waits of CGA-1V (like SAPIemu)')
    a = ap.parse_args()
    if a.stream:
        stream = open(a.stream, 'rb').read()
    else:
        stream, _ = vcodec.encode(a.frames, verbose=False)
    m = SapiV()
    m.load_com(os.path.join(ROOT, 'build', 'vtest.com'))
    if not a.nowait:
        m.cga_wait = CGA_WAIT_HW
    ref = [bytearray(vcodec.PAGE), bytearray(vcodec.PAGE)]
    pos = 0
    n = 0
    worst = 0
    tot_meas = tot_model = 0
    while stream[pos] and n < a.frames:
        start = pos + 1
        end = vcodec.decode_frame(stream, start, ref[n & 1])
        body = stream[start:end]
        m.ram[FRAME:FRAME + len(body)] = body
        m.cfg = (n & 1) << 1                     # CPU page
        cpu = m.cpu
        cpu.pc = 0x100
        cpu.halted = False
        cpu.iff1 = cpu.iff2 = 0
        c0 = cpu.cycles
        m.run(10_000_000, check=lambda c: c.halted)
        if not cpu.halted:
            sys.exit(f'frame {n}: did not finish')
        meas = cpu.cycles - c0 - 72              # minus the test frame (ld sp, out, ld bc, call, halt)
        model = frame_cycles(body)
        tot_meas += meas
        tot_model += model
        worst = max(worst, abs(meas - model))
        if m.cga[n & 1] != ref[n & 1]:
            diff = [i for i in range(vcodec.PAGE) if m.cga[n & 1][i] != ref[n & 1][i]]
            sys.exit(f'frame {n}: page differs at {len(diff)} bytes, first C000h+{diff[0]:04X}h')
        n += 1
        pos = end
    print(f'{n} frames equal to the reference; T measured {tot_meas} model {tot_model:.0f} '
          f'({100 * (tot_meas / tot_model - 1):+.2f} %), worst frame {worst:.0f} T')


if __name__ == '__main__':
    main()
