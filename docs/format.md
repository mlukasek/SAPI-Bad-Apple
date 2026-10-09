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
- **FFh** = počkat na další VBI (jeden tik 59,94 Hz);
- **FEh** = konec.

Dvojice před prvním FFh jsou nastavení nástrojů. `mus_init` je zapíše při startu s čekáním, které čip
potřebuje (3,3 µs po adrese, 23,5 µs po datech).

**Přehrávání:**
- Přerušení (82C54, 1300,7 Hz) zapíše při každém volání **nejvýš jednu dvojici**. Zápisy jsou od sebe
  aspoň 770 µs, takže na čip se nečeká.
- Každé VBI pustí přehrávač za jedno FFh. První VBI hraje tik 0, stejně jako se při něm zobrazí snímek 0.
- V nejvytíženějším tiku je 21 zápisů. Zápis se tak opozdí nejvýš o 0,97 tiku (simulace v `mkmusic.py`).
- Když není co zapsat, nastaví se `mus_wait` a přehrávač stojí přerušení jen 29 T.

**Kruhový buffer:**
- 1 KB na 3800h–3BFFh (4 stránky); ukazatel se zalamuje přes `RES 2,H`.
- Stránku, kterou přerušení opustilo, doplní hlavní smyčka (`mus_fill`) z RAM disku.
- Přerušení na porty ZRD-1V nikdy nesahá, adresu RAM disku nastavuje jen hlavní smyčka.

**Aranžmá** (`tools/mkmusic.py`, nástroje `tools/opl_patches.py`): rytmický režim OPL2 a 6 melodických hlasů.

| Kanál | Part (stopa MIDI) |
|---|---|
| 0 | zpěv (horní tón) |
| 1 | basa (spodní tón stopy Bass; sub basa, Synth2 a Bass2 hrají totéž v oktávách) |
| 2 | Synth1 (čtvercový lead) |
| 3 | arpeggio |
| 4, 5 | kytara (dva spodní tóny akordu) |
| 6–8 | bicí: BD (35, 36), SD (38–40), HH (42, 69, 82; 46 otevřený), TOM (bonga, kongy), CYM (49) |

**Hlasitost a noty:**
- Hlasitost noty určuje úroveň nosiče podle velocity (polovina z 40·log10(127/v) dB) a útlumu partu.
- Nota, která navazuje na předchozí, ji v témže tiku vypne a znovu zapne. Mezi oběma zápisy je
  aspoň jedno přerušení, takže obálka se spustí znovu.
- Bicí se zapínají bitem v registru BDh a další tik se bit nuluje.
