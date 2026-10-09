# Formát dat

- **Video:** kódování `tools/vcodec.py`, tabulka operačních kódů `tools/vfmt.py`. Dekodér v Z80 je
  `sapi/video.asm` a generované obsluhy `sapi/gen/vdec.asm` (`tools/mkvdec.py`).
- **Hudba:** `tools/mkmusic.py` → `sapi/music.asm` a přerušení v `sapi/badapple.asm`.
- **Soubor na RAM disku:** `tools/mkdat.py`.

## BADAPPLE.DAT

Leží souvisle od bloku 8 RAM disku (adresa 10000h ZRD-1V). Hlavička:

| Posun | Obsah |
|---|---|
| 0 | `BADAPPL1` |
| 8 | posun videa (3 B, násobek 256) |
| 11 | délka videa (3 B) |
| 14 | posun hudby (3 B, násobek 256) |
| 17 | délka hudby (3 B) |

Video je zarovnané tak, že žádný snímek nepřekročí hranici 32 KB proudu (kruhový buffer 4000h–BFFFh).
Před takovým snímkem je FFh a snímek začíná až od hranice.

# Video

## Obraz

- 256×192 bodů, 1 bit na bod (logicky bílá/černá), uprostřed obrazovky CGA-1V 320×200 v režimu CGA
  (2 bity na bod, bílá = oba bity).
- Řádek obrazu y leží na `C000h + (y + 4) × 80 + 8`, tedy 4 řádky shora a 8 bajtů (32 bodů) zleva.
- Bod p bajtu (0 = vlevo) jsou bity 7-p a 3-p.

## Časování

- Snímek se zobrazí při VBI (59,94 Hz), normálně každé druhé VBI (29,97 fps).
- Dekodér kreslí do skryté stránky, kde je snímek n-2. Začít může, až je zobrazený snímek n-1.
- Kodér počítá cykly dekodéru (cyklový model ověřený v modelu Z80, `tools/vtest.py`, s čekáním CGA-1V
  naměřeným na HW).
  - Snímek, který se nestihne, se zobrazí o VBI později.
  - Další snímek se pak vezme ze zdroje podle skutečného času, takže se zpoždění nehromadí.

## Proud

Pro každý snímek:
- **1 B hlavička:** počet VBI od předchozího snímku (0 = konec videa);
- **tělo:** operace `CLR`, pak stopy, nakonec `END`.

**Stopa** je svislý řetěz intervalů XOR, jeden interval na řádek.
- Stav dekodéru je DE = adresa levého bajtu intervalu v předchozím řádku stopy.
- Každý řádek je jeden kód s krokem `DE += 80 + d`, kde d ∈ {-1, 0, 1}.

| Kód | Bajty | Význam |
|---|---|---|
| `S(d,a,b)` | 1 | XOR jednoho bajtu maskou bodů a..b (30 kódů) |
| `M(d,a,b,m)` | 1 | levý bajt body a..3, m = 0–2 celých bajtů (CPL), pravý bajt body 0..b (144 kódů) |
| `MX(d,a,b)` | 1 + 1 | totéž s m = 3–62, prostředek se ale **vyplní** barvou (00h nebo FFh); další bajt = 2 × (62 − m) + barva, vstup do rozvinutého plnění `vfill` (3400h). Kodér ho použije, jen když je prostředek ve staré stránce jednobarevný (48 kódů) |
| `TRACKA` | 1 + 2 | nová stopa: DE (adresa nad prvním řádkem) |
| `TRACKR` | 1 + 1 | nová stopa: DE = začátek předchozí stopy + bajt (stopy jsou seřazené podle adresy) |
| `CLR` | 1 + 4 | adresa, počet řádků, barva: vyplní řádky po 64 B (PUSH, mezi řádky povolené přerušení) |
| `END` | 1 | konec snímku (`ret`) |

