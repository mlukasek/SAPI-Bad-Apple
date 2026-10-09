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
# the body of the riff bass under DRIVE: a sine. The fundamental of the original's riff is 6 dB stronger than
# ours; the FM of DRIVE spreads its energy (a sine at full level has an 11 dB stronger fundamental, lab
# work/lab_layer.py)
DEEP = patch('deep', op(mult=1, tl=63, ar=15, dr=3, sl=1, rr=10),
             op(mult=1, tl=0, ar=15, dr=3, sl=1, rr=10))
# pluck of the arpeggios: bright attack that dies down
PLUCK = patch('pluck', op(mult=1, tl=12, ar=15, dr=5, sl=4, rr=7, egt=0, ksl=1),
              op(mult=1, tl=0, ar=15, dr=6, sl=8, rr=7, egt=0), fb=6)

# Noise from a melodic channel: the modulator at full level with feedback 7 is chaotic, the sound is almost white
# noise (SAPIemu lab work/lab_noise.py: flatness 0.97 in 1.5-11 kHz, no peak over 3 dB; the rhythm HH and SD have
# tonal peaks of 15-19 dB). The tails of the drums of the original (reverb, the wash of the hats) are white noise
# too. The modulator holds, the carrier decays at its own rate; a tail is a note on a free channel.
def noise(name, rate):
    return patch(name, op(mult=15, tl=0, ar=15, dr=0, sl=0, rr=rate),
                 op(mult=15, tl=0, ar=15, dr=rate, sl=15, rr=rate, egt=0), fb=7)


# Measured at C5 (work/lab_nzdecay.py, lab_nzcal.py): rate 6 falls 11 dB in 0.1 s and 21 dB in 0.2 s, rate 5
# 5 and 11 dB; at full level the noise is as loud as the rhythm SD (1.5-5 kHz) and 5 dB louder than the HH
# (5-15 kHz). The sine carrier: the abs-sine one has a strong DC and low end that muddies the kick.
NZ_HAT = noise('nz_hat', 6)          # the wash of the hats
NZ_SNARE = noise('nz_snare', 5)      # the reverb of the snare
NZ_CRASH = noise('nz_crash', 4)      # the tail of the crash
NOISE_KEY = 72                       # the key of the noise notes (C5): any key is noise

# the body of the snare: the original's has a steady tone at ~118 Hz about 10 dB over its noise
# (work/bodyflat.py); a short sine that dies by itself (-18 dB in 0.1 s; work/lab_body.py). A sliding, longer
# body sounded like a hummed "boo" (author).
BODY = patch('body', op(mult=1, tl=63, ar=15, dr=7, sl=15, rr=7, egt=0),
             op(mult=1, tl=0, ar=15, dr=7, sl=15, rr=7, egt=0))

# rhythm mode: one operator each (BD has both)
# kick: the punch comes from the pitch sweep (tools/mkmusic.py BD_SWEEP); the deep body (A1, the original's is at
# 54 Hz) holds and is cut off after ~280 ms (BD_GATE), measured in the intro of the original. A pure sine body
# sounded like a hummed "mmm" (author); the original's has its harmonics ~19 dB under it: a weak, steady
# modulator (work/lab_kick3.py). No click: a decaying modulator put 200-500 Hz into the attack, 5-8 dB over the
# original's. 4 dB softer than the short kick before: the held body has more energy.
BD = patch('bd', op(mult=1, tl=52, ar=15, dr=0, sl=0, rr=11, egt=1),
           op(mult=1, tl=5, ar=15, dr=5, sl=2, rr=11, egt=1), fb=0)
# With channels 7 and 8 at 4.5 and 1.2 kHz (tools/mkmusic.py RHYTHM_HZ) SD and HH are noise; HH mult 15 also brightens SD.
SD = op(mult=1, tl=0, ar=15, dr=8, sl=15, rr=9, egt=0)
HH = op(mult=15, tl=0, ar=15, dr=9, sl=15, rr=5, egt=0)      # closed hat; OH and CR differ only in DR, RR: two writes
OH = op(mult=15, tl=0, ar=15, dr=7, sl=15, rr=5, egt=0)      # open hat
CR = op(mult=15, tl=0, ar=15, dr=5, sl=15, rr=5, egt=0)      # crash: the hat with a long decay
TOM = op(mult=1, tl=0, ar=15, dr=8, sl=15, rr=8, egt=0)
CYM = op(mult=1, tl=63, ar=15, dr=5, sl=15, rr=6, egt=0)     # never played (metallic): only its phase feeds HH
