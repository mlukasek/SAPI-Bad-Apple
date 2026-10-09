# Rozhodnutí a poznatky

Nové rozhodnutí vždy dopsat sem, s datem a důvodem.

## Sestava a hardware (2026-10-09)

- **Sestava V:**
  - JPR-1V (Z80, **4 MHz TURBO**), RAM-1V, AND-1V, DSM-1V;
  - **ZRD-1V rev 1.1** (autor ho tak má);
  - **CGA-1V**;
  - MPH-1V (YM3812).
- **CGA-1V, ne DGD-1V:**
  - CGA-1V má dvě stránky (kreslí se do skryté), příznak a přerušení VBI a paletu.
  - DGD-1V má jednu stránku a žádnou synchronizaci, obraz by trhal.
- **Hudba je vlastní FM aranžmá pro OPL2** (autor zvolil). MPH-1V nemá DAC, zpěv proto hraje FM nástroj.

## Video (2026-10-09)

Měřeno na `orig/Touhou - Bad Apple_003.avi` (bezztrátové 480×360 při 30 fps, 6571 snímků), zmenšeném
ffmpegem (plošný průměr) a s prahem 50 %. Skripty: `tools/vlab.py`, `tools/vcodec.py`.

- **256×192 při 29,97 fps.** Je to přesně 4:3 a x se vejde do bajtu. Pro srovnání: nejlepší porty na 8080
  mají 64×48 při 12,5 fps (Vector-06c) a 180×70 při 9,1 fps (PMD 85).
- **Rozpočet:** 133 467 T na snímek (2 VBI při 4 MHz) a ≈ 4,0 MB RAM disku (bloky 8–1015).
- **Delta proti stránce N-2** (dvě stránky): kreslí se jen to, co se změnilo od snímku, který je ve skryté
  stránce. Je to jeden průchod a dekodér nemá žádný stav.

**Formáty, které neprošly:**

| Formát | Proč neprošel |
|---|---|
| Naivní bajtová RLE | 6,1 MB, nevejde se |
| Seznamy přechodů se slučováním se stavem stránky | 68 % snímků přes rozpočet |
| Intervaly v řádcích s predikcí z řádku nad ním (pracovní `work/vcodec_old.py`, mimo repo) | 2,5 MB, ale ≈ 250–340 T na interval (tabulky, ukazatele seznamů) a jen 86 % snímků včas |

**Stopy** ([format.md](format.md)):
- Svislé řetězy intervalů s jedním bajtem na řádek.
- Pro každý kód je vygenerovaná obsluha bez tabulek: řádek v jednom bajtu stojí 81 T, ve dvou 112 T.
- Celé video (první model přerušení): 2,94 MB, 6349 z 6564 snímků včas (96,7 %). Medián 52 k T, 90. percentil
  114 k T na snímek. Nejhorší snímek trvá 6 VBI. S přesnějším modelem přerušení viz Hudba.
- Kodér počítá cykly; model Z80 (`tools/vtest.py`) ukázal shodu ±23 T na snímek a obraz po bajtech
  stejný jako reference.
- **Mrtvá zóna 1 bod:** odstraní 26 % intervalů a chyba hrany je nejvýš 1 bod.
- **Inverze paletou nepomohla:** střihy v Bad Apple nejsou prosté inverze.

## Hudba (2026-10-09)

