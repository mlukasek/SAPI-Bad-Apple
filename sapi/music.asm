; Music player of Bad Apple!! for the YM3812 of MPH-1V (docs/format.md, tools/mkmusic.py).
;
; Stream: pairs (register, value); FFh = wait for the next VBI; FEh = end. The pairs before the first FFh are
; the setup, written by mus_init with the delays of the chip. Then the interrupt (badapple.asm isr) writes at
; most one pair per call (1300.7 Hz, 770 us apart, so no delays are needed); a VBI lets it past one FFh.
; The stream comes from the RAM disk into a ring of 4 pages (MUS_RING); the main loop refills a page the
; interrupt has left (mus_fill), the interrupt never touches the ports of ZRD-1V.

YM_ADDR:	equ 056h
YM_DATA:	equ 057h
MUS_RING:	equ 03800h		; 1 KB; the pointer wraps by RES 2,H (3C00h -> 3800h)
MUS_RING_END:	equ 03C00h
MUS_WAIT:	equ 0FFh
MUS_END:	equ 0FEh

; ---- mus_init: load the ring, write the setup (interrupt off). Leaves mus_r at the first FFh.
mus_init:
	ld hl,(dat_hdr+14)		; music offset (256-aligned) -> ZRD page
	ld a,(dat_hdr+16)
	ld l,h
	ld h,a
	ld de,DAT_PHYS*256
	add hl,de
	ld (mus_zrd),hl
	ld hl,(dat_hdr+17)		; music length -> pages
	ld a,(dat_hdr+19)
	ld de,255
	add hl,de
	adc a,0
	ld l,h
	ld h,a
	ld (mus_left),hl
	ld hl,MUS_RING
	ld (mus_r),hl
	ld a,HIGH MUS_RING
	ld (mus_w),a
	xor a
	ld (mus_vbi),a
	ld (mus_wait),a
	ld b,4
.mi_load:
	push bc
	call mus_page
	pop bc
	djnz .mi_load
	ld hl,MUS_RING
.mi_set:
	ld a,(hl)
	cp MUS_END
	jr nc,.mi_done			; FFh (or FEh: no music)
	inc hl
	ld e,(hl)
	inc hl
	call ym_write
	jr .mi_set
.mi_done:
	ld (mus_r),hl
	ret

; ---- mus_fill: load one page of the stream if the interrupt has left the page mus_w
mus_fill:
	ld a,(mus_r+1)			; page being read (one byte: atomic)
	ld b,a
	ld a,(mus_w)
	cp b
	ret z
	; fall through

; ---- mus_page: next 256 B of the stream into the page mus_w (nothing when the stream is all read)
mus_page:
	ld hl,(mus_left)
	ld a,h
	or l
	ret z
	dec hl
	ld (mus_left),hl
	ld hl,(mus_zrd)
	ld a,(mus_w)
	ld d,a
	call zrd_read
	ld (mus_zrd),hl
	ld a,d
	cp HIGH MUS_RING_END
	jr nz,.mp_w
	ld a,HIGH MUS_RING
.mp_w:	ld (mus_w),a
	ret

; ---- mus_silence: all keys off, rhythm off (interrupt off)
mus_silence:
	ld a,0B0h
.ms:	ld e,0
	push af
	call ym_write
	pop af
	inc a
	cp 0B9h
	jr nz,.ms
	ld a,0BDh
	ld e,0
	; fall through

; ---- ym_write: register A = E with the delays of the YM3812 (3.3 us after the address, 23.5 us after the
; data: 94 T at 4 MHz). Keeps BC, DE, HL.
ym_write:
	out (YM_ADDR),a
	ex (sp),hl
	ex (sp),hl
	ld a,e
	out (YM_DATA),a
	push bc
	ld b,7
.yw:	djnz .yw
	pop bc
	ret

; ---- variables
mus_r:		dw 0			; read pointer of the interrupt
mus_w:		db 0			; page to load next
mus_vbi:	db 0			; VBIs not yet used by the player
mus_wait:	db 0			; 1: at an FFh (or the end) with no VBI, the interrupt skips the player
mus_zrd:	dw 0			; A8-A21 of the next page on the RAM disk
mus_left:	dw 0			; pages still to load
