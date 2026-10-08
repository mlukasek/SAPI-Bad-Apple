; =====================================================================
;  Bad Apple!! for SAPI-1 (sestava V), CP/M .COM (docs/vyvoj.md).
;
;  Hardware (tools/emu/badapple_sapi1v.sapi):
;  - JPR-1V Z80 4 MHz (TURBO), RAM-1V: MAP register 63h, C0h = CGA-1V
;    at C000h (RAM C000-FFFF hidden, CP/M is not called while running);
;  - CGA-1V in CGA mode (2 bits per pixel, COLMASK 11h), two pages:
;    the decoder draws into the hidden one, the interrupt flips them at
;    the vertical blank (VBI);
;  - ZRD-1V RAM disk: BADAPPLE.DAT from block 8 (10000h), read through
;    the ports into a ring buffer of 32 KB;
;  - MPH-1V: 82C54 counter 2 gives the interrupt (1300.7 Hz, IM 1),
;    YM3812 the music;
;  - keyboard on JPR-1V: STROBE on port 01h D0 (a pulse of 1 ms, so the
;    interrupt polls it), any key ends the demo.
; =====================================================================

MAPREG:		equ 063h		; RAM-1V MAP register (bits 6, 7), ZRD-1V A16-A21 (bits 0-5)
MAP_CGA:	equ 0C0h		; MAP1 = MAP2 = H
CGA:		equ 0C000h
CGA_CFG:	equ CGA+03FFBh		; CONFIG (write): D0 shown page, D1 CPU page, D2 CGA mode, D7 ack VBI
CGA_STATUS:	equ CGA+03FFBh		; STATUS (read): D7 = VBI since the last acknowledge
CGA_PAL_ADDR:	equ CGA+03FFCh
CGA_PAL_DATA:	equ CGA+03FFDh
CGA_COLMASK:	equ CGA+03FFEh
CFG_CGA:	equ 004h

ZRD_DATA:	equ 060h
ZRD_A0:		equ 061h
ZRD_A8:		equ 062h
DAT_PHYS:	equ 01h			; A16-A21 of BADAPPLE.DAT (10000h)

PIT2:		equ 052h		; 82C54 counter 2
PITCW:		equ 053h
MIEN:		equ 054h		; MPH-1V IEN (write)
MIACK:		equ 055h		; MPH-1V IACK (write)
TICK_DIV:	equ 43			; 55930.4 / 43 = 1300.7 Hz
IEN_QUIET:	equ 020h		; gate G2, no interrupt
IEN_RUN:	equ 0A0h		; and the F2 interrupt

KSTB:		equ 001h		; P0-IN D0: STROBE (0 = key); P0-OUT D0 ACK, D1 buzzer off

DSM_A:		equ 010h		; DSM-1V channels: 03h = no interrupts
DSM_B:		equ 014h
DSM_NOINT:	equ 003h

RING:		equ 04000h		; ring buffer of the video stream, 32 KB (4000h-BFFFh)
RING_END:	equ 0C000h
AHEAD_PAGES:	equ 17			; before a frame: at least this many 256 B pages loaded
STACK_TOP:	equ 03F00h		; stack below the ring buffer, above the decoder handlers

	org 100h

; ---- start
start:
	di
	ld sp,STACK_TOP
	ld hl,0038h
	ld de,page0_save
	ld bc,3
	ldir
	ld a,0C3h			; JP isr
	ld (0038h),a
	ld hl,isr
	ld (0039h),hl
	im 1
	xor a				; I = 0 (graphics cards and INTA, see SAPI-FXS4)
	ld i,a
	ld a,DSM_NOINT
	out (DSM_A),a
	out (DSM_B),a
	ld a,002h			; keyboard ACK off, buzzer off
	out (KSTB),a
	ld a,MAP_CGA
	out (MAPREG),a
	call dat_open
	jp nz,no_dat
	ld a,CFG_CGA+002h		; clear page B, then A
	ld (CGA_CFG),a
	call cga_clear
	ld a,CFG_CGA+001h		; shown B, CPU page A (frame 0 is drawn into A)
	ld (cfg),a
	ld (CGA_CFG),a
	call cga_clear
	call vbi_wait
	call pal_init
	ld a,011h
	ld (CGA_COLMASK),a
	; the interrupt
	ld a,0B4h			; counter 2: LSB+MSB, mode 2
	out (PITCW),a
	ld a,TICK_DIV
	out (PIT2),a
	xor a
	out (PIT2),a
	ld a,0C0h			; clear F2 and F1
	out (MIACK),a
	ld a,IEN_RUN
	out (MIEN),a
	call ring_init
	ld hl,0
	ld (vbi_cnt),hl
	ld hl,-1			; "the flip before frame 0": frame 0 is shown at VBI 1
	ld (flip_at),hl
	ei

