"""Assemble sapi/pop.asm with pasmo -> build/pop.com, build/pop.sym. A 'jr' out of range is turned into 'jp'
in the source automatically (the translated code does not know the distances), other errors stop.

Usage: python tools/asmloop.py   (pasmo: environment variable PASMO, default E:/SAPI_GIT/Tools/pasmo-0.5.3/pasmo.exe)
"""
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PASMO = os.environ.get('PASMO', r'E:\SAPI_GIT\Tools\pasmo-0.5.3\pasmo.exe')


def main():
    sapi = os.path.join(ROOT, 'sapi')
    os.makedirs(os.path.join(ROOT, 'build'), exist_ok=True)
    for _ in range(400):
        r = subprocess.run([PASMO, '--bin', 'pop.asm', '../build/pop.com', '../build/pop.sym'], cwd=sapi,
                           capture_output=True, text=True)
        out = (r.stdout + r.stderr).strip()
        if not out and r.returncode == 0:
            print('BUILD OK')
            return
        m = re.search(r'line (\d+) of file (\S+)', out)
        if not m:
            sys.exit(out)
        line, fn = int(m.group(1)), os.path.join(sapi, m.group(2))
        src = open(fn, encoding='utf-8').read().split('\n')
        if 'Relative jump out of range' in out:
            src[line - 1] = re.sub(r'\bjr\b', 'jp', src[line - 1], count=1)
            open(fn, 'w', encoding='utf-8', newline='\n').write('\n'.join(src))
            continue
        sys.exit(f'{out}\n>> {m.group(2)}:{line}: {src[line - 1]}')
    sys.exit('too many jr -> jp')


if __name__ == '__main__':
    main()
