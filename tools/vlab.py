"""Encoder lab: statistics of codec variants on the real frames (docs/rozhodnuti.md). Standard library only;
a row of the picture is a Python int (bit x = pixel x, 1 = white).

Usage: python tools/vlab.py [W H] [--dz N] [--lag 1|2] [--pol]
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import frames  # noqa: E402

THR = bytes((b'1' if v >= 128 else b'0')[0] for v in range(256))


def rows_of(data, i, w, h):
    f = data[i * w * h:(i + 1) * w * h].translate(THR)
    return [int(f[y * w:(y + 1) * w][::-1], 2) for y in range(h)]


def runs(d):
    """Runs of ones in d: list of (start, end) (end exclusive), ascending."""
    s = d & ~(d << 1)
    e = ~d & (d << 1)
    out = []
    while s:
        lo = s & -s
        a = lo.bit_length() - 1
        rest = e >> a
        b = a + ((rest & -rest).bit_length() - 1)
        out.append((a, b))
        s ^= lo
    return out


def deadzone(d, dz):
    if dz <= 0:
        return d
    for a, b in runs(d):
        if b - a <= dz:
            d &= ~(((1 << (b - a)) - 1) << a)
    return d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('wh', nargs='*', type=int, default=[256, 192])
    ap.add_argument('--dz', type=int, default=0)
    ap.add_argument('--lag', type=int, default=2)
    ap.add_argument('--pol', action='store_true')
    ap.add_argument('--step', type=int, default=1)
    a = ap.parse_args()
    w, h = a.wh
    n, data = frames.load(w, h)
    full = (1 << w) - 1
    k_max = frames.demo_frames(n)
    hist = [[0] * h for _ in range(a.lag)]      # logical pictures of the last frames (L)
    pol = 0
    stats = []
    for k in range(0, k_max, a.step):
        img = rows_of(data, frames.source_index(k), w, h)
        prev = hist[-1]
        page = hist[-a.lag]
        best = None
        for p in ((0, 1) if a.pol else (0,)):
            cand = [r ^ (full if p else 0) for r in img]
            # dead zone against the previous logical picture
            new = [prev[y] ^ deadzone(prev[y] ^ cand[y], a.dz) for y in range(h)]
            cost = sum(len(runs(page[y] ^ new[y])) for y in range(h))
            if best is None or cost < best[0]:
                best = (cost, p, new)
        cost, p, new = best
        # statistics of the intervals against the page
        nrows = 0
        niv = 0
        nvert = 0
        nbytes = 0
        prev_iv = []
        for y in range(h):
            iv = runs(page[y] ^ new[y])
            if not iv:
                prev_iv = []
                continue
            nrows += 1
            niv += len(iv)
            for j, (s, e) in enumerate(iv):
                nbytes += ((e - 1) >> 2) - (s >> 2) + 1
                if j < len(prev_iv):
                    ps, pe = prev_iv[j]
                    if abs(s - ps) <= 1 and abs((e - s) - (pe - ps)) <= 1:
                        nvert += 1
            prev_iv = iv
        stats.append((nrows, niv, nvert, nbytes, p != pol))
        pol = p
        hist.append(new)
        hist.pop(0)
    m = len(stats)

    def q(col):
        v = sorted(s[col] for s in stats)
        return f'median {v[m // 2]} p90 {v[m * 9 // 10]} p99 {v[m * 99 // 100]} max {v[-1]} sum {sum(v)}'
    print(f'{w}x{h} lag {a.lag} dz {a.dz} pol {a.pol}: {m} frames, polarity flips {sum(s[4] for s in stats)}')
    print('  rows   ', q(0))
    print('  ivs    ', q(1))
    print('  vert   ', q(2))
    print('  bytes  ', q(3))
    tot_iv = sum(s[1] for s in stats)
    tot_v = sum(s[2] for s in stats)
    tot_r = sum(s[0] for s in stats)
    # size model: changed row ~ 1 B (skip + count), interval 1.5 B, vertically predicted 0.5 B
    size = tot_r * 1.0 + (tot_iv - tot_v) * 1.5 + tot_v * 0.5
    print(f'  vert fraction {tot_v / tot_iv:.2f}; size model {size / 1e6:.2f} MB (plain 1.5 B/iv: '
          f'{(tot_r + tot_iv * 1.5) / 1e6:.2f} MB) per frame {size / m:.0f} B')


if __name__ == '__main__':
    main()
