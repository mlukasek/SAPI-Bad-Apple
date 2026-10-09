"""Listening files from an emulator recording of the demo (tools/emu/run_demo.py --to-end --wav W):
build/badapple_opl.wav (the music from the start of the video), build/sync.wav (left the audio of the video,
right ours) and build/preview_opl.mp4 (the original video with our music). The recording is aligned by its
first sound, which is MIDI time 0 (tools/mkmusic.py MIDI_OFFSET s of the video).

Usage: python tools/emu/mkpreview.py [work/demo_full.wav]
"""
import array
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import mkmusic  # noqa: E402

VIDEO = os.path.join(ROOT, 'orig', 'Touhou - Bad Apple_003.avi')
B = os.path.join(ROOT, 'build')


def first_sound(path, thr=300):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-vn', '-ac', '1', '-ar', '8000', '-f', 's16le', '-'],
                         capture_output=True, check=True).stdout
    a = array.array('h')
    a.frombytes(raw[:len(raw) // 2 * 2])
    return next(i for i, x in enumerate(a) if abs(x) > thr) / 8000


def ff(*args):
    subprocess.run(['ffmpeg', '-v', 'error', '-y'] + list(args), check=True)


def main():
    rec = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'work', 'demo_full.wav')
    shift = first_sound(rec) - mkmusic.MIDI_OFFSET
    print(f'video time 0 is {shift:.3f} s of the recording')
    ours = os.path.join(B, 'badapple_opl.wav')
    ff('-i', rec, '-af', f'atrim=start={shift:.4f},asetpts=PTS-STARTPTS,aresample=44100,volume=1.6', ours)
    ff('-i', VIDEO, '-i', ours, '-filter_complex',
       '[0:a]aresample=44100,pan=mono|c0=0.5*c0+0.5*c1,volume=0.6,aformat=sample_fmts=fltp:channel_layouts=mono[l];'
       '[1:a]aformat=sample_fmts=fltp:channel_layouts=mono[r];[l][r]amerge=inputs=2[a]',
       '-map', '[a]', '-t', '220', os.path.join(B, 'sync.wav'))
    ff('-i', VIDEO, '-i', ours, '-map', '0:v', '-map', '1:a', '-c:v', 'libx264', '-crf', '23', '-preset', 'veryfast',
       '-c:a', 'aac', '-b:a', '192k', '-shortest', os.path.join(B, 'preview_opl.mp4'))
    print('build/badapple_opl.wav, build/sync.wav, build/preview_opl.mp4')


if __name__ == '__main__':
    main()
