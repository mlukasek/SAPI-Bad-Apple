# Formát videa

Kódování: `tools/vcodec.py`, tabulka operačních kódů: `tools/vfmt.py`, dekodér v Z80: `sapi/video.asm`
a generované obsluhy `sapi/gen/vdec.asm` (`tools/mkvdec.py`).

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
| `MX(d,a,b)` | 1 + 1 | totéž s m = 3–255 v dalším bajtu (48 kódů) |
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