; ---- main loop: one frame
frame_loop:
	ld a,(key_hit)
	or a
	jp nz,exit
	call ring_ahead			; at least AHEAD_PAGES loaded (or the end of the stream)
	ld bc,(ring_r)
	ld a,(bc)			; header: VBIs after the previous frame
	inc bc
	or a
	jp z,video_end
	cp 0FFh				; padding to the end of the ring buffer
	jr nz,.fl_hdr
	ld bc,RING
	ld (ring_r),bc
	jr frame_loop
.fl_hdr:
	ld hl,(flip_at)
	ld e,a
	ld d,0
	add hl,de
	ld (next_flip),hl
	call vdec_frame			; BC = after the frame
	ld (ring_r),bc
	; late? (VBI counter already past the time of the flip)
	di
	ld hl,(vbi_cnt)
	ld de,(next_flip)
	ld (flip_at),de
	or a
	sbc hl,de
	jp m,.fl_ok			; its VBI is still to come
	ld hl,(late_cnt)
	inc hl
	ld (late_cnt),hl
.fl_ok:
	ld a,1
	ld (ready),a
	ei
	ld hl,(frame_cnt)
	inc hl
	ld (frame_cnt),hl
frame_done:				; (symbol for the tests: frame drawn, waiting for the flip)
.fl_wait:
	ld a,(ready)			; the interrupt clears it at the flip
	or a
	jr z,frame_loop
	ld a,(key_hit)
	or a
	jp nz,exit
	call ring_fill1			; read ahead meanwhile
	jr .fl_wait

video_end:
	ld b,120			; 2 s of the last picture
.ve_w:	call vbi_count_wait
	djnz .ve_w

; ---- back to CP/M: interrupt off, page 0 back, CGA-1V unmapped, warm boot
exit:
	di
	ld sp,STACK_TOP
	ld a,IEN_QUIET
	out (MIEN),a
	ld a,0C0h
	out (MIACK),a
	ld a,080h			; acknowledge VBI, page A, EGA mode
	ld (CGA_CFG),a
	ld hl,page0_save
	ld de,0038h
	ld bc,3
	ldir
	xor a
	out (MAPREG),a
	ld a,002h
	out (KSTB),a
	jp 0

no_dat:
	xor a
	out (MAPREG),a
	ld de,msg_nodat
	ld c,9
	call 5
	jp 0

msg_nodat:
	db 'BADAPPLE.DAT is not at its place on the RAM disk (build.cmd).', 13, 10, '$'

; =====================================================================
; Interrupt (RST 38h, 82C54 counter 2, 1300.7 Hz)
; Polls the keyboard STROBE and the VBI of CGA-1V. At a VBI: acknowledge
; it (the only writer of CONFIG), count it, flip the pages when a frame
; is ready and its time has come.
; =====================================================================
isr:
	push af
	ld a,080h			; clear F2
	out (MIACK),a
	in a,(KSTB)
	rrca
	jr c,.is_nokey
	ld a,1
	ld (key_hit),a
	ld a,003h			; ACK
	out (KSTB),a
.is_nokey:
	ld a,(CGA_STATUS)
	rlca
	jr nc,.is_done
	push hl
	ld a,(cfg)
	or 080h
	ld (CGA_CFG),a
	ld hl,(vbi_cnt)
	inc hl
	ld (vbi_cnt),hl
	ld a,(ready)
	or a
	jr z,.is_vend
	push de
	ld de,(flip_at)
	or a
	sbc hl,de
	pop de
	jp m,.is_vend			; not yet
	ld a,(cfg)			; flip: shown page and CPU page swap
	xor 003h
	ld (cfg),a
	or 080h
	ld (CGA_CFG),a
	xor a
	ld (ready),a
.is_vend:
	pop hl
.is_done:
	pop af
	ei
	reti

; ---- vbi_count_wait: wait for the next VBI counted by the interrupt (keeps BC)
vbi_count_wait:
	ld hl,(vbi_cnt)
.vcw:	ld de,(vbi_cnt)
	ld a,e
	cp l
	jr z,.vcw
	ret

; ---- vbi_wait: wait for a VBI by polling (interrupt off); acknowledges it
vbi_wait:
	ld a,(cfg)
	or 080h
	ld (CGA_CFG),a
.vw:	ld a,(CGA_STATUS)
	rlca
	jr nc,.vw
	ld a,(cfg)
	or 080h
	ld (CGA_CFG),a
	ret

