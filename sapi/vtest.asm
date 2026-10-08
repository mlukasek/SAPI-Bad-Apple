; Test of the video decoder in the Z80 model (tools/vtest.py): the script puts a frame body at FRAME, selects the
; CPU page and starts at vt_start; the program decodes the frame and halts.

FRAME	equ 4000h

	org 100h
vt_start:
	ld sp,0E00h			; below the generated tables at 1000h
	ld a,0C0h
	out (63h),a			; map CGA-1V at C000h
	ld bc,FRAME
	call vdec_frame
	halt

	include "video.asm"

	include "gen/vdec.asm"
