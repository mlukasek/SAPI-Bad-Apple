"""SAPI-1 machine V for running the port headless (only what the port uses), standard library only.

- RAM 64 KB (RAM-1V); MAP register on port 63h (bit 6 MAP1, bit 7 MAP2): with MAP1 = MAP2 = H the
  CGA-1V is at C000-FFFF (RAM-1V has a hole there), with MAP1 = L F800-FFFF is AND-1V (own 2 KB).
- CGA-1V: pages A, B (16 KB), CONFIG at 3FFBh (D0 shown page, D1 CPU page, D7 = acknowledge VBI),
  STATUS read at 3FC0-3FFF (D7 = VBI request, set every 16.68 ms), Bt476 palette at 3FFCh-3FFEh.
- ZRD-1V: 60h data (auto increment of A0-A7 within 256 B), 61h, 62h, 63h (A16-A21 bits 0-5) on an image
  file (build/ramdisk.bin).
- MPH-1V K4 joystick: port 54h (0 = on: D0 down, D1 up, D2 right, D3 left, D4 FL, D5 FR).
- Keyboard (JPR-1V): port 01h D0 = STROBE (0 = key), 02h = code (inverted); a key queue.
- MPH-1V timer interrupt: 82C54 counter 2 (52h, CLK 55930.4 Hz, the divisor only), F2 enabled by IEN bit 7
  (port 54h write), acknowledged on 55h; taken in IM 2 (vector byte FFh) when interrupts are enabled.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, 'tools'))
from cpuz80 import CPUZ80  # noqa: E402

CPU_HZ = 4_000_000
FRAME_T = 66_720          # 16.68 ms at 4 MHz
# waits of CGA-1V in 1/100 T per access, measured with ZRDBENCH on the real SAPI-1 at 4 MHz (2026-10-08): LDIR
# to CGA-1V 23.61 T/B, from it 22.44 (memory 21.18). Off by default (SAPIemu waits about 0.1 T); speed.py --hw
CGA_WAIT_HW = (126, 243)  # read, write


class SapiV:
    def __init__(self, ramdisk_path=None):
        self.ram = bytearray(0x10000)
        self.and1v = bytearray(0x800)
        self.cga = [bytearray(0x4000), bytearray(0x4000)]
        self.cfg = 0
        self.pal_addr = 0
        self.palette = [(0, 0, 0)] * 256
        self.pal_rgb = []
        self.colmask = 0xFF
        self.vbi_req = 0
        self.last_vbi = 0
        self.map = 0
        self.zrd = bytearray(open(ramdisk_path, 'rb').read()) if ramdisk_path else bytearray(0x400000)
        self.zrd_addr = 0
        self.joy = 0xFF
        self.keys = []
        self.key_strobe = False
        self.pit2_div = 0
        self.pit2_lsb = None
        self.ien = 0
        self.next_irq = None          # cycle of the next F2 request (None = timer off)
        self.pit0_start = 0           # counter 0 (CLK0 55930.4 Hz, mode 2 from 65536)
        self.pit0_latch = 0
        self.pit0_msb = False
        self.io_log = None
        self.cga_wait = (0, 0)
        self.cga_frac = 0
        self.cpu = CPUZ80(self)

    # memory --------------------------------------------------------------------------------------------
    def cga_on(self):
        return (self.map & 0xC0) == 0xC0

    def read(self, a):
        if a >= 0xC000:
            if self.cga_on():
                return self.cga_read(a - 0xC000)
            if a >= 0xF800 and not (self.map & 0x40):
                return self.and1v[a - 0xF800]
        return self.ram[a]

    def write(self, a, v):
        if a >= 0xC000:
            if self.cga_on():
                self.cga_write(a - 0xC000, v)
                return
            if a >= 0xF800 and not (self.map & 0x40):
                self.and1v[a - 0xF800] = v
                return
        self.ram[a] = v

    def cga_waits(self, w):
        if w:
            self.cga_frac += w
            self.cpu.cycles += self.cga_frac // 100
            self.cga_frac %= 100

    def cga_read(self, off):
        self.cga_waits(self.cga_wait[0])
        page = self.cga[(self.cfg >> 1) & 1]
        if off >= 0x3FC0:
            self.update_vbi()
            return (page[off] & 0x7F) | (0x80 if self.vbi_req else 0)
        return page[off]

    def cga_write(self, off, v):
        self.cga_waits(self.cga_wait[1])
        page = self.cga[(self.cfg >> 1) & 1]
        page[off] = v
        if off >= 0x3FC0:
            reg = off & 7
            if reg in (3,):           # 3FFB CONFIG (A2 = 0)
                self.update_vbi()
                if v & 0x80:
                    self.vbi_req = 0
                self.cfg = v & 0x7F
            elif reg == 4:            # palette address (write)
                self.pal_addr = v
                self.pal_comp = []
            elif reg == 5:            # palette data R, G, B
                self.pal_comp = getattr(self, 'pal_comp', []) + [v & 0x3F]
                if len(self.pal_comp) == 3:
                    r, g, b = self.pal_comp
                    self.palette[self.pal_addr] = (r * 255 // 63, g * 255 // 63, b * 255 // 63)
                    self.pal_addr = (self.pal_addr + 1) & 0xFF
                    self.pal_comp = []
            elif reg == 6:
                self.colmask = v

    def update_vbi(self):
        t = self.cpu.cycles
        if t - self.last_vbi >= FRAME_T:
            self.last_vbi = t - (t - self.last_vbi) % FRAME_T
            self.vbi_req = 1

    # I/O -------------------------------------------------------------------------------------------------
    def inp(self, port):
        p = port & 0xFF
        if p == 0x60:
            v = self.zrd[self.zrd_addr] if self.zrd_addr < len(self.zrd) else 0xFF
            self.zrd_addr = (self.zrd_addr & ~0xFF) | ((self.zrd_addr + 1) & 0xFF)
            return v
        if p == 0x54:
            return self.joy
        if p == 0x50:                    # 82C54 counter 0 (latched by control word 00h), LSB then MSB
            v = self.pit0_latch
            b = (v >> 8) if self.pit0_msb else (v & 0xFF)
            self.pit0_msb = not self.pit0_msb
            return b
        if p == 0x01:
            return 0xFE if self.keys else 0xFF
        if p == 0x02:
            return (~self.keys[0]) & 0xFF if self.keys else 0xFF
        return 0xFF

    def outp(self, port, v):
        p = port & 0xFF
        if self.io_log is not None:
            self.io_log.append((self.cpu.cycles, p, v))
        if p == 0x60:
            if self.zrd_addr < len(self.zrd):
                self.zrd[self.zrd_addr] = v
            self.zrd_addr = (self.zrd_addr & ~0xFF) | ((self.zrd_addr + 1) & 0xFF)
        elif p == 0x61:
            self.zrd_addr = (self.zrd_addr & ~0xFF) | v
        elif p == 0x62:
            self.zrd_addr = (self.zrd_addr & ~0xFF00) | v << 8
        elif p == 0x63:
            self.zrd_addr = (self.zrd_addr & 0xFFFF) | (v & 0x3F) << 16
            self.map = v & 0xC0
        elif p == 0x01:
            if v & 1 and self.keys:      # ACK
                self.keys.pop(0)
        elif p == 0x52:                  # counter 2: LSB, MSB
            if self.pit2_lsb is None:
                self.pit2_lsb = v
            else:
                self.pit2_div = self.pit2_lsb | v << 8
                self.pit2_lsb = None
                self.timer_restart()
        elif p == 0x54:
            self.ien = v
            self.timer_restart()
        elif p == 0x53:                  # 82C54 control word: counter 0 mode 2 from 65536, latch
            if v == 0x34:
                self.pit0_start = self.cpu.cycles
            elif v == 0x00:
                n = int((self.cpu.cycles - self.pit0_start) * 55930.4 / CPU_HZ)
                self.pit0_latch = (65536 - n % 65536) & 0xFFFF
                self.pit0_msb = False

    def timer_restart(self):
        if self.ien & 0x80 and self.pit2_div:
            self.irq_period = round(self.pit2_div * CPU_HZ / 55930.4)
            self.next_irq = self.cpu.cycles + self.irq_period
        else:
            self.next_irq = None

    def interrupt(self):
        """IM 2 interrupt with the vector byte FFh (the bus floats)."""
        cpu = self.cpu
        self.next_irq += self.irq_period
        if not cpu.iff1 or cpu.im != 2:
            return
        cpu.iff1 = cpu.iff2 = 0
        cpu.push(cpu.pc)
        v = (cpu.i << 8) | 0xFF
        cpu.pc = self.read(v) | self.read((v + 1) & 0xFFFF) << 8
        cpu.cycles += 19

    # running ---------------------------------------------------------------------------------------------
    def load_com(self, path, addr=0x100):
        d = open(path, 'rb').read()
        self.ram[addr:addr + len(d)] = d
        self.cpu.pc = addr
        self.cpu.sp = 0xD600

    def run(self, cycles, check=None):
        cpu = self.cpu
        end = cpu.cycles + cycles
        main = cpu.main
        read = self.read
        while cpu.cycles < end:
            if check is not None and check(cpu):
                return False
            if self.next_irq is not None and cpu.cycles >= self.next_irq:
                self.interrupt()
            op = read(cpu.pc)
            cpu.pc = (cpu.pc + 1) & 0xFFFF
            cpu.r = (cpu.r & 0x80) | ((cpu.r + 1) & 0x7F)
            t = main[op]()         # (not "cycles += main[op]()": the waits of CGA-1V add to cycles inside)
            cpu.cycles += t
        return True

    # screen ----------------------------------------------------------------------------------------------
    def screen_codes(self, page=None):
        """Colour codes 0-3 of the 320 x 200 CGA page (the shown one by default)."""
        if page is None:
            page = self.cfg & 1
        v = self.cga[page]
        out = []
        for y in range(200):
            row = []
            for x in range(320):
                b = v[y * 80 + (x >> 2)]
                k = x & 3
                row.append(((b >> (7 - k)) & 1) | ((b >> (3 - k)) & 1) << 1)
            out.append(row)
        return out

    def screen_rgb(self, page=None):
        """What CGA-1V shows: 200 rows of 320 (r, g, b). Colour index = (P7..P0) & COLMASK, P7..P5 = y >> 5,
        P0 = the dot's bit of D7..D4; CGA mode (CONFIG D2 = 1): P4 = the dot's bit of D3..D0 (P3..P1 the
        rest of the shifted nibble); EGA mode: P4..P1 = D3..D0."""
        if page is None:
            page = self.cfg & 1
        v = self.cga[page]
        cga = self.cfg & 4
        out = []
        for y in range(200):
            row = []
            dom = (y >> 5) << 5
            for x in range(320):
                b = v[y * 80 + (x >> 2)]
                k = x & 3
                p0 = (b >> (7 - k)) & 1
                if cga:
                    low = ((b << k) & 0x0F) << 1        # D3..D0 shifted left by k: P4 = D(3-k)
                else:
                    low = (b & 0x0F) << 1
                row.append(self.palette[(dom | low | p0) & self.colmask])
            out.append(row)
        return out

    def screen_png(self, path, page=None):
        import png
        png.write(path, 320, 200, self.screen_rgb(page))
