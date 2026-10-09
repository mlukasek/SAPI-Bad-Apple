"""Run BADAPPLE in SAPIemu (MCP, tools/emu/sapiemu.cmd): boot CP/M from the RAM disk, start the demo, take
screenshots of CGA-1V at given times and report the counters of the program (frames, late frames, VBIs).

Usage: python tools/emu/run_demo.py [--at 5,10,30] [--out work/shots] [--wav work/demo.wav] [--to-end]
"""
import argparse
import base64
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import sapimcp as sm  # noqa: E402
import cpm  # noqa: E402
from check_build import symbols  # noqa: E402


def read(addr, n):
    """Bytes from the memory (read_memory gives a hex dump: 'AAAA: xx xx ...  text', 16 per line)."""
    out = bytearray()
    for line in sm.call('read_memory', address=addr, length=n).splitlines():
        if ':' in line:
            out += bytes.fromhex(line.split(':', 1)[1][:49].strip())
    return bytes(out[:n])


def word(addr):
    b = read(addr, 2)
    return b[0] | b[1] << 8


def counters(sym):
    c = {k: word(sym[k]) for k in ('frame_cnt', 'late_cnt', 'vbi_cnt')}
    if 'mus_vbi' in sym:
        c['mus_vbi'] = read(sym['mus_vbi'], 1)[0]          # VBIs the music player is behind
    return c


def screenshot(path):
    r = sm.call('screenshot', display='CGA-1V')
    items = r if isinstance(r, list) else [r]
    for it in items:
        if isinstance(it, dict) and it.get('data'):
            open(path, 'wb').write(base64.b64decode(it['data']))
            return
    raise RuntimeError(f'no image: {str(r)[:200]}')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--at', default='3,10,30')
    ap.add_argument('--out', default=os.path.join(ROOT, 'work', 'shots'))
    ap.add_argument('--wav')
    ap.add_argument('--to-end', action='store_true')
    a = ap.parse_args()
    sym = symbols()
    os.makedirs(a.out, exist_ok=True)
    cpm.boot()                     # fresh: the state may hold an old RAM disk image
    sm.call('resume')
    sm.call('type_text', text='BADAPPLE\r')
    sm.call('run_for', ms=300)
    if a.wav:
        sm.call('audio_record', start=True)
    t = 0.3
    for at in [float(x) for x in a.at.split(',') if x]:
        sm.call('run_for', ms=int((at - t) * 1000))
        t = at
        sm.call('pause')
        p = os.path.join(a.out, f'shot_{at:06.1f}.png')
        screenshot(p)
        print(f'{at:6.1f} s: {counters(sym)}  {p}', flush=True)
        sm.call('resume')
    if a.to_end:
        for _ in range(5):                      # run_until takes at most 120 s
            r = sm.call('run_until', address=sym['exit'], timeout_ms=120000)
            if r.get('reason') != 'timeout' and r.get('stopped') != 'timeout':
                break
        print('end:', counters(sym), r)
    sm.call('pause')
    if a.wav:
        print('audio:', sm.call('audio_record', file=os.path.abspath(a.wav)))


if __name__ == '__main__':
    main()