; ---- cga_clear: the CPU page black (16 KB, also the registers' mirror area is plain RAM)
cga_clear:
	ld hl,CGA
	ld de,CGA+1
	ld bc,16000-1
	ld (hl),0
	ldir
	ret

; ---- pal_init: colours 0 black, 1 and 16 greys, 17 white (COLMASK 11h); during a VBI
pal_init:
	xor a
	ld (CGA_PAL_ADDR),a
	ld hl,pal_rgb
	ld b,18*3
.pi:	ld a,(hl)
	ld (CGA_PAL_DATA),a
	inc hl
	djnz .pi
	ret

pal_rgb:					; entries 0-17 (only 0, 1, 16, 17 are seen)
	db 0,0,0, 21,21,21
	rept 14
	db 0,0,0
	endm
	db 42,42,42, 63,63,63

; =====================================================================
; BADAPPLE.DAT on the RAM disk (tools/mkdat.py): header at 10000h
;   0: 'BADAPPL1'  8: video offset (3 B), 11: video length (3 B)
; The video is read in pages of 256 B into the ring buffer; a frame never
; crosses the end of the ring (the encoder pads with FFh).
; =====================================================================

; ---- dat_open: Z = the header is there; reads the video position
dat_open:
	ld a,DAT_PHYS+MAP_CGA
	out (MAPREG),a
	xor a
	out (ZRD_A8),a
	out (ZRD_A0),a
	ld hl,dat_hdr
	ld bc,14*256+ZRD_DATA
	inir
	ld hl,dat_hdr
	ld de,dat_magic
	ld b,8
.do_m:	ld a,(de)
	cp (hl)
	ret nz
	inc hl
	inc de
	djnz .do_m
	ret

dat_magic:
	db 'BADAPPL1'

; ---- ring_init: read position = start of the video, ring empty
ring_init:
	ld hl,(dat_hdr+8)		; video offset (256-aligned) -> ZRD page
	ld a,(dat_hdr+10)
	ld l,h
	ld h,a				; HL = offset >> 8
	ld de,DAT_PHYS*256
	add hl,de
	ld (zrd_page),hl		; A8-A21 of the next page to read
	ld hl,(dat_hdr+11)		; video length -> pages
	ld a,(dat_hdr+13)
	ld de,255
	add hl,de
	adc a,0
	ld l,h
	ld h,a
	ld (pages_left),hl
	ld hl,RING
	ld (ring_r),hl
	ld a,HIGH RING
	ld (ring_w),a
	ret

; ---- ring_ahead: load pages until AHEAD_PAGES are ahead of the read pointer (or no more data)
ring_ahead:
	ld a,(ring_r+1)
	ld b,a
	ld a,(ring_w)
	sub b
	and 07Fh			; pages loaded ahead (ring of 128 pages)
	cp AHEAD_PAGES
	ret nc
	call ring_page
	ret z				; no more data
	jr ring_ahead

; ---- ring_fill1: load one page if there is room (keeps one page free before the read page)
ring_fill1:
	ld a,(ring_r+1)
	dec a
	cp HIGH RING
	jr nc,.rf
	ld a,HIGH RING_END-1
.rf:	ld b,a
	ld a,(ring_w)
	cp b
	ret z				; full
	; fall through

; ---- ring_page: read the next 256 B of the stream to ring_w. Z = no more data.
ring_page:
	ld hl,(pages_left)
	ld a,h
	or l
	ret z
	dec hl
	ld (pages_left),hl
	ld hl,(zrd_page)
	ld a,h
	or MAP_CGA
	out (MAPREG),a
	ld a,l
	out (ZRD_A8),a
	xor a
	out (ZRD_A0),a
	inc hl
	ld (zrd_page),hl
	ld a,(ring_w)
	ld h,a
	ld l,0
	ld bc,0*256+ZRD_DATA		; B = 0: 256 bytes
.rp:	rept 16
	ini
	endm
	jr nz,.rp
	ld a,h				; INI moved HL to the next page

	cp HIGH RING_END
	jr nz,.rp_w
	ld a,HIGH RING
.rp_w:	ld (ring_w),a
	or 1				; NZ
	ret

	include "video.asm"

; ---- variables
page0_save:	ds 3
cfg:		db 0			; CONFIG without D7 (shown page, CPU page, mode)
ready:		db 0			; a frame is drawn and waits for its flip
key_hit:	db 0
vbi_cnt:	dw 0			; VBIs since the start
flip_at:	dw 0			; VBI of the flip of the last frame
next_flip:	dw 0
frame_cnt:	dw 0			; frames drawn
late_cnt:	dw 0			; frames that were not ready at their VBI
dat_hdr:	ds 14
zrd_page:	dw 0			; A8-A21 of the next page to read
pages_left:	dw 0
ring_r:		dw 0			; read pointer (start of the next frame)
ring_w:		db 0			; page of the next page to load

PROGRAM_END:				; must be below 1000h, VDEC_TOP below STACK_TOP-100h (tools/mkdat.py checks)

	include "gen/vdec.asm"
	include "vfill.asm"
