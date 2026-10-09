"""Instruments of the YM3812 arrangement (tools/mkmusic.py), own patches.

An operator: mult (0-15), ksl (0-3), tl (total level 0-63, 0.75 dB steps, 0 = loudest), ar, dr, sl, rr (0-15),
egt (1 = sustain until key off), vib, am, ksr (0/1), ws (waveform 0-3: sine, half sine, abs sine, quarter).
A patch: mod and car operators, fb (feedback 0-7), cnt (0 = FM, 1 = additive).
"""


def op(mult=1, tl=0, ar=15, dr=0, sl=0, rr=7, egt=1, ksl=0, vib=0, am=0, ksr=0, ws=0):
    return dict(mult=mult, tl=tl, ar=ar, dr=dr, sl=sl, rr=rr, egt=egt, ksl=ksl, vib=vib, am=am, ksr=ksr, ws=ws)


def patch(mod, car, fb=0, cnt=0):
    return dict(mod=mod, car=car, fb=fb, cnt=cnt)


# melodic voices
VOCAL = patch(op(mult=1, tl=30, ar=10, dr=2, sl=4, ksl=1, vib=1),          # soft lead with vibrato
              op(mult=1, tl=0, ar=11, dr=1, sl=1, rr=6, vib=1), fb=3)
BASS = patch(op(mult=1, tl=20, ar=15, dr=5, sl=6, egt=1, ksl=1),            # synth bass, the index falls
             op(mult=1, tl=0, ar=15, dr=2, sl=2, rr=8), fb=5)
SQUARE = patch(op(mult=2, tl=26, ar=15, dr=1, sl=3, ksl=1),                 # odd harmonics: square lead
               op(mult=1, tl=0, ar=14, dr=1, sl=2, rr=7, vib=1), fb=1)
ARP = patch(op(mult=1, tl=24, ar=15, dr=6, sl=8, egt=0),                    # pluck
            op(mult=2, tl=0, ar=15, dr=5, sl=10, rr=7, egt=0), fb=6)
GUITAR = patch(op(mult=1, tl=14, ar=15, dr=1, sl=2, ksl=1, ws=0),           # overdriven guitar
               op(mult=1, tl=0, ar=15, dr=2, sl=3, rr=6, ws=1), fb=7)

# rhythm mode: one operator each (BD has both)
BD = patch(op(mult=0, tl=12, ar=15, dr=8, sl=4, rr=12, egt=0),
           op(mult=1, tl=0, ar=15, dr=7, sl=15, rr=12, egt=0), fb=3)
SD = op(mult=1, tl=0, ar=15, dr=8, sl=15, rr=9, egt=0)
HH = op(mult=1, tl=0, ar=15, dr=9, sl=15, rr=9, egt=0)
HH_OPEN = op(mult=1, tl=0, ar=15, dr=6, sl=15, rr=7, egt=0)
TOM = op(mult=1, tl=0, ar=15, dr=7, sl=15, rr=8, egt=0)
CYM = op(mult=1, tl=0, ar=15, dr=5, sl=15, rr=6, egt=0)
