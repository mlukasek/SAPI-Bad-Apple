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
- Celé video: **2,94 MB, 6349 z 6564 snímků včas (96,7 %)**. Medián 52 k T, 90. percentil 114 k T na snímek.
  Nejhorší snímek trvá 6 VBI.
- Kodér počítá cykly; model Z80 (`tools/vtest.py`) ukázal shodu ±23 T na snímek a obraz po bajtech
  stejný jako reference.
- **Mrtvá zóna 1 bod:** odstraní 26 % intervalů a chyba hrany je nejvýš 1 bod.
- **Inverze paletou nepomohla:** střihy v Bad Apple nejsou prosté inverze.
