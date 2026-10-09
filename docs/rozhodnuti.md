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
- Kontrola výsledku (pracovní `work/compare.py`, nahrávka z SAPIemu proti originálu): podobnost chromy po
  taktech většinou 0,6–0,96 a tónina sedí. Slabší jsou takty, kde melodie drží tón přes akord, a intro
  (jen bicí, chroma tam nic neříká).

**Plán aranžmá podle originálu** (měřeno: rytmický otisk po pásmech a šestnáctinách, chroma po půltaktech,
salience středu a stran sterea; autor první verzi s vlastním intrem zvonků odmítl, protože originál začíná
bubny a činely):
- **Intro 0–7: jen bicí.** Kopák na doby, virbl na 2 a 4 s vírem šestnáctin na konci sudých taktů, činely
  na osminy, crash na začátku; kopák je laděný kolem A#1 (58 Hz). Takt 7 graduje do riffu.
- **Riff 8–15, 64–71:** basová linka v šestnáctinách, pod ní tiše držená kvinta D#4 + A#4 (power chord).
  Podrobněji v odstavci „Riff“ níže.
- **Sloka:** široká držená plocha (struny) D#m, basa osminy s důrazem mezi doby, hi-haty mezi dobami.
- **Refrén:** široká plocha, basa osminy, plný rytmus.
- **Tichý refrén 48–62:** bez kopáku, tlesknutí na 3. dobu, hlas zpívá dál. **Takt 63:** dva údery virblu a
  společný úder na 3. dobu, pak ticho do riffu.
- **Poslední refrén 104–119 v e moll: bez bicích.** Kopák mizí po taktu 103.
- **Dohra 120–124:** jen doznívající Esus4, beze basy.

**Aranžmá pro OPL2** ([format.md](format.md)): 6 melodických kanálů a rytmický režim. Hlas má ozvěnu nebo
druhý hlas pod melodií, plochy ve sloce a v tichém refrénu mají 3 hlasy, virbl má pod sebou nízký TOM jako tělo,
činely na osminy hraje „ride“ (CYM s kratším doznětím).

**Zvuk proti originálu** (autor: „moc to zvoní, originál má spíš šustivé bubny, kopák, činely“). Měřeno
pracovními nástroji `work/drumlab.py`, `work/sectcmp.py` a laboratoří OPL2 v SAPIemu (`work/oplab.py`: zápisy do
registrů YM3812 přes MCP `io_write`, nahrávka jednotlivých úderů a tónů):
- **Chyba přehrávače bicích:** bity v registru BDh se nulovaly hned v dalším tiku, takže každý buben držel
  klávesu jen 16 ms a pak doznával rychlostí RR (kopák RR 12 = cvaknutí bez těla). Teď bit zůstává a buben
  dozní svou obálkou (DR); nový úder bit nejdřív vynuluje. Kopák má pak 99 % energie v 40–80 Hz jako originál.
- **Činel CYM se nehraje:** v OPL2 je to jen kovová kombinace dvou obdélníků bez šumu (tóny kolem 1 a 2 kHz,
  plochost spektra 0,04). Činely na osminy, otevřený hi-hat i crash hraje HH (obsahuje šum) s různým DR.
- **Kanály 7 a 8 na 6 kHz:** při 392 / 147 Hz měl virbl tón 2,6 kHz a hi-hat 1 kHz („zvonění“). Při 6 kHz jsou
  šum: virbl plochost 0,51, hi-hat 0,43–0,58 (originál 0,53). Tom pod virblem (ladil kanál 8 dolů) je pryč.
- **Melodické nástroje byly skoro čisté sinusovky:** pásmo 1,6–3,2 kHz o 40–60 dB pod základním tónem, originál
  jen o 8 dB. Mřížka parametrů v laboratoři: zpětná vazba 6–7 a silný modulátor (TL 12–18) dávají −2, −8 a −13 dB
  v pásmech 630–1200 Hz, 1,6–3,2 kHz a 4–8 kHz jako refrén originálu. Doprovodné hlasy jsou proti sobě rozladěné
  o 4–10 centů (hutnost).
