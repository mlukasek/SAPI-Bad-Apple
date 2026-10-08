# SAPI-Bad-Apple – kontext projektu

Demo Bad Apple!! (Touhou, video Anira, hudba Alstroemeria Records feat. nomico) pro Tesla SAPI-1, sestavu V:
JPR-1V (Z80 4 MHz), RAM-1V, AND-1V, DSM-1V, RAM disk ZRD-1V rev 1.1, CGA-1V, MPH-1V (YM3812). Jako CP/M
`.COM` s daty na RAM disku. Autor: Martin Lukášek (mlukasek). Komunikace **česky**.

## Kde co je

- **Pro práci začni v `docs/vyvoj.md`** (nástroje, překlad, testy, pasti).
- Dál `docs/format.md` (formát videa a dekodér), `docs/rozhodnuti.md` (rozhodnutí s důvody, nové
  dopisovat), `docs/hw-otazky.md` (ověření na HW).
- **Zdroje (jen lokálně, `orig/`, necommitovat):**
  - `Touhou - Bad Apple_003.avi` (bezztrátové 480×360 při 30 fps);
  - `Touhou - Bad Apple.mp3`;
  - bitmapy.
- **Emulátor:** `..\SAPIemu-release` (MCP, sestava `tools/emu/badapple_sapi1v.sapi`). **Vývojové repo
  `..\SAPIemu` nepoužívat**, nanejvýš číst dokumentaci desek (`docs/desky/`).
- **Sesterské projekty se stejným stylem:**
  - `..\SAPI-Prince-of-Persia`: RAM disk, CGA-1V, YM3812; odtud `tools/cpmdisk.py`, `bin2hex.py`, `png.py`,
    `tools/z80/` a `tools/emu/`;
  - `..\SAPI-FXS4`: YM3812, ISR;
  - `..\SAPI-Flappy`, `..\SAPI-Bomberman`.

## Pravidla

- **Originální data nikdy necommitovat:** video, hudbu, bitmapy, MIDI, vygenerovaný `.DAT`, `ramdisk.bin`.
  Repo má jít zveřejnit bez úprav.
- **Jazyk:** kód a komentáře v asm a skriptech **anglicky**, dokumentace **česky**.
- **Asm:** pasmo 0.5.3 (`E:\SAPI_GIT\Tools\pasmo-0.5.3\pasmo.exe`), pasti v `~/.claude/CLAUDE.md`.
- **Python 3, jen standardní knihovna.** ffmpeg musí být na PATH.
- **Měřit, nehádat:**
  - cykly dekodéru v modelu Z80 (`tools/vtest.py`, s čekáním CGA-1V z HW);
  - celek v SAPIemu.
- **Dokumentace:** důležité poznatky zapisovat do `docs/` (pracuje se z více počítačů).
- **Git:** lokální commity průběžně, push jen na výslovné vyžádání. Na konec commitu řádek Co-Authored-By.
- **Reálný HW má autor.** Otázky k ověření sbírat v `docs/hw-otazky.md`.
- **Nic neukládat mimo `E:\SAPI_GIT\`.** SAPIemu vypínat přes MCP `power off`, ne zabít.
