"""Z80 CPU for running the port headless (tools/z80/sapi.py), standard library only.

Documented instructions (with the documented flags S Z H P/V N C; X and Y follow the result as on a real
Z80 where it is simple), IX/IY with displacement, IXh/IXl/IYh/IYl, CB/ED/DD/FD/DDCB/FDCB.
T-states per instruction (no contention). The bus: read(a), write(a, v), inp(port16), outp(port16, v).
Checked against SAPIemu with the drawing tests (tools/emu/test_lay.py) and the game.
"""

FS, FZ, FY, FH, FX, FP, FN, FC = 0x80, 0x40, 0x20, 0x10, 0x08, 0x04, 0x02, 0x01

PARITY = [0] * 256
for _v in range(256):
    PARITY[_v] = FP if bin(_v).count('1') % 2 == 0 else 0
SZP = [(v & (FS | FY | FX)) | (FZ if v == 0 else 0) | PARITY[v] for v in range(256)]
SZ = [(v & (FS | FY | FX)) | (FZ if v == 0 else 0) for v in range(256)]


class Halt(Exception):
    pass


class CPUZ80:
    def __init__(self, bus):
        self.bus = bus
        self.a = self.f = self.b = self.c = self.d = self.e = self.h = self.l = 0
        self.a_ = self.f_ = self.b_ = self.c_ = self.d_ = self.e_ = self.h_ = self.l_ = 0
        self.ix = self.iy = 0xFFFF
        self.sp = 0xFFFF
        self.pc = 0
        self.i = self.r = 0
        self.iff1 = self.iff2 = 0
        self.im = 0
        self.halted = False
        self.cycles = 0
        self._build()

    # 16-bit register helpers
    def get_hl(self): return self.h << 8 | self.l
    def set_hl(self, v): self.h = (v >> 8) & 0xFF; self.l = v & 0xFF
    def get_bc(self): return self.b << 8 | self.c
    def set_bc(self, v): self.b = (v >> 8) & 0xFF; self.c = v & 0xFF
    def get_de(self): return self.d << 8 | self.e
    def set_de(self, v): self.d = (v >> 8) & 0xFF; self.e = v & 0xFF
    def get_af(self): return self.a << 8 | self.f
    def set_af(self, v): self.a = (v >> 8) & 0xFF; self.f = v & 0xFF

    def push(self, v):
        self.sp = (self.sp - 1) & 0xFFFF
        self.bus.write(self.sp, (v >> 8) & 0xFF)
        self.sp = (self.sp - 1) & 0xFFFF
        self.bus.write(self.sp, v & 0xFF)

    def pop(self):
        rd = self.bus.read
        lo = rd(self.sp)
        hi = rd((self.sp + 1) & 0xFFFF)
        self.sp = (self.sp + 2) & 0xFFFF
        return hi << 8 | lo

    def step(self):
        op = self.bus.read(self.pc)
        self.pc = (self.pc + 1) & 0xFFFF
        self.r = (self.r & 0x80) | ((self.r + 1) & 0x7F)
        t = self.main[op]()
        self.cycles += t

    # --- build tables -------------------------------------------------------------------------------------
    def _build(self):
        cpu = self
        bus = self.bus
        rd = bus.read
        wr = bus.write

        def fetch():
            v = rd(cpu.pc)
            cpu.pc = (cpu.pc + 1) & 0xFFFF
            return v

        def fetch16():
            lo = rd(cpu.pc)
            hi = rd((cpu.pc + 1) & 0xFFFF)
            cpu.pc = (cpu.pc + 2) & 0xFFFF
            return hi << 8 | lo

        def rd16(a):
            return rd(a) | rd((a + 1) & 0xFFFF) << 8

        def wr16(a, v):
            wr(a, v & 0xFF)
            wr((a + 1) & 0xFFFF, (v >> 8) & 0xFF)

        def sdisp():
            d = fetch()
            return d - 256 if d & 0x80 else d

        # register access by index (0 B, 1 C, 2 D, 3 E, 4 H, 5 L, 6 (HL), 7 A)
        RN = ['b', 'c', 'd', 'e', 'h', 'l', None, 'a']

        def getr(i):
            if i == 6:
                return rd(cpu.h << 8 | cpu.l)
            return getattr(cpu, RN[i])

        def setr(i, v):
            if i == 6:
                wr(cpu.h << 8 | cpu.l, v)
            else:
                setattr(cpu, RN[i], v)

        # ALU
        def add8(v, carry=0):
            a = cpu.a
            r = a + v + carry
            f = SZ[r & 0xFF] | ((a ^ v ^ r) & FH) | (FC if r > 0xFF else 0)
            if (~(a ^ v) & (a ^ r)) & 0x80:
                f |= FP
            cpu.f = f
            cpu.a = r & 0xFF

        def sub8(v, carry=0, store=True):
            a = cpu.a
            r = a - v - carry
            f = SZ[r & 0xFF] | FN | ((a ^ v ^ r) & FH) | (FC if r < 0 else 0)
            if ((a ^ v) & (a ^ r)) & 0x80:
                f |= FP
            if not store:
                f = (f & ~(FY | FX)) | (v & (FY | FX))
            cpu.f = f
            if store:
                cpu.a = r & 0xFF

        def and8(v):
            cpu.a &= v
            cpu.f = SZP[cpu.a] | FH

        def xor8(v):
            cpu.a ^= v
            cpu.f = SZP[cpu.a]

        def or8(v):
            cpu.a |= v
            cpu.f = SZP[cpu.a]

        def alu(op, v):
            if op == 0:
                add8(v)
            elif op == 1:
                add8(v, cpu.f & FC)
            elif op == 2:
                sub8(v)
            elif op == 3:
                sub8(v, cpu.f & FC)
            elif op == 4:
                and8(v)
            elif op == 5:
                xor8(v)
            elif op == 6:
                or8(v)
            else:
                sub8(v, 0, False)

        def inc8(v):
            r = (v + 1) & 0xFF
            cpu.f = (cpu.f & FC) | SZ[r] | (FH if (v & 0x0F) == 0x0F else 0) | (FP if v == 0x7F else 0)
            return r

        def dec8(v):
            r = (v - 1) & 0xFF
            cpu.f = (cpu.f & FC) | SZ[r] | FN | (FH if (v & 0x0F) == 0 else 0) | (FP if v == 0x80 else 0)
            return r

        def add16(a, v):
            r = a + v
            cpu.f = (cpu.f & (FS | FZ | FP)) | (FC if r > 0xFFFF else 0) | (((a ^ v ^ r) >> 8) & FH) | \
                ((r >> 8) & (FY | FX))
            return r & 0xFFFF

        def adc16(v):
            a = cpu.get_hl()
            c = cpu.f & FC
            r = a + v + c
            f = (FC if r > 0xFFFF else 0) | (((a ^ v ^ r) >> 8) & FH) | ((r >> 8) & (FS | FY | FX))
            if (r & 0xFFFF) == 0:
                f |= FZ
            if (~(a ^ v) & (a ^ r)) & 0x8000:
                f |= FP
            cpu.f = f
            cpu.set_hl(r & 0xFFFF)

        def sbc16(v):
            a = cpu.get_hl()
            c = cpu.f & FC
            r = a - v - c
            f = FN | (FC if r < 0 else 0) | (((a ^ v ^ r) >> 8) & FH) | ((r >> 8) & (FS | FY | FX))
            if (r & 0xFFFF) == 0:
                f |= FZ
            if ((a ^ v) & (a ^ r)) & 0x8000:
                f |= FP
            cpu.f = f
            cpu.set_hl(r & 0xFFFF)

        def cond(cc):
            f = cpu.f
            return [not f & FZ, f & FZ, not f & FC, f & FC, not f & FP, f & FP, not f & FS, f & FS][cc]

        # rotate / shift (CB)
        def rot(op, v):
            c = cpu.f & FC
            if op == 0:      # rlc
                r = ((v << 1) | (v >> 7)) & 0xFF
                nc = v >> 7
            elif op == 1:    # rrc
                r = ((v >> 1) | (v << 7)) & 0xFF
                nc = v & 1
            elif op == 2:    # rl
                r = ((v << 1) | c) & 0xFF
                nc = v >> 7
            elif op == 3:    # rr
                r = (v >> 1) | (c << 7)
                nc = v & 1
            elif op == 4:    # sla
                r = (v << 1) & 0xFF
                nc = v >> 7
            elif op == 5:    # sra
                r = (v >> 1) | (v & 0x80)
                nc = v & 1
            elif op == 6:    # sll (undocumented)
                r = ((v << 1) | 1) & 0xFF
                nc = v >> 7
            else:            # srl
                r = v >> 1
                nc = v & 1
            cpu.f = SZP[r] | (FC if nc else 0)
            return r

        main = [None] * 256

        def op_nop():
            return 4
        main[0x00] = op_nop

        # ld rr,nn / ld (rr),a / inc/dec rr / add hl,rr
        def make_ld_rr(pair):
            def f():
                v = fetch16()
                if pair == 0:
                    cpu.set_bc(v)
                elif pair == 1:
                    cpu.set_de(v)
                elif pair == 2:
                    cpu.set_hl(v)
                else:
                    cpu.sp = v
                return 10
            return f

        def get_rr(pair):
            return [cpu.get_bc, cpu.get_de, cpu.get_hl, lambda: cpu.sp][pair]()

        def set_rr(pair, v):
            if pair == 3:
                cpu.sp = v & 0xFFFF
            else:
                [cpu.set_bc, cpu.set_de, cpu.set_hl][pair](v & 0xFFFF)

        for p in range(4):
            main[0x01 + p * 16] = make_ld_rr(p)

            def inc_rr(p=p):
                set_rr(p, get_rr(p) + 1)
                return 6

            def dec_rr(p=p):
                set_rr(p, get_rr(p) - 1)
                return 6

            def add_hl(p=p):
                cpu.set_hl(add16(cpu.get_hl(), get_rr(p)))
                return 11
            main[0x03 + p * 16] = inc_rr
            main[0x0B + p * 16] = dec_rr
            main[0x09 + p * 16] = add_hl

        def ld_bc_a():
            wr(cpu.get_bc(), cpu.a)
            return 7

        def ld_de_a():
            wr(cpu.get_de(), cpu.a)
            return 7

        def ld_a_bc():
            cpu.a = rd(cpu.get_bc())
            return 7

        def ld_a_de():
            cpu.a = rd(cpu.get_de())
            return 7
        main[0x02], main[0x12], main[0x0A], main[0x1A] = ld_bc_a, ld_de_a, ld_a_bc, ld_a_de

        def ld_nn_hl():
            wr16(fetch16(), cpu.get_hl())
            return 16

        def ld_hl_nn():
            cpu.set_hl(rd16(fetch16()))
            return 16

        def ld_nn_a():
            wr(fetch16(), cpu.a)
            return 13

        def ld_a_nn():
            cpu.a = rd(fetch16())
            return 13
        main[0x22], main[0x2A], main[0x32], main[0x3A] = ld_nn_hl, ld_hl_nn, ld_nn_a, ld_a_nn

        # inc r / dec r / ld r,n
        for r in range(8):
            def inc_r(r=r):
                setr(r, inc8(getr(r)))
                return 11 if r == 6 else 4

            def dec_r(r=r):
                setr(r, dec8(getr(r)))
                return 11 if r == 6 else 4

            def ld_r_n(r=r):
                setr(r, fetch())
                return 10 if r == 6 else 7
            main[0x04 + r * 8] = inc_r
            main[0x05 + r * 8] = dec_r
            main[0x06 + r * 8] = ld_r_n

        def rlca():
            a = cpu.a
            cpu.a = ((a << 1) | (a >> 7)) & 0xFF
            cpu.f = (cpu.f & (FS | FZ | FP)) | (cpu.a & (FY | FX)) | (a >> 7)
            return 4

        def rrca():
            a = cpu.a
            cpu.a = ((a >> 1) | (a << 7)) & 0xFF
            cpu.f = (cpu.f & (FS | FZ | FP)) | (cpu.a & (FY | FX)) | (a & 1)
            return 4

        def rla():
            a = cpu.a
            cpu.a = ((a << 1) | (cpu.f & FC)) & 0xFF
            cpu.f = (cpu.f & (FS | FZ | FP)) | (cpu.a & (FY | FX)) | (a >> 7)
            return 4

        def rra():
            a = cpu.a
            cpu.a = (a >> 1) | ((cpu.f & FC) << 7)
            cpu.f = (cpu.f & (FS | FZ | FP)) | (cpu.a & (FY | FX)) | (a & 1)
            return 4
        main[0x07], main[0x0F], main[0x17], main[0x1F] = rlca, rrca, rla, rra

        def ex_af():
            cpu.a, cpu.a_ = cpu.a_, cpu.a
            cpu.f, cpu.f_ = cpu.f_, cpu.f
            return 4
        main[0x08] = ex_af

        def djnz():
            d = sdisp()
            cpu.b = (cpu.b - 1) & 0xFF
            if cpu.b:
                cpu.pc = (cpu.pc + d) & 0xFFFF
                return 13
            return 8
        main[0x10] = djnz

        def jr():
            d = sdisp()
            cpu.pc = (cpu.pc + d) & 0xFFFF
            return 12
        main[0x18] = jr
        for cc in range(4):
            def jr_cc(cc=cc):
                d = sdisp()
                if cond(cc):
                    cpu.pc = (cpu.pc + d) & 0xFFFF
                    return 12
                return 7
            main[0x20 + cc * 8] = jr_cc

        def daa():
            a = cpu.a
            f = cpu.f
            corr = 0
            c = f & FC
            if (f & FH) or (a & 0x0F) > 9:
                corr |= 0x06
            if c or a > 0x99:
                corr |= 0x60
                c = FC
            if f & FN:
                r = (a - corr) & 0xFF
                h = FH if (f & FH) and (a & 0x0F) < 6 else 0
            else:
                r = (a + corr) & 0xFF
                h = FH if (a & 0x0F) > 9 else 0
            cpu.a = r
            cpu.f = SZP[r] | h | (f & FN) | c
            return 4
        main[0x27] = daa

        def cpl():
            cpu.a ^= 0xFF
            cpu.f = (cpu.f & (FS | FZ | FP | FC)) | FH | FN | (cpu.a & (FY | FX))
            return 4
        main[0x2F] = cpl

        def scf():
            cpu.f = (cpu.f & (FS | FZ | FP)) | FC | (cpu.a & (FY | FX))
            return 4

        def ccf():
            c = cpu.f & FC
            cpu.f = (cpu.f & (FS | FZ | FP)) | (FH if c else 0) | (0 if c else FC) | (cpu.a & (FY | FX))
            return 4
        main[0x37], main[0x3F] = scf, ccf

        # ld r,r'
        for dst in range(8):
            for src in range(8):
                code = 0x40 + dst * 8 + src
                if code == 0x76:
                    def halt():
                        cpu.halted = True
                        cpu.pc = (cpu.pc - 1) & 0xFFFF
                        return 4
                    main[code] = halt
                    continue

                def ld_rr_(dst=dst, src=src):
                    setr(dst, getr(src))
                    return 7 if (dst == 6 or src == 6) else 4
                main[code] = ld_rr_

        # alu a,r
        for op in range(8):
            for src in range(8):
                def alu_r(op=op, src=src):
                    alu(op, getr(src))
                    return 7 if src == 6 else 4
                main[0x80 + op * 8 + src] = alu_r

            def alu_n(op=op):
                alu(op, fetch())
                return 7
            main[0xC6 + op * 8] = alu_n

        # ret cc, pop, jp cc, jp, call cc, push, rst, ret, call
        for cc in range(8):
            def ret_cc(cc=cc):
                if cond(cc):
                    cpu.pc = cpu.pop()
                    return 11
                return 5

            def jp_cc(cc=cc):
                a = fetch16()
                if cond(cc):
                    cpu.pc = a
                return 10

            def call_cc(cc=cc):
                a = fetch16()
                if cond(cc):
                    cpu.push(cpu.pc)
                    cpu.pc = a
                    return 17
                return 10

            def rst(n=cc * 8):
                cpu.push(cpu.pc)
                cpu.pc = n
                return 11
            main[0xC0 + cc * 8] = ret_cc
            main[0xC2 + cc * 8] = jp_cc
            main[0xC4 + cc * 8] = call_cc
            main[0xC7 + cc * 8] = rst
        for p in range(4):
            def pop_rr(p=p):
                v = cpu.pop()
                if p == 3:
                    cpu.set_af(v)
                else:
                    set_rr(p, v)
                return 10

            def push_rr(p=p):
                cpu.push(cpu.get_af() if p == 3 else get_rr(p))
                return 11
            main[0xC1 + p * 16] = pop_rr
            main[0xC5 + p * 16] = push_rr

        def ret():
            cpu.pc = cpu.pop()
            return 10

        def jp():
            cpu.pc = fetch16()
            return 10

        def call():
            a = fetch16()
            cpu.push(cpu.pc)
            cpu.pc = a
            return 17
        main[0xC9], main[0xC3], main[0xCD] = ret, jp, call

        def out_n():
            n = fetch()
            bus.outp(cpu.a << 8 | n, cpu.a)
            return 11

        def in_n():
            n = fetch()
            cpu.a = bus.inp(cpu.a << 8 | n)
            return 11
        main[0xD3], main[0xDB] = out_n, in_n

        def exx():
            cpu.b, cpu.b_ = cpu.b_, cpu.b
            cpu.c, cpu.c_ = cpu.c_, cpu.c
            cpu.d, cpu.d_ = cpu.d_, cpu.d
            cpu.e, cpu.e_ = cpu.e_, cpu.e
            cpu.h, cpu.h_ = cpu.h_, cpu.h
            cpu.l, cpu.l_ = cpu.l_, cpu.l
            return 4
        main[0xD9] = exx

        def ex_sp_hl():
            v = rd16(cpu.sp)
            wr16(cpu.sp, cpu.get_hl())
            cpu.set_hl(v)
            return 19

        def jp_hl():
            cpu.pc = cpu.get_hl()
            return 4

        def ex_de_hl():
            cpu.d, cpu.h = cpu.h, cpu.d
            cpu.e, cpu.l = cpu.l, cpu.e
            return 4

        def ld_sp_hl():
            cpu.sp = cpu.get_hl()
            return 6

        def di():
            cpu.iff1 = cpu.iff2 = 0
            return 4

        def ei():
            cpu.iff1 = cpu.iff2 = 1
            return 4
        main[0xE3], main[0xE9], main[0xEB], main[0xF9], main[0xF3], main[0xFB] = \
            ex_sp_hl, jp_hl, ex_de_hl, ld_sp_hl, di, ei

        # CB
        cb = [None] * 256
        for code in range(256):
            x, y, z = code >> 6, (code >> 3) & 7, code & 7

            def cbop(x=x, y=y, z=z):
                v = getr(z)
                if x == 0:
                    setr(z, rot(y, v))
                elif x == 1:
                    r = v & (1 << y)
                    f = (cpu.f & FC) | FH | (FZ | FP if not r else 0) | (v & (FY | FX))
                    if y == 7 and r:
                        f |= FS
                    cpu.f = f
                    return 12 if z == 6 else 8
                elif x == 2:
                    setr(z, v & ~(1 << y))
                else:
                    setr(z, v | (1 << y))
                return 15 if z == 6 else 8
            cb[code] = cbop

        def prefix_cb():
            cpu.r = (cpu.r & 0x80) | ((cpu.r + 1) & 0x7F)
            return cb[fetch()]()
        main[0xCB] = prefix_cb

        # ED
        ed = {}
        for p in range(4):
            def sbc_hl(p=p):
                sbc16(get_rr(p))
                return 15

            def adc_hl(p=p):
                adc16(get_rr(p))
                return 15

            def ld_nn_rr(p=p):
                wr16(fetch16(), get_rr(p))
                return 20

            def ld_rr_nn(p=p):
                set_rr(p, rd16(fetch16()))
                return 20
            ed[0x42 + p * 16] = sbc_hl
            ed[0x4A + p * 16] = adc_hl
            ed[0x43 + p * 16] = ld_nn_rr
            ed[0x4B + p * 16] = ld_rr_nn
        for r in range(8):
            def in_r_c(r=r):
                v = bus.inp(cpu.get_bc())
                if r != 6:
                    setattr(cpu, RN[r], v)
                cpu.f = (cpu.f & FC) | SZP[v]
                return 12

            def out_c_r(r=r):
                bus.outp(cpu.get_bc(), 0 if r == 6 else getattr(cpu, RN[r]))
                return 12
            ed[0x40 + r * 8] = in_r_c
            ed[0x41 + r * 8] = out_c_r

        def neg():
            v = cpu.a
            cpu.a = 0
            sub8(v)
            return 8
        for k in (0x44, 0x4C, 0x54, 0x5C, 0x64, 0x6C, 0x74, 0x7C):
            ed[k] = neg

        def retn():
            cpu.iff1 = cpu.iff2
            cpu.pc = cpu.pop()
            return 14
        ed[0x45] = ed[0x4D] = retn

        def im0():
            cpu.im = 0
            return 8

        def im1():
            cpu.im = 1
            return 8

        def im2():
            cpu.im = 2
            return 8
        ed[0x46], ed[0x56], ed[0x5E] = im0, im1, im2

        def ld_i_a():
            cpu.i = cpu.a
            return 9

        def ld_r_a():
            cpu.r = cpu.a
            return 9

        def ld_a_i():
            cpu.a = cpu.i
            cpu.f = (cpu.f & FC) | SZ[cpu.a] | (FP if cpu.iff2 else 0)
            return 9

        def ld_a_r():
            cpu.a = cpu.r
            cpu.f = (cpu.f & FC) | SZ[cpu.a] | (FP if cpu.iff2 else 0)
            return 9
        ed[0x47], ed[0x4F], ed[0x57], ed[0x5F] = ld_i_a, ld_r_a, ld_a_i, ld_a_r

        def rrd():
            a = cpu.get_hl()
            m = rd(a)
            wr(a, ((cpu.a << 4) | (m >> 4)) & 0xFF)
            cpu.a = (cpu.a & 0xF0) | (m & 0x0F)
            cpu.f = (cpu.f & FC) | SZP[cpu.a]
            return 18

        def rld():
            a = cpu.get_hl()
            m = rd(a)
            wr(a, ((m << 4) | (cpu.a & 0x0F)) & 0xFF)
            cpu.a = (cpu.a & 0xF0) | (m >> 4)
            cpu.f = (cpu.f & FC) | SZP[cpu.a]
            return 18
        ed[0x67], ed[0x6F] = rrd, rld

        # block instructions
        def ldx(step, repeat):
            def f():
                v = rd(cpu.get_hl())
                wr(cpu.get_de(), v)
                cpu.set_hl(cpu.get_hl() + step)
                cpu.set_de(cpu.get_de() + step)
                bc = (cpu.get_bc() - 1) & 0xFFFF
                cpu.set_bc(bc)
                n = (v + cpu.a) & 0xFF
                cpu.f = (cpu.f & (FS | FZ | FC)) | (FP if bc else 0) | (n & FX) | ((n << 4) & FY)
                if repeat and bc:
                    cpu.pc = (cpu.pc - 2) & 0xFFFF
                    return 21
                return 16
            return f

        def cpx(step, repeat):
            def f():
                v = rd(cpu.get_hl())
                r = (cpu.a - v) & 0xFF
                cpu.set_hl(cpu.get_hl() + step)
                bc = (cpu.get_bc() - 1) & 0xFFFF
                cpu.set_bc(bc)
                h = (cpu.a ^ v ^ r) & FH
                cpu.f = (cpu.f & FC) | SZ[r] & (FS | FZ) | FN | h | (FP if bc else 0)
                if repeat and bc and r:
                    cpu.pc = (cpu.pc - 2) & 0xFFFF
                    return 21
                return 16
            return f

        def inx(step, repeat):
            def f():
                v = bus.inp(cpu.get_bc())
                wr(cpu.get_hl(), v)
                cpu.set_hl(cpu.get_hl() + step)
                cpu.b = (cpu.b - 1) & 0xFF
                cpu.f = SZ[cpu.b] | FN
                if repeat and cpu.b:
                    cpu.pc = (cpu.pc - 2) & 0xFFFF
                    return 21
                return 16
            return f

        def outx(step, repeat):
            def f():
                v = rd(cpu.get_hl())
                cpu.b = (cpu.b - 1) & 0xFF
                bus.outp(cpu.get_bc(), v)
                cpu.set_hl(cpu.get_hl() + step)
                cpu.f = SZ[cpu.b] | FN
                if repeat and cpu.b:
                    cpu.pc = (cpu.pc - 2) & 0xFFFF
                    return 21
                return 16
            return f
        ed[0xA0], ed[0xA8], ed[0xB0], ed[0xB8] = ldx(1, 0), ldx(-1, 0), ldx(1, 1), ldx(-1, 1)
        ed[0xA1], ed[0xA9], ed[0xB1], ed[0xB9] = cpx(1, 0), cpx(-1, 0), cpx(1, 1), cpx(-1, 1)
        ed[0xA2], ed[0xAA], ed[0xB2], ed[0xBA] = inx(1, 0), inx(-1, 0), inx(1, 1), inx(-1, 1)
        ed[0xA3], ed[0xAB], ed[0xB3], ed[0xBB] = outx(1, 0), outx(-1, 0), outx(1, 1), outx(-1, 1)

        def prefix_ed():
            cpu.r = (cpu.r & 0x80) | ((cpu.r + 1) & 0x7F)
            code = fetch()
            f = ed.get(code)
            if f is None:
                return 8
            return f()
        main[0xED] = prefix_ed

        # DD / FD: index registers
        def make_index(name):
            def getx():
                return getattr(cpu, name)

            def setx(v):
                setattr(cpu, name, v & 0xFFFF)

            def run():
                cpu.r = (cpu.r & 0x80) | ((cpu.r + 1) & 0x7F)
                code = fetch()
                x = getx()
                # instructions with HL -> IX
                if code == 0x21:
                    setx(fetch16())
                    return 14
                if code == 0x22:
                    wr16(fetch16(), x)
                    return 20
                if code == 0x2A:
                    setx(rd16(fetch16()))
                    return 20
                if code == 0x23:
                    setx(x + 1)
                    return 10
                if code == 0x2B:
                    setx(x - 1)
                    return 10
                if code in (0x09, 0x19, 0x29, 0x39):
                    p = (code >> 4) & 3
                    v = x if p == 2 else get_rr(p)
                    setx(add16(x, v))
                    return 15
                if code == 0xE1:
                    setx(cpu.pop())
                    return 14
                if code == 0xE5:
                    cpu.push(x)
                    return 15
                if code == 0xE9:
                    cpu.pc = x
                    return 8
                if code == 0xF9:
                    cpu.sp = x
                    return 10
                if code == 0xE3:
                    v = rd16(cpu.sp)
                    wr16(cpu.sp, x)
                    setx(v)
                    return 23
                if code == 0x34 or code == 0x35:
                    a = (x + sdisp()) & 0xFFFF
                    wr(a, inc8(rd(a)) if code == 0x34 else dec8(rd(a)))
                    return 23
                if code == 0x36:
                    a = (x + sdisp()) & 0xFFFF
                    wr(a, fetch())
                    return 19
                if code == 0xCB:
                    a = (x + sdisp()) & 0xFFFF
                    c2 = fetch()
                    xx, y, z = c2 >> 6, (c2 >> 3) & 7, c2 & 7
                    v = rd(a)
                    if xx == 1:
                        r = v & (1 << y)
                        f = (cpu.f & FC) | FH | (FZ | FP if not r else 0) | ((a >> 8) & (FY | FX))
                        if y == 7 and r:
                            f |= FS
                        cpu.f = f
                        return 20
                    if xx == 0:
                        v = rot(y, v)
                    elif xx == 2:
                        v &= ~(1 << y)
                    else:
                        v |= 1 << y
                    wr(a, v)
                    if z != 6:
                        setattr(cpu, RN[z], v)
                    return 23
                # ld r,(ix+d) / ld (ix+d),r / alu (ix+d)
                if 0x40 <= code <= 0x7F and code != 0x76 and ((code & 7) == 6 or (code >> 3) & 7 == 6):
                    a = (x + sdisp()) & 0xFFFF
                    if (code & 7) == 6:
                        setattr(cpu, RN[(code >> 3) & 7], rd(a))
                    else:
                        wr(a, getattr(cpu, RN[code & 7]))
                    return 19
                if 0x80 <= code <= 0xBF and (code & 7) == 6:
                    a = (x + sdisp()) & 0xFFFF
                    alu((code >> 3) & 7, rd(a))
                    return 19
                # IXh / IXl (undocumented)
                hi_lo = {4: 'h', 5: 'l'}
                if 0x40 <= code <= 0xBF or code in (0x24, 0x25, 0x26, 0x2C, 0x2D, 0x2E):
                    def gr(i):
                        if i == 4:
                            return getx() >> 8
                        if i == 5:
                            return getx() & 0xFF
                        return getr(i)

                    def sr(i, v):
                        if i == 4:
                            setx((getx() & 0xFF) | v << 8)
                        elif i == 5:
                            setx((getx() & 0xFF00) | v)
                        else:
                            setr(i, v)
                    if code in (0x24, 0x2C):
                        i = 4 if code == 0x24 else 5
                        sr(i, inc8(gr(i)))
                        return 8
                    if code in (0x25, 0x2D):
                        i = 4 if code == 0x25 else 5
                        sr(i, dec8(gr(i)))
                        return 8
                    if code in (0x26, 0x2E):
                        sr(4 if code == 0x26 else 5, fetch())
                        return 11
                    if code < 0x80:
                        sr((code >> 3) & 7, gr(code & 7))
                        return 8
                    alu((code >> 3) & 7, gr(code & 7))
                    return 8
                # otherwise: the prefix is ignored
                cpu.pc = (cpu.pc - 1) & 0xFFFF
                return 4 + main[fetch()]() if False else 4
            return run
        main[0xDD] = make_index('ix')
        main[0xFD] = make_index('iy')
        self.main = main
