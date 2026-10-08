; Unrolled fill of the MX rows of the video decoder (sapi/video.asm), at a fixed page after the generated
; handlers.

; vfill: middle bytes of an MX row. The handler sets HL = first middle byte, A = colour, IYL = mask of the right
; byte and jumps to vfill + 2 * (62 - m) (IXH = HIGH vfill). Must start a page.
	org 03400h
vfill:
	rept 62
	ld (hl),a
	inc hl
	endm
	ld a,(hl)			; right byte
	xor iyl
	ld (hl),a
	ld a,(bc)			; dispatch
	inc bc
	ld l,a
	ld h,HI_VJT
	ld h,(hl)
	jp (hl)
vfill_end:
