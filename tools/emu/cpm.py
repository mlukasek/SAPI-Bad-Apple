"""Helpers for scripts: boot CP/M in SAPIemu (state 'cpm' kept in the emulator), run commands.

boot(): power cycle, ECMON menu choice 1 (CP/M from the RAM disk), wait for A>, save_state 'cpm'.
ready(): load_state 'cpm' if it exists, else boot().
command(text, wait='A>'): type a command line and wait for the prompt; returns the screen text.
Command line: python tools/emu/cpm.py "DIR"   (boots if needed, prints the screen)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sapimcp as sm  # noqa: E402


def boot():
    sm.call('pause')
    sm.call('power', state='cycle')
    sm.call('resume')
    sm.call('run_until', screen_text='Zadej 0-3', timeout_ms=20000)
    sm.call('type_text', text='1')
    sm.call('run_until', screen_text='A>', timeout_ms=30000)
    sm.call('pause')
    sm.call('save_state', name='cpm')


def ready():
    sm.call('pause')
    try:
        sm.call('load_state', name='cpm')
    except RuntimeError:
        boot()


def command(text, wait='A>', timeout_ms=30000):
    sm.call('resume')
    sm.call('type_text', text=text + '\r')
    sm.call('run_for', ms=200)
    sm.call('run_until', screen_text=wait, timeout_ms=timeout_ms)
    sm.call('pause')
    return sm.call('screen_text')


if __name__ == '__main__':
    ready()
    print(command(sys.argv[1]) if len(sys.argv) > 1 else sm.call('screen_text'))
