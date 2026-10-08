@echo off
rem Start sapiemu-cli with MCP for the scripts in tools\emu (SAPIEMU_MCP default http://127.0.0.1:8594/mcp).
rem SAPIEMU_DIR: the released SAPIemu to use, default E:\SAPI_GIT\SAPIemu-release (not the SAPIemu repo,
rem which is developed in parallel). Stop it with MCP "power off" first, then close the window.
setlocal
if "%SAPIEMU_DIR%"=="" set SAPIEMU_DIR=E:\SAPI_GIT\SAPIemu-release
cd /d "%SAPIEMU_DIR%"
start "sapiemu-cli MCP 8594" sapiemu-cli.exe --machine "%~dp0badapple_sapi1v.sapi" --mcp --mcp-port 8594
