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


# lead "voice": soft attack, slightly nasal; the vibrato comes later in long notes (the player sets VIB)
LEAD = patch('lead', op(mult=1, tl=29, ar=10, dr=2, sl=4, rr=6, ksl=1),
             op(mult=1, tl=0, ar=11, dr=1, sl=1, rr=6), fb=3)
# the same voice darker and rounder: echo and second voice
SHADOW = patch('shadow', op(mult=1, tl=35, ar=10, dr=2, sl=4, rr=6, ksl=1),
               op(mult=1, tl=0, ar=10, dr=1, sl=1, rr=6), fb=2)
# synth bass: the brightness falls during the note ("wow"), punchy attack
BASS = patch('bass', op(mult=1, tl=17, ar=15, dr=5, sl=6, rr=8, ksl=1),
             op(mult=1, tl=0, ar=15, dr=3, sl=3, rr=9), fb=5)
# round sub bass for the quiet parts
SUB = patch('sub', op(mult=1, tl=34, ar=13, dr=2, sl=4, rr=6, ksl=1),
            op(mult=1, tl=0, ar=12, dr=1, sl=2, rr=6), fb=2)
# warm saw-like pad, slow attack and release, vibrato
PAD = patch('pad', op(mult=1, tl=27, ar=5, dr=2, sl=3, rr=5, ksl=1, vib=1),
            op(mult=1, tl=0, ar=5, dr=1, sl=1, rr=5, vib=1), fb=6)
# electric-piano-like stab of the verses: bright bark, mellow decay
STAB = patch('stab', op(mult=1, tl=27, ar=15, dr=5, sl=7, rr=7, egt=0, ksl=1),
             op(mult=1, tl=0, ar=15, dr=4, sl=5, rr=7, egt=0), fb=4)
# gated saw of the riffs: full sustain, fast release (the notes are cut short)
GATE = patch('gate', op(mult=1, tl=24, ar=15, dr=1, sl=2, rr=10, ksl=1),
             op(mult=1, tl=0, ar=15, dr=1, sl=1, rr=10), fb=6)
# trance pluck of the arpeggios
PLUCK = patch('pluck', op(mult=2, tl=28, ar=15, dr=5, sl=8, rr=7, egt=0, ksl=1),
              op(mult=1, tl=0, ar=15, dr=6, sl=9, rr=7, egt=0), fb=4)
# bell: modulator 3x the carrier (harmonic: no foreign partials against the key), the carrier an octave up,
# the brightness dies away faster than the tone
BELL = patch('bell', op(mult=6, tl=31, ar=15, dr=5, sl=7, rr=5, egt=0),
             op(mult=2, tl=0, ar=15, dr=3, sl=7, rr=5, egt=0), fb=1, tr=-12)

# rhythm mode: one operator each (BD has both)
BD = patch('bd', op(mult=0, tl=12, ar=15, dr=8, sl=4, rr=12, egt=0),
           op(mult=1, tl=0, ar=15, dr=7, sl=15, rr=12, egt=0), fb=3)
SD = op(mult=1, tl=0, ar=15, dr=8, sl=15, rr=9, egt=0)
HH = op(mult=1, tl=0, ar=15, dr=9, sl=15, rr=7, egt=0)       # HH and OH differ only in DR: one write
OH = op(mult=1, tl=0, ar=15, dr=7, sl=15, rr=7, egt=0)
TOM = op(mult=1, tl=0, ar=15, dr=7, sl=15, rr=8, egt=0)
CYM = op(mult=1, tl=0, ar=15, dr=5, sl=15, rr=6, egt=0)