**Rozskok:** obsluha kódu N leží na adrese `(vjt[N] << 8) | N`, takže stojí
`ld a,(bc) / inc bc / ld l,a / ld h,HI_VJT / ld h,(hl) / jp (hl)` = 35 T. BC je ukazatel do proudu.

**Ceny řádku stopy** (4 MHz, bez čekání CGA-1V, s rozskokem):

| Řádek stopy | Cena |
|---|---|
| S | 81 T |
| M, m = 0 | 112 T |
| M, další bajt | +24 T |
| CLR | ≈ 570 T na řádek |

**Kodér:**
- Pro každý řádek volí mezi XOR proti stránce a smazáním řádku (`CLR`) s nakreslením úseků nového obrazu,
  podle toho, co je levnější.
- Intervaly sousedních řádků spojí do stopy, když se levý bajt posune nejvýš o 1.
- Mrtvá zóna: změna úzká 1 bod se neposílá, takže chvějící se hrana se nepřekresluje. Ve snímcích, které by
  se nestihly, roste mrtvá zóna až na 3 body.

# Hudba

**Proud** (`build/music.bin`) jsou zápisy do registrů YM3812:
- dvojice (registr, hodnota);
- **FFh** = další tik (jmenovitě jeden VBI, 59,94 Hz);
- **FEh** = konec.

Dvojice před prvním FFh jsou nastavení nástrojů. `mus_init` je zapíše při startu s čekáním, které čip
potřebuje (3,3 µs po adrese, 23,5 µs po datech).

**Přehrávání** (`sapi/music.asm`, přerušení v `sapi/badapple.asm`):
- Přerušení (82C54, 1300,7 Hz) zapíše při každém volání **nejvýš jednu dvojici**. Zápisy jsou od sebe
  aspoň 770 µs, takže na čip se nečeká.
- **Tiky odpočítává přerušení:** `mus_step` volání na tik (8.8 bitů), jmenovitě 21,70. Bajt `mus_st` nese
  odpočet (D0–D6) a příznak „jsou dvojice k zápisu“ (D7). Když není co dělat, stojí hudba přerušení 47 T.
- Tik, který přijde uprostřed dávky zápisů, se jen započítá (`mus_pend`) a přehrávač za FFh pokračuje hned.
- Simulace v `mkmusic.py`: v nejvytíženějším tiku je 26 zápisů, zápis se opozdí nejvýš o 1,2 tiku.
  Zápisy bicích jdou v tiku první.

**Synchronizace s obrazem:**
- **Hodiny videa:** každý VBI je posune o jeden, ale ne tehdy, když už měl být ukázán další snímek a ještě
  není hotový (`pend`, `next_flip`). Opožděný snímek se ukáže hned, jak je hotový, a další snímky drží
  odstup od skutečného přepnutí (`flip_at`), takže video se při zdržení zpomalí a nedohání.
- **`mus_lead`** = odehrané tiky minus kroky hodin videa. V každém VBI podle něj přerušení vybere rychlost
  hudby z tabulky `mus_rate`:

  | `mus_lead` | ≤ −3 | −2 | −1 | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | ≥ 10 |
  |---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
  | rychlost | 1,06 | 1,04 | 1,02 | 1,005 | 0,995 | 0,96 | 0,92 | 0,88 | 0,85 | 0,82 | 0,79 | 0,76 | 0,73 | 0,70 |

- Když obraz stíhá, drží se hudba VBI na ±0,5 % (v SAPIemu je `mus_lead` celou dobu 1). Opožděný snímek
  zastaví hodiny videa a hudba plynule zpomalí: o pár procent, když se obraz zdrží jen občas, nejvýš
  o 30 %, když je pozadu hodně. Výška tónů se nemění, jen tempo.

**Kruhový buffer:**
- 1 KB na 3800h–3BFFh (4 stránky); ukazatel se zalamuje přes `RES 2,H`.
- Stránku, kterou přerušení opustilo, doplní hlavní smyčka (`mus_fill`) z RAM disku.
- Přerušení na porty ZRD-1V nikdy nesahá, adresu RAM disku nastavuje jen hlavní smyčka.

