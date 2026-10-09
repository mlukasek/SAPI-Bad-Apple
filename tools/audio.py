"""Audio analysis helpers for the transcription of the soundtrack (stdlib only).

decode(): mono samples of any file ffmpeg reads. Spectrum: magnitudes of a Hann-windowed real FFT. Salience:
harmonic sum of the spectrum at the semitones of a range (a pitch is strong when its harmonics are).
"""
import array
import cmath
import math
import subprocess


def decode(path, rate, channels=1):
    """Float samples (-1..1) at a rate: one array, or a list of arrays per channel."""
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-vn', '-ac', str(channels), '-ar', str(rate), '-f',
                          's16le', '-'], capture_output=True, check=True).stdout
    a = array.array('h')
    a.frombytes(raw[:len(raw) // (2 * channels) * 2 * channels])
    if channels == 1:
        return array.array('f', (x / 32768.0 for x in a))
    return [array.array('f', (x / 32768.0 for x in a[c::channels])) for c in range(channels)]


def whiten(mags, width=1.12):
    """Peaks of a spectrum: sqrt magnitude minus its mean over [k/width, k*width], at least 0."""
    lm = [math.sqrt(v) for v in mags]
    cum = [0.0]
    for v in lm:
        cum.append(cum[-1] + v)
    out = []
    n = len(lm)
    for k, v in enumerate(lm):
        a = max(0, int(k / width))
        b = min(n, int(k * width) + 2)
        out.append(max(0.0, v - (cum[b] - cum[a]) / (b - a)))
    return out


class Spectrum:
    """Magnitude spectrum of n real samples (n a power of two), Hann window; bin k = k * rate / n Hz."""

    def __init__(self, n):
        self.n = n
        m = n // 2
        self.m = m
        bits = m.bit_length() - 1
        self.rev = [int(format(i, f'0{bits}b')[::-1], 2) for i in range(m)]
        self.tw = [cmath.exp(-2j * math.pi * k / m) for k in range(m // 2)]
        self.post = [cmath.exp(-2j * math.pi * k / n) for k in range(m)]
        self.win = [0.5 - 0.5 * math.cos(2 * math.pi * (i + 0.5) / n) for i in range(n)]

    def mags(self, x, start):
        """|X[k]| for k < n/2 of x[start:start+n] (zeros outside x)."""
        n, m, w = self.n, self.m, self.win
        seg = x[max(0, start):start + n]
        if start < 0:
            seg = array.array('f', [0.0] * (-start)) + seg
        if len(seg) < n:
            seg = seg + array.array('f', [0.0] * (n - len(seg)))
        # pack: z[i] = x[2i] + j x[2i+1], FFT of m points, then split into the spectrum of x
        rev = self.rev
        z = [complex(seg[2 * i] * w[2 * i], seg[2 * i + 1] * w[2 * i + 1]) for i in rev]
        size, tw = 2, self.tw
        while size <= m:
            half = size // 2
            step = m // size
            tws = tw[::step][:half]
            for s in range(0, m, size):
                for k in range(half):
                    i = s + k
                    t = tws[k] * z[i + half]
                    z[i + half] = z[i] - t
                    z[i] = z[i] + t
            size *= 2
        out = [0.0] * m
        post = self.post
        z0 = z[0]
        out[0] = abs(z0.real + z0.imag)
        for k in range(1, m):
            a, b = z[k], z[m - k].conjugate()
            e = (a + b) * 0.5
            o = (a - b) * -0.5j
            out[k] = abs(e + post[k] * o)
        return out


def key_freq(key):
    return 440.0 * 2 ** ((key - 69) / 12)


class Salience:
    """Harmonic-sum salience of the semitones lo..hi from a magnitude spectrum (Spectrum.mags)."""

    def __init__(self, n, rate, lo, hi, harmonics=6, decay=0.8):
        self.lo, self.hi = lo, hi
        self.table = []
        for key in range(lo, hi + 1):
            parts = []
            for h in range(1, harmonics + 1):
                f = key_freq(key) * h
                a = f * 2 ** (-0.4 / 12) * n / rate
                b = f * 2 ** (0.4 / 12) * n / rate
                k0, k1 = max(1, int(math.floor(a))), int(math.ceil(b))
                if k1 >= n // 2:
                    break
                parts.append((k0, k1 + 1, decay ** (h - 1)))
            self.table.append(parts)

    def __call__(self, mags, compress=True):
        lm = [math.sqrt(v) for v in mags] if compress else mags
        return [sum(w * max(lm[a:b]) for a, b, w in parts) for parts in self.table]


def chroma(mags, n, rate, fmin, fmax):
    """Energy per pitch class (0 = C) of the bins between fmin and fmax."""
    c = [0.0] * 12
    for k in range(max(1, int(fmin * n / rate)), min(n // 2, int(fmax * n / rate) + 1)):
        key = 69 + 12 * math.log2(k * rate / n / 440.0)
        c[int(round(key)) % 12] += mags[k] * mags[k]
    return c
