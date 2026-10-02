# Interactive Problem Simulator

Python sim.py 와 완전히 동일한 UI/기능을 Win32 API로 구현한 단일 실행파일.

## 컴파일

### MinGW-w64 (권장)

[WinLibs](https://winlibs.com) 에서 MinGW-w64 다운로드 후:

```bat
build.bat
```

또는 직접:

```bat
g++ -O2 -std=c++17 -mwindows -o sim.exe sim.cpp -lcomctl32 -lcomdlg32 -lshlwapi -static-libgcc -static-libstdc++
```

### MSVC (Visual Studio 2019/2022)

Developer Command Prompt 에서:

```bat
build.bat msvc
```

## 실행

```
sim.exe
```

같은 폴더에 `pypy3.11.exe` / `pypy3.exe` / `pypy.exe` 가 있으면 자동 인식.
없으면 상단 **변경…** 버튼으로 선택.