**Čas v přerušení a video:** kodér videa (`tools/vcodec.py`) bere čas přerušení pro každý VBI zvlášť z proudu
hudby: 4550 T základ (21,7 nečinných volání po 183 T, VBI, tik) a 168 T za každý zápis. Proto se video
kóduje až po hudbě (`build.cmd video`).

**Aranžmá** (`music/badapple.py`, nástroje `tools/opl_patches.py`, přehrávač not `tools/mkmusic.py`): vlastní,
pro 6 melodických hlasů a rytmický režim OPL2. Melodie, akordy a stavba jsou přepsané ze zvuku videa
(`tools/transcribe.py`, [rozhodnuti.md](rozhodnuti.md)).

| Kanál | Part |
|---|---|
| 0 | hlas (melodie zpěvu); v riffu kytara (linka basy, rozladěná) |
| 1 | basa: osminy s důrazem mezi doby, v riffu šestnáctinová linka (`DRIVE`), v tichých místech sub basa |
| 2 | ozvěna hlasu (o tečkovanou osminu později) nebo druhý hlas pod melodií; v riffu druhá kytara |
| 3, 4 | plocha (pad), ve sloce a v tichém refrénu s kanálem 5 třemi hlasy; v riffu 3 tělo virblu, 4 plocha |
| 0, 1 v intru | tělo virblu (`SNARE_BODY`) |
| 3–5 v intru | šumové ocasy bicích (dozvuk virblu, hi-hatů a crashe: `INTRO_TAILS`) |
| 5 | arpeggio (pluck) v refrénech, třetí hlas plochy; v riffu sinus pod basou (`DEEP`) |
| 6–8 | bicí: BD s klesající výškou (A#1), SD, HH jako zavřený a otevřený hi-hat i crash, TOM ve vířeních; CYM se nehraje (kovový bez šumu) |

**Přehrávač not** (`tools/mkmusic.py`):
- Krok je šestnáctina (138 BPM), takt 0 začíná 1,39 s po prvním VBI. Tik = zaokrouhlený čas × 59,94.
- Úroveň nosiče = nástroj + útlum noty + automatizace kanálu (`level`); úroveň modulátoru = nástroj +
  automatizace `bright` (tmavší/jasnější zvuk, „filtr“).
- **Vibrato až po chvíli:** bit VIB se nastaví po `vib` krocích noty a s další notou se vrátí.
- Legato bez nového náběhu (`legato`, `glide` = sklouznutí výšky po tikách).
- Nota, po které hned následuje další, se vypne o tik dřív, aby v tiku náběhů nebyly i vypínací zápisy.
- Změna nástroje se zapíše až 24 tiků předem, když kanál nehraje.
- Kopák: kanál 6 sjede po tikách z E3 přes C3, G2 a D#2 na A#1 (`BD_SWEEP`). Drží 17 tiků, pak přehrávač
  vynuluje jeho bit v BDh (`BD_GATE`), pokud mezitím nepřišel nový úder.
- HH, otevřený HH a crash jsou týž operátor s jiným doznětím: přepnutí stojí dva zápisy (DR/AR, SL/RR).
- Kanály 7 a 8 jsou na 4,5 a 1,2 kHz (`RHYTHM_HZ`): virbl a hi-hat jsou pak šum, ne kovový tón. TOM kanál 8 přeladí,
  další úder ostatních bubnů ho vrátí.
- Úder nastaví bit v BDh a nechá ho: buben dozní svou obálkou. Nový úder téhož bubnu bit nejdřív vynuluje.
- `MIX` a `DETUNE` v partituře: útlum kanálů pro celou skladbu a rozladění doprovodných hlasů.
- Bicí se zapínají bitem v registru BDh; nový úder téhož nástroje bit nejdřív vynuluje.
