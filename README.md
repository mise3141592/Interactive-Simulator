# Interactive Problem Simulator — C++ 버전

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

## 구조

| 항목 | 내용 |
|------|------|
| 의존성 | Windows API만 (comctl32, comdlg32, shlwapi) |
| 추가 DLL | 없음 (static link) |
| 파일 | sim.exe 단일 파일 |

## Python sim.py 와의 차이

- GUI: tkinter → Win32 API (GDI 직접 렌더링)
- 엔진: 동일 — 솔루션/인터랙터를 각각 `-u` 플래그로 실행, 부모 프로세스가 PIPE로 relay
- 트레이스 렌더링: 배치 처리 없이 WM_ENGINE_STEP 메시지로 즉시 렌더 (이미 OS 메시지 큐가 비동기 처리)
- 내보내기: 동일한 HTML 생성
