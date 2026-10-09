"""Instruments of the YM3812 arrangement (music/badapple.py, tools/mkmusic.py), own patches.

An operator: mult (0-15; 0 = x0.5), ksl (0-3), tl (total level 0-63, 0.75 dB steps, 0 = loudest), ar, dr, sl, rr (0-15),
egt (1 = sustain until key off), vib, am, ksr (0/1), ws (waveform 0-3: sine, half sine, abs sine, quarter).
A patch: mod and car operators, fb (feedback 0-7), cnt (0 = FM, 1 = additive), tr (semitones from the written key to
the key of the channel, for a carrier with mult 2).

Rough times of the envelope at 3.58 MHz: attack from silence AR 4 = 0.35 s, 5 = 0.18 s, 6 = 90 ms, 10 = 6 ms; a fall of
the whole 96 dB at DR/RR 5 = 2.4 s, 6 = 1.2 s, 7 = 0.6 s, 8 = 0.3 s, 9 = 0.15 s, 10 = 80 ms.
"""


def op(mult=1, tl=0, ar=15, dr=0, sl=0, rr=7, egt=1, ksl=0, vib=0, am=0, ksr=0, ws=0):
    return dict(mult=mult, tl=tl, ar=ar, dr=dr, sl=sl, rr=rr, egt=egt, ksl=ksl, vib=vib, am=am, ksr=ksr, ws=ws)


def patch(name, mod, car, fb=0, cnt=0, tr=0):
    return dict(name=name, mod=mod, car=car, fb=fb, cnt=cnt, tr=tr)


# The melodic patches are bright and dense like the synths and the voice of the original: measured in SAPIemu
# (work lab, docs/rozhodnuti.md), a sustained note has its 630-1200 Hz band 2-7 dB, 1.6-3.2 kHz 8-11 dB and
# 4-8 kHz 12-16 dB under the band of its fundamental (the original's chorus: 2, 8, 13 dB). The first version had
# almost pure sines (1.6-3.2 kHz 40-60 dB down): it sounded hollow and bell-like. Feedback 6-7 with a strong
# modulator makes the saw-like spectrum.

# lead "voice": bright, a little nasal, soft attack; the vibrato comes later in long notes (the player sets VIB)
LEAD = patch('lead', op(mult=1, tl=13, ar=12, dr=1, sl=1, rr=6, ksl=1),
             op(mult=1, tl=0, ar=11, dr=1, sl=1, rr=6), fb=6)
# the same voice a little darker: echo and second voice
SHADOW = patch('shadow', op(mult=1, tl=15, ar=11, dr=1, sl=1, rr=6, ksl=1),
               op(mult=1, tl=0, ar=10, dr=1, sl=1, rr=6), fb=6)
# synth bass: saw-bright and a little rough, the brightness settles after the attack
BASS = patch('bass', op(mult=1, tl=14, ar=15, dr=3, sl=1, rr=8, ksl=1),
             op(mult=1, tl=0, ar=15, dr=2, sl=2, rr=9), fb=7)
# rounder bass for the quiet parts (still with its harmonics)
SUB = patch('sub', op(mult=1, tl=20, ar=13, dr=2, sl=2, rr=6, ksl=1),
            op(mult=1, tl=0, ar=12, dr=1, sl=2, rr=6), fb=6)
# string / supersaw pad: feedback 7, half-sine carrier, slow attack and release, vibrato (chorus)
PAD = patch('pad', op(mult=1, tl=18, ar=6, dr=1, sl=1, rr=5, ksl=1, vib=1),
            op(mult=1, tl=0, ar=5, dr=1, sl=1, rr=5, vib=1, ws=1), fb=7)
# gated saw (the chord of the stop in bar 63): full sustain, fast release
GATE = patch('gate', op(mult=1, tl=12, ar=15, dr=1, sl=1, rr=10, ksl=1),
             op(mult=1, tl=0, ar=15, dr=1, sl=1, rr=10), fb=6)
# The riff: distorted basses. The original's riff falls ~3 dB per octave to 4 kHz like a sawtooth; the closest
# patches in the SAPIemu lab (work/lab_bass.py, third octaves of a D#2 against a saw): feedback 6 with a half-sine
# carrier (within 2 dB), and the modulator at the double (rougher, like a distorted guitar). The attack bites:
# the modulator and the carrier fall 3 dB after it; the fast release separates the 16ths.
DRIVE = patch('drive', op(mult=1, tl=13, ar=15, dr=4, sl=1, rr=10),
              op(mult=1, tl=0, ar=15, dr=4, sl=1, rr=10, ws=1), fb=6)
GRIT = patch('grit', op(mult=2, tl=13, ar=15, dr=4, sl=1, rr=10, ws=1),
             op(mult=1, tl=0, ar=15, dr=4, sl=1, rr=10, ws=1), fb=7)
# pluck of the arpeggios: bright attack that dies down
PLUCK = patch('pluck', op(mult=1, tl=12, ar=15, dr=5, sl=4, rr=7, egt=0, ksl=1),
              op(mult=1, tl=0, ar=15, dr=6, sl=8, rr=7, egt=0), fb=6)

# rhythm mode: one operator each (BD has both)
BD = patch('bd', op(mult=0, tl=14, ar=15, dr=8, sl=4, rr=12, egt=0),         # a little click, long deep body
           op(mult=1, tl=0, ar=15, dr=6, sl=15, rr=12, egt=0), fb=3)
# With channels 7 and 8 at 4.5 and 1.2 kHz (tools/mkmusic.py RHYTHM_HZ) SD and HH are noise; HH mult 15 also brightens SD.
SD = op(mult=1, tl=0, ar=15, dr=8, sl=15, rr=9, egt=0)
HH = op(mult=15, tl=0, ar=15, dr=9, sl=15, rr=5, egt=0)      # closed hat; OH and CR differ only in DR, RR: two writes
OH = op(mult=15, tl=0, ar=15, dr=7, sl=15, rr=5, egt=0)      # open hat
CR = op(mult=15, tl=0, ar=15, dr=5, sl=15, rr=5, egt=0)      # crash: the hat with a long decay
TOM = op(mult=1, tl=0, ar=15, dr=8, sl=15, rr=8, egt=0)
CYM = op(mult=1, tl=63, ar=15, dr=5, sl=15, rr=6, egt=0)     # never played (metallic): only its phase feeds HH
