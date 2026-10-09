# Změny

## 1.0.0 (2026-10-09)

První vydání. Bad Apple!! na SAPI-1 V (JPR-1V, RAM-1V, CGA-1V, MPH-1V, ZRD-1V) jako `BADAPPLE.COM` pro CP/M,
data `BADAPPLE.DAT` na RAM disku.

- **Video:**
  - celé, 256 × 192 při 29,97 snímku/s na CGA-1V, 6393 snímků, 3,1 MB;
  - delta proti snímku ve skryté stránce, svislé stopy intervalů XOR, generované obsluhy dekodéru;
  - 95,5 % snímků za 2 VBI, těžké snímky o VBI později bez zpoždění videa.
- **Úpravy obrazu:**
  - mrtvá zóna pro chvějící se hrany (nejvýš 3 body, jen v těžkých snímcích víc než 1);
  - oprava zubů na svislých hranách, nové tečky a okraje obrazu se posílají vždy;
  - hvězdy v nočním letu jako body, rozmazané hvězdy při zrychlení jako čárky.
- **Hudba:**
  - vlastní aranžmá pro YM3812 (6 FM hlasů a bicí v rytmickém režimu);
  - melodie, akordy a stavba přepsané ze zvuku videa;
  - zpěv po slabikách, kytarový riff, tichý refrén, stop v taktu 63.
- **Synchronizace:**
  - přerušení 1300 Hz z 82C54 píše nejvýš jeden registr YM3812;
  - hudba se řídí hodinami videa: při zdržení obrazu plynule zpomalí.
- **RAM disk:** celý obraz 4 MB (`build/ramdisk.bin`, `build/ramdisk.hex` s rozšířenou adresou po 64 KB),
  `BADAPPLE.DAT` od bloku 8 se čte přímo přes porty ZRD-1V.
- **Ověřeno** na skutečném SAPI-1 V (autor, 2026-10-09) a v SAPIemu 0.3.0-alpha.

Video ani hudbu repo neobsahuje, `BADAPPLE.DAT` se vyrábí z vlastní kopie videa (README, `docs/vyvoj.md`).
