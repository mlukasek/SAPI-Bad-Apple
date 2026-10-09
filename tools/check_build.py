"""Checks of the memory layout of build/badapple.com (symbols from build/badapple.sym)."""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def symbols(path=os.path.join(ROOT, 'build', 'badapple.sym')):
    out = {}
    for line in open(path):
        m = re.match(r'(\S+)\s+EQU\s+0*([0-9A-F]+)H', line)
        if m:
            out[m.group(1)] = int(m.group(2), 16)
    return out


def main():
    s = symbols()
    errors = []
    if s['PROGRAM_END'] > 0x1000:
        errors.append(f'program up to {s["PROGRAM_END"]:04X}h, over the decoder handlers (1000h)')
    if s['VDEC_TOP'] > s['vfill']:
        errors.append(f'decoder handlers up to {s["VDEC_TOP"]:04X}h, into vfill ({s["vfill"]:04X}h)')
    if s['vfill_end'] > s['MUS_RING']:
        errors.append(f'vfill up to {s["vfill_end"]:04X}h, into the music ring ({s["MUS_RING"]:04X}h)')
    if s['MUS_RING_END'] > s['STACK_TOP'] - 0x100:
        errors.append(f'music ring up to {s["MUS_RING_END"]:04X}h, into the stack')
    if errors:
        sys.exit('\n'.join(errors))
    print(f'layout ok: program to {s["PROGRAM_END"]:04X}h, handlers to {s["VDEC_TOP"]:04X}h')


if __name__ == '__main__':
    main()
