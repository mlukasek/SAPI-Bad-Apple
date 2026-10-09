# Podněty pro SAPIemu (z dema Bad Apple!!, 2026-10-09)

Tento soubor je pro agenta, který vyvíjí SAPIemu (`E:\SAPI_GIT\SAPIemu`).

Demo Bad Apple!! (`E:\SAPI_GIT\SAPI-Bad-Apple`) se vyvíjí v SAPIemu 0.3.0-alpha (`..\SAPIemu-release`):
- `sapiemu-cli.exe --machine tools\emu\badapple_sapi1v.sapi --mcp --mcp-port 8594`;
- sestava V: JPR-1V 4 MHz, RAM-1V, AND-1V, DSM-1V, ZRD-1V rev 1.1, CGA-1V, MPH-1V.

Starší podněty z portu Prince of Persia (čekací stavy CGA-1V, sníh Bt476 a další) jsou v
`E:\SAPI_GIT\SAPI-Prince-of-Persia\docs\sapiemu-podnety.md`.

## 1. `audio_record`: dlouhé `run_for` ztrácí zvuk (v nahrávce je digitální ticho)

**Co se děje:**
- Nahrávka zvuku MPH-1V (`audio_record`) má v sobě dlouhé úseky přesných nul, když emulace běží jedním
  dlouhým voláním `run_for` (desítky sekund emulovaného času).
- YM3812 přitom zapisuje a hraje dál:
  - `io_log` ukazuje zápisy na porty 56h/57h;
  - simulace stavu registrů z proudu zápisů je v pořádku (nosiče mají TL kolem 0Ch, kanály mají klíč).
- Když se stejný úsek pustí po kouscích (`run_for ms=1000` opakovaně), nahrávka je celá a bez děr.
- Výsledek se při stejném postupu volání opakuje stejně. Mění se ale s tím, jak je běh rozdělený do volání.

**Postup (MCP, stav před voláními: stroj zapnutý a po `resume` běží v reálném čase):**
1. boot CP/M z RAM disku (`tools/emu/cpm.py boot()`), `resume`, `type_text "BADAPPLE\r"`;
2. `run_for ms=300`;
3. `audio_record start=true`;
4. jedno volání `run_for ms=40000`, pak `pause`;
5. `audio_record file=...`.

**Naměřeno** (hladina v dB po 1 s; −120 = samé nuly):

| Varianta | Výsledek |
|---|---|
| jedno `run_for 40000` (dvakrát za sebou, stejně) | `-80 -69 -44 -41 -57 -120 -120 … -120 -30`: zvuk jen v 0–5 s a od 40 s, 5–39 s ticho; délka 40,12 s |
| 40× `run_for 1000` | `-80 -69 -44 -41 -38 -38 -36 -32 -28 -25 … -20 -21 -24`: zvuk celou dobu; délka 43,70 s |

**Celé demo (222 s) jinak rozdělené:** `run_for` po úsecích a pak `run_until` s `timeout_ms=120000` dalo ticho
v 10–25 s a 35–95 s (bloky po 5 s). Po kouscích 1 s je celé demo v pořádku (222,0 s, špička 21 615).

**Druhá drobnost:** se 40 voláními po 1 s měla nahrávka 43,70 s místo 40 s. Mezi voláními stroj zřejmě dál
běží v reálném čase (byl po `resume`) a nahrávka zachytí i to. To je asi v pořádku, ale nikde to nestojí.
Pro zarovnání nahrávky s emulovaným časem by se hodila zmínka v popisu `audio_record`.

**Co by pomohlo:**
- Nahrávka by měla být úplná bez ohledu na délku `run_for` a `run_until`. Synchronní běh je rychlejší než
  reálný čas, takže se nabízí podezření na přetečení bufferu mezi zvukovou kartou a zapisovačem. Je to jen
  odhad, ověřené to není.
- Pokud se nějaké vzorky zahodí, měl by to výsledek `audio_record` nebo `get_log` aspoň ohlásit (počet
  zahozených vzorků). Teď vypadá nahrávka jako platná: `seconds` sedí a ticho se dá splést s chybou programu.

**Obejití v demu:** `tools/emu/run_demo.py` při nahrávání volá `run_for` a `run_until` po 1000 ms.

**Skript na zopakování** (z kořene repa Bad Apple; potřebuje `build\ramdisk.bin` z `build.cmd`). První
argument je délka v ms, druhý velikost kousku; `python rec.py 40000` ukáže díru, `python rec.py 40000 1000`
ne:

```python
import sys, math, os; sys.path.insert(0, 'tools/emu'); sys.path.insert(0, 'tools')
import sapimcp as sm, cpm, audio
ms = int(sys.argv[1]); chunk = int(sys.argv[2]) if len(sys.argv) > 2 else ms
cpm.boot(); sm.call('resume'); sm.call('type_text', text='BADAPPLE\r')
sm.call('run_for', ms=300)
sm.call('audio_record', start=True)
done = 0
while done < ms:
    sm.call('run_for', ms=min(chunk, ms - done)); done += chunk
sm.call('pause')
print(sm.call('audio_record', file=os.path.abspath('work/seg.wav')))
x = audio.decode('work/seg.wav', 2000)
print(' '.join(f'{10*math.log10(sum(v*v for v in x[i:i+2000])/2000+1e-12):.0f}' for i in range(0, len(x), 2000)))
```
