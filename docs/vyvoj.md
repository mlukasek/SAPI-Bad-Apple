# Vývoj

- Formát dat a dekodér: [format.md](format.md).
- Rozhodnutí s důvody a měřeními: [rozhodnuti.md](rozhodnuti.md).
- Ověření na skutečném hardwaru: [hw-otazky.md](hw-otazky.md).
- Zjištění pro vývoj emulátoru: [sapiemu-podnety.md](sapiemu-podnety.md).

## Začít na jiném počítači

Složky vedle sebe (u autora `E:\SAPI_GIT\`; jiné cesty se nastaví proměnnými prostředí, viz níže):

| Složka | Co | K čemu |
|---|---|---|
| `SAPI-Bad-Apple` | toto repo | |
| `SAPI-Bad-Apple\orig` | originál (jen lokálně, v `.gitignore`) | `Touhou - Bad Apple_003.avi`: video, z něj obraz i zvuk pro přepis hudby |
| `SAPIemu-release` | **vydaná verze SAPIemu (0.3.0-alpha)** | běh a testy dema; obraz CP/M RAM disku `media\zrmd-1\SAPI_CPM_Martin_2019-10-07.bin` |
| `Tools\pasmo-0.5.3\pasmo.exe` | assembler Z80 | překlad programu (`PASMO`) |
| `SAPIemu` | vývojová verze emulátoru (repo) | **nepoužívat**, autor ji vyvíjí souběžně; jen dokumentace desek (`docs/desky/`) |

1. **Python 3**, jen standardní knihovna (vyzkoušeno 3.14). **ffmpeg** na `PATH`: čte video a zvuk a dělá
   náhledy. Nic se neinstaluje do systému a nic se neukládá mimo `E:\SAPI_GIT\`.
2. **Video:** `orig\Touhou - Bad Apple_003.avi`.
   - Je to bezztrátové video, huffyuv 480 × 360 při 30 fps, 6571 snímků, 219,0 s.
   - Jiná kopie musí mít stejný počet snímků a stejný začátek, jinak nesedí časování hudby
     (`tools/frames.py` `SRC_FRAMES`, `tools/mkmusic.py` `OFFSET`).
3. **Originální data nejsou v repozitáři** (`.gitignore`): video, zvuk, MIDI, `BADAPPLE.DAT` ani obraz RAM disku.
   Všechno odvozené (`build/`, `work/`) se vyrábí znovu.
4. **Postup od nuly:**
   - `build.cmd video`: hudba, video, program, RAM disk, poprvé několik minut;
   - pak SAPIemu se sestavou `tools\emu\badapple_sapi1v.sapi`.

**Proměnné prostředí** (výchozí hodnoty jsou složky autora):
- `PASMO`: pasmo;
- `CPM_IMAGE`: obraz CP/M RAM disku, bere se z něj jen systémová oblast;
- `SAPIEMU_DIR`: vydané SAPIemu;
- `SAPIEMU_MCP`: adresa MCP, výchozí `http://127.0.0.1:8594/mcp`.

## Překlad

| Příkaz | Co udělá |
|---|---|
| `build.cmd` | hudba (`tools/mkmusic.py` z `music/badapple.py` → `build/music.bin`), obsluhy dekodéru (`tools/mkvdec.py` → `sapi/gen/vdec.asm`), pasmo (`build/badapple.com`, testovací `build/vtest.com`), kontrola rozložení paměti (`tools/check_build.py`), `build/BADAPPLE.DAT` (`tools/mkdat.py`), **`build/ramdisk.bin`** (celý RAM disk A:, `tools/cpmdisk.py --empty`) a `build/ramdisk.hex` (`tools/bin2hex.py`) |
| `build.cmd video` | navíc před programem proud videa (`tools/vcodec.py` → `build/video.bin`, asi 30 s, poprvé i zmenšení snímků ffmpegem) |

- **Video se kóduje až po hudbě:** kodér počítá, kolik času v každém VBI vezme přerušení s hudbou
  (`build/music.bin`). Po změně aranžmá je proto potřeba `build.cmd video`, jinak se může snímek nestihnout.
- **`build/ramdisk.bin`:**
  - ze `CPM_IMAGE` se bere jen systémová oblast (prvních 32 KB), adresář a data jsou E5;
  - `BADAPPLE.DAT` leží od bloku 8 (10000h), program ho čte na pevném místě přes porty ZRD-1V;
  - za ním je `BADAPPLE.COM`.
- **Intel HEX pro skutečný ZRD-1V:** `build/ramdisk.hex`, záznam rozšířené adresy před každými 64 KB.
- **SAPIemu** načte obraz RAM disku při spuštění (režim `nosave`). Po překladu ho stačí vypnout a zapnout
  (MCP `power`), sestava `tools\emu\badapple_sapi1v.sapi`.

## Nástroje

| Skript | Co dělá |
|---|---|
| **Video** | |
| `tools/frames.py [W H]` | snímky videa zmenšené ffmpegem (plošný průměr) na 256 × 192 v šedi, cache `work/frames_256x192.gray` (320 MB); modul |
| `tools/vcodec.py [--frames N] [--out F] [--check]` | **kodér videa**: obraz snímku (práh, hvězdy), mrtvá zóna a oprava zubů, stopy XOR intervalů, cyklový model dekodéru a přerušení, referenční dekodér (`--check` porovná každý snímek); hook `observe` pro měření |
| `tools/vfmt.py` | tabulka operačních kódů proudu (sdílí kodér a generátor dekodéru) |
| `tools/mkvdec.py` | generátor obsluh dekodéru Z80 (`sapi/gen/vdec.asm`) a jejich cen v T |
| `tools/vtest.py [--frames N] [--stream F]` | **dekodér v modelu Z80** (`tools/z80/`, s čekáním CGA-1V z HW) proti referenčnímu dekodéru: obraz po bajtech a T na snímek |
| `tools/vlab.py` | laboratoř prvních variant kodéru (statistiky formátů, `docs/rozhodnuti.md`) |
| **Hudba** | |
| `music/badapple.py` | **aranžmá**: noty, akordy, bicí a automatizace po šestnáctinách |
| `tools/mkmusic.py` | přehrávač not → proud zápisů do YM3812 po tikách (`build/music.bin`), simulace přerušení (zápisů na tik, zpoždění) |
| `tools/opl_patches.py` | nástroje (patche) YM3812 |
| `tools/transcribe.py` | měření zvuku videa pro přepis: salience půltónů ve středu a po stranách sterea, basa, chroma (`work/sal.json`); výpisy `roll`, `melody` |
| `tools/audio.py` | dekódování zvuku ffmpegem, FFT, harmonická salience; modul |
| **Data a RAM disk** | |
| `tools/mkdat.py` | `build/BADAPPLE.DAT`: hlavička, video (snímek nepřekročí hranici 32 KB), hudba |
| `tools/cpmdisk.py` | soubory do obrazu RAM disku CP/M (`--empty`, `@BLOK` souvisle od bloku), výpis adresáře, soubor ven |
| `tools/bin2hex.py` | obraz RAM disku → Intel HEX |
| `tools/check_build.py` | rozložení paměti programu (`build/badapple.sym`) |
| `tools/png.py` | čtení a zápis PNG (RGB) |
| **Emulátor** (`tools/emu/`) | |
| `tools\emu\sapiemu.cmd` | spustí `sapiemu-cli` ze `SAPIEMU_DIR` s MCP na portu **8594** |
| `tools/emu/run_demo.py [--at 5,10] [--out DIR] [--wav W] [--to-end]` | **demo v SAPIemu**: boot CP/M, `BADAPPLE`, snímky obrazovky v daných časech, čítače programu (snímky, pozdní snímky, `mus_lead`), nahrávka zvuku |
| `tools/emu/mkpreview.py W` | z nahrávky celého dema `build/badapple_opl.wav`, `build/sync.wav` (vlevo originál, vpravo naše hudba) a `build/preview_opl.mp4` (video originálu s naší hudbou) |
| `tools/emu/cpm.py`, `sapimcp.py` | boot CP/M a příkazy, klient MCP |
| `tools/z80/cpuz80.py`, `sapi.py` | model Z80 a sestavy V pro `vtest.py` |

**Program** (`sapi/`):
- `badapple.asm`: start, hlavní smyčka, přerušení, kruhový buffer, návrat do CP/M;
- `video.asm` a `gen/vdec.asm`: dekodér;
- `vfill.asm`: rozvinuté plnění;
- `music.asm`: přehrávač;
- `vtest.asm`: dekodér pro `tools/vtest.py`.

Pracovní skripty měření jsou ve `work/` (mimo repo). Patří sem laboratoře zvuku (`work/lab_*.py`), porovnání
pásem s originálem (`work/sectcmp.py`), přepis zpěvu (`work/vox/`) a vady obrazu kodéru (`work/vid/`).

## Testy

- **Kodér:** `python tools/vcodec.py --check`. Referenční dekodér musí dát přesně obraz, který kodér chtěl.
  Vypíše velikost, T na snímek, špatné body a počty VBI na snímek.
- **Dekodér Z80:** `python tools/vtest.py --frames 700`. Shoda obrazu po bajtech a T proti modelu (naposledy
  +0,08 %, nejhorší snímek 34 T).
- **Celé demo v SAPIemu:**
  - spustit `tools\emu\sapiemu.cmd`;
  - pak `python tools/emu/run_demo.py --to-end --wav work/demo_full.wav` a
    `python tools/emu/mkpreview.py work/demo_full.wav`;
  - na konci musí být `frame_cnt` = počet snímků z `build.cmd`, `late_cnt` 1 (tolik ukazuje každý běh) a
    `mus_lead` 1.
- **Hudba proti originálu:** poslech `build/sync.wav`, pásma po částech skladby `work/sectcmp.py`.

## Pasti

- **PowerShell:** `.\build.cmd | Select-Object -First N` zastaví překlad uprostřed.
  - Hudba se přeloží, ale `build/ramdisk.bin` zůstane starý a SAPIemu hraje starou verzi.
  - Celý výstup je proto potřeba poslat do logu: `.\build.cmd video *> work\build.log`.
- **SAPIemu vypínat přes MCP `power off`, nezabíjet.** Používat `SAPIemu-release`, ne vývojové repo.
- **Nahrávání zvuku v SAPIemu 0.3.0:** dlouhé `run_for` ztrácí zvuk, `run_demo.py` proto běží po 1 s
  ([sapiemu-podnety.md](sapiemu-podnety.md)).
- **SAPIemu po `resume` běží v reálném čase i mezi voláními MCP.** Skripty, které mají počítat emulovaný čas
  nebo chytat adresu, musí stroj nejdřív zastavit (`pause`) a pak volat `run_for` a `run_until`.
- **Python na Windows** píše v textovém režimu konce řádků CRLF. Repo má LF, při úpravách skripty psát
  s `newline=''`.
- **pasmo 0.5.3:** pasti v `~/.claude/CLAUDE.md` (unární minus, závorky v operandu, žádné ALIGN).
- **Časy ve videu:** demo snímek k ukazuje zdrojový snímek podle skutečného času (ve VBI 2k). Pozdní snímek
  posune zdroj, takže číslo snímku dema se od zdrojového liší (`observe` v `vcodec.py` dává obě čísla).
