"""Source frames of the video for the encoder: orig/Touhou - Bad Apple_003.avi (lossless huffyuv 480x360, 30 fps,
6571 frames) scaled by ffmpeg (area average) to W x H grey, cached in work/frames_WxH.gray (raw, 1 B per pixel).

Usage: python tools/frames.py [W H]      (default 256 192; ffmpeg must be on PATH)
In code: frames.load(w, h) -> (count, bytes) ; frame i = data[i*w*h:(i+1)*w*h]
Display timing (docs/rozhodnuti.md): demo frame k is shown at VBI 2k = k * 1001/30000 s, so it takes the source
frame round(k * 1.001) (source_index).
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'orig', 'Touhou - Bad Apple_003.avi')
SRC_FRAMES = 6571


def cache_path(w, h):
    return os.path.join(ROOT, 'work', f'frames_{w}x{h}.gray')


def extract(w, h):
    out = cache_path(w, h)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', SRC, '-vf', f'scale={w}:{h}:flags=area',
                    '-f', 'rawvideo', '-pix_fmt', 'gray', out + '.tmp'], check=True)
    os.replace(out + '.tmp', out)
    return out


def load(w=256, h=192):
    p = cache_path(w, h)
    if not os.path.exists(p):
        extract(w, h)
    data = open(p, 'rb').read()
    return len(data) // (w * h), data


def source_index(k):
    """Source frame (30 fps) for demo frame k (29.97 fps)."""
    return min(SRC_FRAMES - 1, (k * 1001 + 500) // 1000)


def demo_frames(n_src=SRC_FRAMES):
    """Number of demo frames covering the source."""
    k = 0
    while (k * 1001 + 500) // 1000 < n_src:
        k += 1
    return k


if __name__ == '__main__':
    w, h = (int(sys.argv[1]), int(sys.argv[2])) if len(sys.argv) > 2 else (256, 192)
    n, _ = load(w, h)
    print(f'{cache_path(w, h)}: {n} frames {w}x{h}, demo frames {demo_frames(n)}')
