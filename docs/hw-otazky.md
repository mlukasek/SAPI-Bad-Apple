# Ověření na skutečném hardwaru

Otázky, které jde ověřit jen na skutečném SAPI-1. Sbírat sem, autor je ověří dávkově.

**Jak:**
1. Nahrát `build/ramdisk.bin` (nebo `build/ramdisk.hex`) do ZRD-1V.
2. V nabídce ECMON zvolit `1`, v CP/M spustit `BADAPPLE`.
3. Demo běží 3 min 40 s a pak se vrátí do CP/M. Klávesa ho ukončí dřív.

## Ověřeno na skutečném SAPI-1 (autor, 2026-10-09)

- **Demo běží celé**, autor ho na sestavě V (JPR-1V na 4 MHz) hodnotí „za mě dobrý“.
- Tím jsou ověřené i předpoklady, na kterých demo stojí:
  - **přerušení 1300,7 Hz** z čítače 2 obvodu 82C54 na MPH-1V v IM 1 pod CP/M (`JP isr` na 0038h);
  - **přepínání stránek CGA-1V** ve VBI a příznak VBI ve STATUS;
  - **režim CGA** (2 bity na bod, COLMASK 11h) a paleta;
  - **čtení RAM disku** přes porty ZRD-1V (`BADAPPLE.DAT` od 10000h);
  - **zápisy do YM3812** po jednom v přerušení, nejméně 770 µs od sebe.
- **Cyklový model kodéru** počítá s čekáním CGA-1V naměřeným na HW u portu Prince of Persia: při 4 MHz
  asi 2,4 T na zápis a 1,3 T na čtení (`SAPI-Prince-of-Persia/docs/hw-otazky.md`, měřicí program
  `ZRDBENCH`).

## Otevřené (zatím nikdo nehlásil problém, ale cíleně neověřeno)

- **Stíhají se snímky na HW přesně jako v modelu?** Program má čítač pozdních snímků `late_cnt` (symbol
  v `build/badapple.sym`), na HW se zatím nečetl. V SAPIemu je na konci 1.
- **Konec klávesou:** ukončí libovolná klávesa demo hned a vrátí se do CP/M v pořádku (prompt `A>`, další
  spuštění)? Klávesnice se v přerušení čte z portu 01h (pulz STROBE 1 ms).
- **Hlasitost a barva hudby** proti SAPIemu: model YM3812 v emulátoru a skutečný čip se můžou lišit
  v hlasitosti bicích v rytmickém režimu a ve zkreslení se zpětnou vazbou 6–7.
- **Konec dema:** po posledním snímku 2 s poslední obraz, pak ticho, mapa paměti zpět a teplý start
  CP/M (`JP 0`).
