@echo off
rem Build of Bad Apple!! for SAPI-1 (docs\vyvoj.md, "Preklad"):
rem   build.cmd        the music (tools\mkmusic.py, if orig\midi is there), the program, BADAPPLE.DAT (from
rem                    build\video.bin, build\music.bin) and the RAM disk image build\ramdisk.bin
rem   build.cmd video  first the video stream (tools\vcodec.py, a few minutes; needs ffmpeg and orig\)
rem Needs Python 3 and pasmo 0.5.3 (PASMO). Paths in the environment or the defaults below.
setlocal
cd /d "%~dp0"
if "%PASMO%"=="" set PASMO=E:\SAPI_GIT\Tools\pasmo-0.5.3\pasmo.exe
if "%CPM_IMAGE%"=="" set CPM_IMAGE=E:\SAPI_GIT\SAPIemu-release\media\zrmd-1\SAPI_CPM_Martin_2019-10-07.bin
if not exist build mkdir build

if /i "%1"=="video" (
  python tools\vcodec.py --out build\video.bin || exit /b 1
)
if exist orig\midi\handhule90-full.mid (
  python tools\mkmusic.py || exit /b 1
)
python tools\mkvdec.py || exit /b 1
pushd sapi
"%PASMO%" --bin badapple.asm ..\build\badapple.com ..\build\badapple.sym || (popd & exit /b 1)
"%PASMO%" --bin vtest.asm ..\build\vtest.com ..\build\vtest.sym || (popd & exit /b 1)
popd
python tools\check_build.py || exit /b 1
python tools\mkdat.py --music build\music.bin || exit /b 1
python tools\cpmdisk.py --empty "%CPM_IMAGE%" build\ramdisk.bin build\BADAPPLE.DAT=BADAPPLE.DAT@8 build\badapple.com=BADAPPLE.COM || exit /b 1
python tools\bin2hex.py || exit /b 1
echo build\ramdisk.bin and .hex: the whole RAM disk A: (CP/M, BADAPPLE.COM, BADAPPLE.DAT)
