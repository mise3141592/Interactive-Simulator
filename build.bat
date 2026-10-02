@echo off
:: Interactive Problem Simulator - Build Script
:: 요구사항: MinGW-w64 (g++ 12+) 또는 MSVC (VS 2019+)
::
:: MinGW 빌드 (권장):
::   build.bat
:: MSVC 빌드:
::   build.bat msvc

if "%1"=="msvc" goto msvc

:: ── MinGW ──────────────────────────────────────────────────────────────────
echo [MinGW] Compiling sim.cpp ...
g++ -O2 -std=c++17 -mwindows ^
    -Wall -Wno-unused-result ^
    -o sim.exe sim.cpp ^
    -lcomctl32 -lcomdlg32 -lshlwapi ^
    -static-libgcc -static-libstdc++ ^
    -Wl,-subsystem,windows

if %ERRORLEVEL%==0 (
    echo [OK] sim.exe 생성 완료
) else (
    echo [FAIL] 빌드 실패 — g++ 이 PATH 에 있는지 확인하세요
    echo  설치: https://winlibs.com  (WinLibs MinGW-w64)
)
goto end

:msvc
:: ── MSVC ───────────────────────────────────────────────────────────────────
echo [MSVC] Compiling sim.cpp ...
cl /O2 /std:c++17 /EHsc /W3 ^
   /D_UNICODE /DUNICODE /D_WIN32_WINNT=0x0A00 ^
   sim.cpp ^
   /link /SUBSYSTEM:WINDOWS /ENTRY:wWinMainCRTStartup ^
   comctl32.lib comdlg32.lib shlwapi.lib user32.lib gdi32.lib

if %ERRORLEVEL%==0 (
    echo [OK] sim.exe 생성 완료
) else (
    echo [FAIL] 빌드 실패 — Visual Studio Developer Command Prompt 에서 실행하세요
)

:end