**Vlastní aranžmá místo převzatého MIDI.** První verze hrála MIDI přepis z
[Handhule90/badapple-midi](https://github.com/Handhule90/badapple-midi). Autor ji zamítl: aranž byla zvláštní
a cizí, demo má být vlastní tvorba. Teď je aranžmá vlastní, psané pro OPL2 (`music/badapple.py`).
MIDI soubory zůstaly jen lokálně v `orig/midi/` a nic je nepoužívá.

**Přepis ze zvuku videa** (`tools/transcribe.py`, `tools/audio.py`; FFT a harmonická salience jen ve
standardní knihovně):
- Mřížka: 138 BPM, takt 0 v 1,39 s zvuku videa (ověřeno nástupy kopáků a hi-hatů).
- Stavba (podobnost chromy po taktech): intro 0–7, riff 8–15, sloka 16–31, refrén 32–47, tichý refrén 48–63,
  riff 64–71, sloka 72–87, refrén 88–103, **refrén o půltón výš (e moll)** 104–119, dohra 120–124.
- Melodie zpěvu ze středu sterea (M − 1,2·|S| ve spektru), zprůměrovaná přes všechna opakování téhož místa
  a dohledaná Viterbiho průchodem; sloka i refrén sedí na známou melodii.
- Akordy z bělené chromy a basy po půltaktech: sloka D#m – D#m – Bmaj7 – C# Dm, refrén Bmaj7 – C#sus2 –
  D#m – D#m, v riffu D#m s G#7 a F#sus2, konce refrénu bas G# → G.
- Kontrola výsledku (`work/compare.py`, nahrávka z SAPIemu proti originálu): podobnost chromy po taktech
  většinou 0,6–0,98 a tónina sedí. Slabší jsou jen takty, kde melodie drží tón přes akord.

**Aranžmá** ([format.md](format.md)):
- 6 melodických kanálů a rytmický režim: hlas, basa, ozvěna nebo druhý hlas, dva hlasy akordů, arpeggio
  nebo zvonky.
- Vlastní intro (zvonky s ozvěnou nad sílící plochou, nástup kopáku a basy s otevíráním „filtru“ modulátorem,
  vír virblu) a vlastní riff (rytmizovaný saw 3-3-2 a zvonkový motiv).
- Tichý refrén zpívá zvonek, pak se vrátí hlas a vše graduje. Závěr v e moll vrací zvonky z intra.
- Zvonek má poměr operátorů 3:1. Původní 3,5:1 dával do d moll cizí tóny C a D (ukázala to chroma).

**Synchronizace hudby s obrazem:**
- Hudba se neřídí VBI, ale hodinami videa. Ty stojí, když je snímek pozdě, a hudba podle náskoku plynule
  zpomalí ([format.md](format.md), tabulka `mus_rate`).
- Snímky po opožděném drží odstup od skutečného přepnutí, takže video zpomalí a nedohání skoky.
- **Zkouška v SAPIemu** (`work/slowtest.py`): 10 s uprostřed dema s CPU na 2 MHz (TURBO vypnuté). Video
  běží na ~73 %, hudba zpomalí s ním, náskok hudby je nejvýš 13 tiků (0,2 s), většinou 3–9. Po návratu na
  4 MHz se do 2 s vrátí na 1 tik.
- Při běžném běhu je náskok celou dobu 1 tik a pozdní je jen první snímek.

**Přerušení a čas pro video:**
- Přerušení zůstává časovač 82C54, ne VBI z CGA-1V: klávesnice Consul bez latche dává jen 1 ms impuls STROBE.
- Nečinné volání stojí 183 T (odpočet tiku), zápis do YM 168 T navíc.
- Kodér videa bere čas přerušení pro každý VBI z proudu hudby (nejvíc z VBI a sousedů).
- Video: **2,97 MB, 6438 z 6564 snímků (98,1 %)**, 2 VBI 6209 snímků, 3 VBI 186, 4 VBI 37, 5 VBI 6.

**Nahrávání v SAPIemu 0.3.0:** dlouhá volání `run_for` (desítky sekund) ztrácejí zvuk (v nahrávce jsou
úseky digitálního ticha). `run_demo.py` proto při nahrávání běží po 1 s.

**Soubory k poslechu** (`tools/emu/run_demo.py --to-end --wav W`, pak `tools/emu/mkpreview.py W`):
- `build/preview_opl.mp4`: původní video s naší hudbou;
- `build/badapple_opl.wav`: jen naše hudba;
- `build/sync.wav`: originál vlevo, naše hudba vpravo;
- `build/badapple.vgm`: pro přehrávač VGM.
