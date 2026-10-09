; Music player of Bad Apple!! for the YM3812 of MPH-1V (docs/format.md, tools/mkmusic.py).
;
; Stream: pairs (register, value); FFh = the next tick; FEh = end. The pairs before the first FFh are the
; setup, written by mus_init with the delays of the chip. Then the interrupt (badapple.asm isr) writes at most
; one pair per call (1300.7 Hz, 770 us apart, so no delays are needed) and lets the player past an FFh for each
; tick that is due. Ticks come from a countdown of the calls (mus_step calls per tick, 8.8 fixed point): 21.70
; at the nominal 59.94 Hz. At each VBI the interrupt sets mus_step from mus_lead, the ticks played minus the VBIs
; the video advanced: the music runs a little faster or slower to stay with the picture (mus_rate), and when a
; frame is late the video clock stops, so the music slows down smoothly (by up to 30 %).
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
	ld (mus_pend),a
	ld (mus_lead),a
	ld (mus_frac),a
	inc a
	ld (mus_st),a			; idle, the first tick at the first call of the interrupt
	ld hl,(mus_rate+2*3)
	ld (mus_step),hl
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
mus_st:		db 0			; D7: pairs to write (else waiting at an FFh), D0-D6: calls to the next tick
mus_pend:	db 0			; ticks due and not yet started
mus_lead:	db 0			; ticks started minus VBIs of the video (signed)
mus_frac:	db 0			; fraction of the countdown
mus_step:	dw 0			; calls per tick, 8.8
; calls per tick by the lead -3..10: 21.70 * 256 / speed; speeds 1.06 1.04 1.02 1.005 0.995 0.96 0.92 0.88 0.85
; 0.82 0.79 0.76 0.73 0.70 (gently near the video, harder when it is far behind)
mus_rate:	dw 5241, 5342, 5446, 5528, 5583, 5787, 6038, 6313, 6536, 6775, 7032, 7310, 7610, 7936
mus_zrd:	dw 0			; A8-A21 of the next page on the RAM disk
mus_left:	dw 0			; pages still to load