- **Mix:** originál má skoro všechnu energii v kopáku a base (40–80 Hz). Hlas a syntezátory jsou proto
  o 4–6 dB níž (`MIX`), hi-haty a shaker dodávají vzduch nad 4 kHz.
- **Výsledek (energie po pásmech proti celku, naše minus originál):** intro, riff, sloka a refrén většinou do
  ±3 dB, nad 4 kHz o 3–7 dB méně. Před opravou intro +18 dB v 250–500 Hz a −4 dB v 40–80 Hz, refrén −20 až
  −30 dB nad 1,6 kHz. Hutnost středů (plochost 0,15–0,25 proti 0,45) a vzduch v částech bez bicích zůstávají
  slabší: OPL2 nemá dozvuk ani víc hlasů.

**Riff: razantní basy** (autor: „po bubnech před zpěvem mají být fakt razantní baskytary, v originále je to
super zvuk“). Měřeno pracovními nástroji `work/riff*.py` (riff proti intru se stejnými bicími, po šestnáctinách
a pásmech, střed a strany sterea zvlášť):
- **Linka:** šestnáctiny D#2 D#2 D#2 D#3 D#3 D#3 C#3 D#3 v každé půlce taktu. Lichý takt končí přes G#
  (d#2 d#2 d#3 f#3 g#2 g#2 f#3 g#2), každý čtvrtý přes F# (g#2 g#2 f#2 g#2 f#2 f#2 d#3 f#3). Stejnou linku
  hraje střed i obě strany sterea, tedy basa a zdvojené kytary.
- **Barva:** hustá řada harmonických do 4 kHz, která klesá asi o 3 dB na oktávu, tedy skoro přesně jako pila.
  Pásmo 1–4 kHz je v riffu o 16 dB silnější než v intru. Naše dřívější verze (držená basa a pulzující akord)
  měla středy o 10 dB slabší a jen jednotlivé tóny.
- **Zvuky** (laboratoř `work/lab_bass.py`: třetinooktávy D#2 proti pile, mřížka zpětné vazby, síly modulátoru
  a vlnových tvarů): `DRIVE` (basa, zpětná vazba 6, nosná půlsinus, do 2 dB od pily) a `GRIT` (kytary,
  modulátor na dvojnásobku, drsnější). Tvrdý náběh, po něm pokles o 3 dB, rychlé uvolnění odděluje šestnáctiny.
- **Hloubka** (autor: „chybí větší hloubka a víc basy, jsou to baskytary“): základní tón riffu byl proti kopáku
  o 6 dB slabší než v originálu. FM zvuk `DRIVE` rozkládá energii do harmonických: sinus na plné úrovni má
  základní tón o 11 dB silnější (`work/lab_layer.py`). Pod linku proto hraje sinus `DEEP` na kanálu 5 (o 2 dB
  pod basou). Teď je pásmo 80 Hz proti kopáku −4 dB (originál −5 dB).
- **Aranž:** basa na kanálu 1, sinus na kanálu 5, dvě kytary na kanálech 0 a 2 rozladěné o ±12 centů. Synkopy
  (4. a 8. šestnáctina půltaktu) jsou o 1 dB silnější. Kytary končí dvě šestnáctiny před slokou, aby se stihly
  přepnout nástroje.

**Činely v intru** (autor: „místy ještě trochu zvoní“). Laboratoř `work/lab_hh3.py` a `lab_hh4.py` měřila
spektrum zprůměrované přes 8 úderů. Jeden úder má vlastní náhodné špičky šumu 10–15 dB, takže z něj tón
nepoznáš. Výsledky:
- Při kanálech 7 a 8 na 6 kHz měl hi-hat tón 1,7–2 kHz (16 dB nad okolím).
- Při 4,5 kHz a 1,2 kHz nemají hi-hat ani virbl žádný tón pod 4,9 kHz. Zůstávají jen špičky nad 5 kHz, které
  zní jako šustění.
- Hi-haty v intru jsou navíc o 1,5 dB a crashe o 2 dB tišší.

**Dozvuky bicích v intru** (autor: „bicí jsou krátké, jako by chyběly dozvuky, celkově plošší“). Pracovní
`work/introdecay.py` měří energii po pásmech v osminách šestnáctiny, průměr taktů 1–6:
- **Originál:** hi-haty slábnou jako šumový záblesk (−9 dB za 70 ms, −24 dB za 180 ms) a vzduch mezi údery
  nemizí. Virbl spadne o 12 dB za 55 ms a pak dozní (−24 dB za 0,2 s). Kopák drží plnou sílu ~280 ms a pak
  ostře skončí.
- **Naše dřív:** rytmický HH zmizí o 26 dB za 25 ms, virbl za 50 ms, kopák postupně slábne.
- **Šum z melodického kanálu:** modulátor na plné úrovni se zpětnou vazbou 7 je chaotický. Výsledek je skoro
  bílý šum: plochost 0,97 v 1,5–11 kHz a žádný tón přes 3 dB (`work/lab_noise.py`). Ocasy bicích originálu
  jsou také bílý šum: v třetinooktávách stoupají o 3 dB na oktávu. Nosná musí být sinus, protože absolutní
  sinus (ws 2) má silnou stejnosměrnou složku a basy, které zakalí kopák.
- **Ocasy** (`Parts.tails`, `INTRO_TAILS`): ke každému úderu v intru hraje volný melodický kanál šumovou notu,
  která sama doznívá:
  - virbl: kanál 3, rychlost 5, asi 12 dB pod ním;
  - hi-haty: kanál 4, rychlost 6, asi 3 dB pod nimi;
  - crash: kanál 5, rychlost 4.

  Zvonivý rytmický crash je tišší a jeho zvuk nese šum. Tónové špičky crashe klesly z 16–21 dB nad okolím na
  ≤ 12 dB (originál ≤ 16 dB), u hi-hatu a virblu z 18–19 na 13 dB.
- **Kopák:** drží na nosné (EGT, SL 2) a po 17 tikách (280 ms) přehrávač vynuluje jeho bit v BDh (`BD_GATE`).
  Protože má delší tělo, je o 4 dB tišší.
- **Výsledek:** obálky všech pásem v intru sedí s originálem. Energie po pásmech v intru a riffu je do ±4 dB,
  ve sloce a refrénu do ±5 dB, nad 4 kHz o 4–6 dB méně.

**Kopák a tělo virblu** (autor: „šumu je už možná hodně, zvlášť u kopáku chybí víc basy“). Pracovní
`work/kickspec.py` a `hitspec.py` měří třetinooktávy 0–50 ms a 50–200 ms po dobách, laboratoř
`work/lab_kick2.py` a `lab_body.py`:
- **Úder kopáku** má v originálu v prvních 50 ms vrchol na 100–125 Hz a nad 160 Hz skoro nic. Náš měl úder níž
  a v 200–500 Hz o 5–8 dB víc. To byl cvak modulátoru a šum ocasů hi-hatů, které hrají na dobách s kopákem.
  - Kopák je teď čistý sinus (modulátor ztlumený). Úder dává rychlý sjezd výšky po tikách: E3, C3, G2, D#2,
    pak A#1 (`BD_SWEEP`).
  - Ocasy jsou o 3 dB tišší a akcenty hi-hatů na dobách je nezesilují.
- **Tělo virblu:** na dobách 2 a 4 má originál v 80–250 Hz o 15–20 dB víc než náš šumový virbl, to je ten chybějící
  „bas“. Melodický kanál k němu teď hraje sinus s mírnou zpětnou vazbou, který sjede z G3 na D2 za 9 tiků
  (`SNARE_BODY`, nástroj `BODY`). V intru hraje na kanálech 0 a 1 (rozladěné o 15 centů), v riffu na kanálu 3.
  Plocha v riffu má proto jen jeden hlas.
  - Čistý sinus měl málo energie v 200–500 Hz (o 10 dB méně než originál), silné harmonické zase příliš
    (o 10 dB víc). Zpětná vazba 2 a modulátor TL 34 jsou mezi tím.
- **Výsledek v intru:** pásma 40 Hz–16 kHz do ±3 dB od originálu, jen 630–1200 Hz o 6 dB méně (praskot virblu).

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
