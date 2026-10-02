/*
 * Interactive Problem Simulator  —  sim.cpp
 * Compile (MinGW-w64):
 *   g++ -O2 -std=c++17 -mwindows -o sim.exe sim.cpp -lcomctl32 -lcomdlg32 -lshlwapi -static-libgcc -static-libstdc++
 * Compile (MSVC):
 *   cl /O2 /std:c++17 sim.cpp /link /SUBSYSTEM:WINDOWS comctl32.lib comdlg32.lib shlwapi.lib shell32.lib
 */

#define UNICODE
#define _UNICODE
#define WIN32_LEAN_AND_MEAN
#ifndef _WIN32_WINNT
#  define _WIN32_WINNT 0x0600   // Vista+ minimum; DPI v2 detected at runtime
#endif
#include <windows.h>
#include <commctrl.h>
#include <commdlg.h>
#include <shlwapi.h>
#include <shellapi.h>   // ShellExecuteW
#include <windowsx.h>   // GET_Y_LPARAM, GET_X_LPARAM
#include <richedit.h>

#include <algorithm>
#include <atomic>
#include <cstdio>
#include <cstring>
#include <cwchar>
#include <fstream>
#include <functional>
#include <memory>
#include <mutex>
#include <sstream>
#include <string>
#include <thread>
#include <vector>

using std::min;
using std::max;
#include <queue>

/* ══════════════════════════════════════════════════════════════════════════
   Colour palette  (matches Python sim.py)
   ══════════════════════════════════════════════════════════════════════════ */
#define C(r,g,b) RGB(r,g,b)
static const COLORREF
    COL_BG      = C(0x0f,0x11,0x17),
    COL_BG2     = C(0x16,0x1b,0x27),
    COL_BG3     = C(0x1e,0x25,0x35),
    COL_BG4     = C(0x25,0x2d,0x42),
    COL_BORDER  = C(0x2a,0x33,0x50),
    COL_BORDER2 = C(0x3a,0x44,0x66),
    COL_TEXT    = C(0xe2,0xe8,0xf8),
    COL_TEXT2   = C(0x88,0x92,0xb0),
    COL_TEXT3   = C(0x4a,0x55,0x80),
    COL_BLUE    = C(0x4f,0x8e,0xf7),
    COL_GREEN   = C(0x3d,0xd6,0x8c),
    COL_RED     = C(0xf0,0x70,0x70),
    COL_AMBER   = C(0xf0,0xc0,0x60),
    COL_TEAL    = C(0x40,0xd4,0xc0),
    COL_BLUE_BG = C(0x1a,0x2a,0x4a),
    COL_GREEN_BG= C(0x0d,0x2a,0x1e),
    COL_RED_BG  = C(0x2a,0x10,0x10),
    COL_TEAL_BG = C(0x0d,0x2a,0x26);

/* ══════════════════════════════════════════════════════════════════════════
   String helpers
   ══════════════════════════════════════════════════════════════════════════ */
static std::wstring s2w(const std::string& s) {
    if (s.empty()) return {};
    int n = MultiByteToWideChar(CP_UTF8, 0, s.c_str(), -1, nullptr, 0);
    std::wstring w(n, 0); MultiByteToWideChar(CP_UTF8, 0, s.c_str(), -1, w.data(), n);
    if (!w.empty() && w.back()==0) w.pop_back();
    return w;
}
static std::string w2s(const std::wstring& w) {
    if (w.empty()) return {};
    int n = WideCharToMultiByte(CP_UTF8, 0, w.c_str(), -1, nullptr, 0, nullptr, nullptr);
    std::string s(n, 0); WideCharToMultiByte(CP_UTF8, 0, w.c_str(), -1, s.data(), n, nullptr, nullptr);
    if (!s.empty() && s.back()==0) s.pop_back();
    return s;
}
static std::wstring GetEditText(HWND h) {
    int len = GetWindowTextLengthW(h);
    if (len <= 0) return {};
    std::wstring buf(len+1, 0);
    GetWindowTextW(h, buf.data(), len+1);
    buf.resize(len);
    return buf;
}
// trim trailing \r\n
static std::string rtrim(std::string s) {
    while (!s.empty() && (s.back()=='\n'||s.back()=='\r')) s.pop_back();
    return s;
}

/* ══════════════════════════════════════════════════════════════════════════
   Temp file helper
   ══════════════════════════════════════════════════════════════════════════ */
static std::wstring TempDir() {
    wchar_t buf[MAX_PATH]; GetTempPathW(MAX_PATH, buf); return buf;
}
static std::wstring TempFile(const wchar_t* suffix) {
    wchar_t tmp[MAX_PATH], dir[MAX_PATH];
    GetTempPathW(MAX_PATH, dir);
    GetTempFileNameW(dir, L"sim", 0, tmp);
    // rename to desired suffix (just append)
    std::wstring p = tmp; p += suffix;
    // use original name — just write to it
    return tmp;  // keep original name, caller knows content
}
static bool WriteUtf8File(const std::wstring& path, const std::string& content) {
    HANDLE h = CreateFileW(path.c_str(), GENERIC_WRITE, 0, nullptr,
                           CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, nullptr);
    if (h == INVALID_HANDLE_VALUE) return false;
    DWORD written;
    WriteFile(h, content.c_str(), (DWORD)content.size(), &written, nullptr);
    CloseHandle(h);
    return true;
}
static std::string ReadUtf8File(const std::wstring& path) {
    HANDLE h = CreateFileW(path.c_str(), GENERIC_READ, FILE_SHARE_READ, nullptr,
                           OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, nullptr);
    if (h == INVALID_HANDLE_VALUE) return {};
    DWORD sz = GetFileSize(h, nullptr);
    std::string buf(sz, 0);
    DWORD read; ReadFile(h, buf.data(), sz, &read, nullptr);
    CloseHandle(h);
    return buf;
}

/* ══════════════════════════════════════════════════════════════════════════
   Interaction engine
   ══════════════════════════════════════════════════════════════════════════ */
struct Step { std::string kind, text; };

struct Engine {
    std::wstring interp;
    std::string  sol_code, iact_code, secret;

    // output
    std::vector<Step>  steps;
    std::mutex         steps_mtx;
    std::atomic<bool>  done{false};
    std::atomic<bool>  kill_flag{false};
    int                rc = -1;
    std::string        iact_err_msg;

    // progress callback (called from worker thread, posted to main thread)
    std::function<void()> on_step;   // called after each step added
    std::function<void()> on_done;   // called when finished

    void push(const std::string& kind, const std::string& text) {
        { std::lock_guard<std::mutex> lk(steps_mtx); steps.push_back({kind, text}); }
        if (on_step) on_step();
    }

    void run_async() {
        std::thread([this]{ this->run_sync(); }).detach();
    }

private:
    // ── create anonymous pipe (inheritable) ──────────────────────────────
    struct Pipe { HANDLE r=INVALID_HANDLE_VALUE, w=INVALID_HANDLE_VALUE; };
    static Pipe MakePipe() {
        SECURITY_ATTRIBUTES sa{sizeof(sa), nullptr, TRUE};
        Pipe p; CreatePipe(&p.r, &p.w, &sa, 0); return p;
    }
    static void CloseH(HANDLE& h) { if(h!=INVALID_HANDLE_VALUE){CloseHandle(h);h=INVALID_HANDLE_VALUE;} }

    // ── drain a pipe into a string on a background thread ────────────────
    static std::string DrainToString(HANDLE h) {
        std::string out;
        char buf[4096]; DWORD got;
        while (ReadFile(h, buf, sizeof(buf), &got, nullptr) && got)
            out.append(buf, got);
        return out;
    }

    // ── spawn one process ─────────────────────────────────────────────────
    struct Proc { HANDLE proc=INVALID_HANDLE_VALUE, thread=INVALID_HANDLE_VALUE; DWORD pid=0; };
    static Proc Spawn(const std::wstring& cmdline,
                      HANDLE hStdIn, HANDLE hStdOut, HANDLE hStdErr) {
        STARTUPINFOW si{}; si.cb=sizeof(si);
        si.dwFlags = STARTF_USESTDHANDLES;
        si.hStdInput  = hStdIn;
        si.hStdOutput = hStdOut;
        si.hStdError  = hStdErr;
        PROCESS_INFORMATION pi{};
        std::wstring cmd = cmdline; // CreateProcess needs mutable
        if (!CreateProcessW(nullptr, cmd.data(), nullptr, nullptr,
                            TRUE, CREATE_NO_WINDOW, nullptr, nullptr, &si, &pi))
            return {};
        return {pi.hProcess, pi.hThread, pi.dwProcessId};
    }

    // ── main relay loop ───────────────────────────────────────────────────
    void run_sync() {
        // 1. write temp files
        wchar_t tdir[MAX_PATH]; GetTempPathW(MAX_PATH, tdir);
        auto mkpath = [&](const wchar_t* name) {
            std::wstring p = tdir; p += name; return p;
        };
        std::wstring sol_path  = mkpath(L"sim_sol.py");
        std::wstring iact_path = mkpath(L"sim_iact.py");
        std::wstring sec_path  = mkpath(L"sim_sec.txt");

        std::string sec_content = secret;
        if (sec_content.empty() || sec_content.back()!='\n') sec_content += '\n';

        if (!WriteUtf8File(sol_path,  sol_code)  ||
            !WriteUtf8File(iact_path, iact_code) ||
            !WriteUtf8File(sec_path,  sec_content)) {
            push("error", "임시 파일 생성 실패");
            if (on_done) on_done(); return;
        }

        // 2. build command lines
        std::wstring sol_cmd  = L"\"" + interp + L"\" -u \"" + sol_path  + L"\"";
        std::wstring iact_cmd = L"\"" + interp + L"\" -u \"" + iact_path + L"\" \"" + sec_path + L"\"";

        // 3. pipes:
        //    sol_stdin_pipe  : parent writes → sol reads
        //    sol_stdout_pipe : sol writes → parent reads
        //    iact_stdin_pipe : parent writes → iact reads
        //    iact_stdout_pipe: iact writes → parent reads
        //    iact_stderr_pipe: iact writes → parent reads (for error message)
        Pipe sol_stdin_p, sol_stdout_p, sol_stderr_p;
        Pipe iact_stdin_p, iact_stdout_p, iact_stderr_p;
        sol_stdin_p   = MakePipe();
        sol_stdout_p  = MakePipe();
        sol_stderr_p  = MakePipe();
        iact_stdin_p  = MakePipe();
        iact_stdout_p = MakePipe();
        iact_stderr_p = MakePipe();

        // make our read-ends non-inheritable
        auto NoInherit = [](HANDLE h) {
            SetHandleInformation(h, HANDLE_FLAG_INHERIT, 0);
        };
        NoInherit(sol_stdin_p.w);
        NoInherit(sol_stdout_p.r);
        NoInherit(sol_stderr_p.r);
        NoInherit(iact_stdin_p.w);
        NoInherit(iact_stdout_p.r);
        NoInherit(iact_stderr_p.r);

        // 4. spawn processes
        Proc p_sol  = Spawn(sol_cmd,
                            sol_stdin_p.r, sol_stdout_p.w, sol_stderr_p.w);
        Proc p_iact = Spawn(iact_cmd,
                            iact_stdin_p.r, iact_stdout_p.w, iact_stderr_p.w);

        // close child-side handles in parent
        CloseH(sol_stdin_p.r);
        CloseH(sol_stdout_p.w);
        CloseH(sol_stderr_p.w);
        CloseH(iact_stdin_p.r);
        CloseH(iact_stdout_p.w);
        CloseH(iact_stderr_p.w);

        if (p_sol.proc==INVALID_HANDLE_VALUE || p_iact.proc==INVALID_HANDLE_VALUE) {
            push("error", "프로세스 실행 실패 — 인터프리터 경로를 확인하세요");
            if (on_done) on_done(); return;
        }

        // 5. drain iact stderr in background thread
        std::string iact_err_buf;
        std::thread t_ierr([&]{
            iact_err_buf = DrainToString(iact_stderr_p.r);
        });
        // drain sol stderr (discard)
        std::thread t_serr([&]{
            DrainToString(sol_stderr_p.r);
        });

        // 6. relay loop
        //    Two reader threads push into a shared queue; this thread relays.
        struct Msg { int src; std::string line; bool eof; };
        std::queue<Msg> mq;
        std::mutex      mq_mtx;
        HANDLE          mq_ev = CreateEventW(nullptr, FALSE, FALSE, nullptr);

        auto reader = [&](HANDLE pipe_r, int src) {
            char buf[65536];
            std::string leftover;
            DWORD got;
            while (true) {
                bool ok = ReadFile(pipe_r, buf, sizeof(buf), &got, nullptr) && got > 0;
                if (!ok) break;
                leftover.append(buf, got);
                // flush complete lines
                size_t pos;
                while ((pos = leftover.find('\n')) != std::string::npos) {
                    std::string line = leftover.substr(0, pos+1);
                    leftover.erase(0, pos+1);
                    { std::lock_guard<std::mutex> lk(mq_mtx);
                      mq.push({src, std::move(line), false}); }
                    SetEvent(mq_ev);
                }
            }
            // flush leftover without newline
            if (!leftover.empty()) {
                { std::lock_guard<std::mutex> lk(mq_mtx);
                  mq.push({src, leftover, false}); }
                SetEvent(mq_ev);
            }
            { std::lock_guard<std::mutex> lk(mq_mtx);
              mq.push({src, {}, true}); }
            SetEvent(mq_ev);
        };

        std::thread t_sol_r([&]{ reader(sol_stdout_p.r, 0); });
        std::thread t_iact_r([&]{ reader(iact_stdout_p.r, 1); });

        int  eof_count = 0;
        bool timed_out = false;
        DWORD deadline = GetTickCount() + 30000;

        while (eof_count < 2 && !kill_flag) {
            DWORD remaining = deadline - GetTickCount();
            if ((int)remaining <= 0) { timed_out = true; break; }
            WaitForSingleObject(mq_ev, min(remaining, (DWORD)200));

            while (true) {
                Msg m;
                { std::lock_guard<std::mutex> lk(mq_mtx);
                  if (mq.empty()) break;
                  m = std::move(mq.front()); mq.pop(); }

                if (m.eof) { eof_count++; continue; }

                std::string text = rtrim(m.line);

                if (m.src == 0) {
                    // sol → iact
                    push("output", text);
                    DWORD wr;
                    WriteFile(iact_stdin_p.w, m.line.c_str(), (DWORD)m.line.size(), &wr, nullptr);
                } else {
                    // iact → sol
                    push("input", text);
                    DWORD wr;
                    WriteFile(sol_stdin_p.w, m.line.c_str(), (DWORD)m.line.size(), &wr, nullptr);
                }
            }
        }

        if (timed_out || kill_flag) {
            TerminateProcess(p_sol.proc,  1);
            TerminateProcess(p_iact.proc, 1);
        }

        // close write ends so processes see EOF
        CloseH(sol_stdin_p.w);
        CloseH(iact_stdin_p.w);

        t_sol_r.join();
        t_iact_r.join();

        // drain remaining messages
        {
            std::lock_guard<std::mutex> lk(mq_mtx);
            while (!mq.empty()) {
                auto& m = mq.front();
                if (!m.eof && !m.line.empty()) {
                    std::string text = rtrim(m.line);
                    if (m.src==0) push("output", text);
                    else          push("input",  text);
                }
                mq.pop();
            }
        }

        CloseHandle(mq_ev);
        CloseH(sol_stdout_p.r);
        CloseH(iact_stdout_p.r);

        // wait for processes
        WaitForSingleObject(p_sol.proc,  5000);
        WaitForSingleObject(p_iact.proc, 5000);

        DWORD exit_iact = 1;
        GetExitCodeProcess(p_iact.proc, &exit_iact);
        rc = (int)exit_iact;

        CloseH(sol_stderr_p.r);
        CloseH(iact_stderr_p.r);
        CloseHandle(p_sol.proc);  CloseHandle(p_sol.thread);
        CloseHandle(p_iact.proc); CloseHandle(p_iact.thread);

        t_ierr.join(); t_serr.join();

        if (timed_out) {
            push("error", "실행 시간 초과 (30초)");
        } else if (rc == 0) {
            int q = 0;
            { std::lock_guard<std::mutex> lk(steps_mtx);
              for (auto& s : steps)
                  if (s.kind=="output") q++;
            }
            push("result", "정답! (질문 " + std::to_string(q) + "회 사용)");
        } else {
            // extract first non-empty line from iact stderr
            std::string msg;
            std::istringstream ss(iact_err_buf);
            std::string ln;
            while (std::getline(ss, ln)) {
                ln = rtrim(ln);
                if (!ln.empty()) { msg = ln; break; }
            }
            if (msg.empty()) msg = "오답 또는 런타임 오류";
            push("error", msg);
        }

        done = true;
        if (on_done) on_done();
    }
};

/* ══════════════════════════════════════════════════════════════════════════
   HTML export
   ══════════════════════════════════════════════════════════════════════════ */
static std::string HtmlEsc(const std::string& s) {
    std::string r; r.reserve(s.size());
    for (char c : s) switch(c){
        case '&': r+="&amp;"; break; case '<': r+="&lt;"; break;
        case '>': r+="&gt;"; break;  default: r+=c;
    }
    return r;
}

static std::string BuildHtml(const std::vector<Step>& steps,
                              const std::string& secret_preview,
                              const std::string& interp_name) {
    // timestamp
    SYSTEMTIME st; GetLocalTime(&st);
    char now[64]; sprintf_s(now, "%04d-%02d-%02d %02d:%02d:%02d",
        st.wYear, st.wMonth, st.wDay, st.wHour, st.wMinute, st.wSecond);

    int q_cnt = 0;
    for (auto& s : steps)
        if (s.kind=="output") q_cnt++;

    std::string rows;
    for (auto& s : steps) {
        if (s.kind=="result") rows += "<div class=\"sep\"></div>\n";
        std::string tc = s.kind=="output"?"out":s.kind=="input"?"in":s.kind=="result"?"ok":"err";
        std::string tl = s.kind=="output"?"출력":s.kind=="input"?"입력":s.kind=="result"?"결과":"오류";
        rows += "<div class=\"row\"><span class=\"tag "+tc+"\">"+tl+"</span>"
                "<span class=\"txt "+tc+"\">"+HtmlEsc(s.text)+"</span></div>\n";
    }

    std::string html =
R"(<!DOCTYPE html><html lang="ko"><head><meta charset="UTF-8"><title>Interaction Trace</title>
<style>
:root{--bg:#0f1117;--bg2:#161b27;--bg3:#1e2535;--border:#2a3350;
--text:#e2e8f8;--text2:#8892b0;--text3:#4a5580;
--blue:#4f8ef7;--blue-bg:#1a2a4a;--green:#3dd68c;--green-bg:#0d2a1e;
--red:#f07070;--red-bg:#2a1010;--teal:#40d4c0;--teal-bg:#0d2a26;
--mono:'JetBrains Mono','Fira Code',ui-monospace,monospace;--sans:'Inter','Pretendard',system-ui,sans-serif;}
*{box-sizing:border-box;margin:0;padding:0;}
body{background:var(--bg);color:var(--text);font-family:var(--sans);padding:44px 24px;}
.hdr{max-width:660px;margin:0 auto 28px;}
.ttl{font-size:18px;font-weight:700;font-family:var(--mono);color:var(--blue);margin-bottom:10px;}
.meta{display:flex;flex-wrap:wrap;gap:10px;font-size:12px;color:var(--text3);}
.chip{background:var(--bg2);border:1px solid var(--border);border-radius:6px;padding:3px 10px;font-family:var(--mono);}
.card{max-width:660px;margin:0 auto;background:var(--bg2);border:1px solid var(--border);border-radius:12px;overflow:hidden;}
.card-h{padding:12px 18px;border-bottom:1px solid var(--border);background:var(--bg3);display:flex;justify-content:space-between;}
.card-hl{font-size:10px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--text3);}
.card-hr{font-size:11px;font-family:var(--mono);color:var(--text3);}
.trace{padding:12px 0;font-family:var(--mono);font-size:13px;line-height:1.65;}
.sep{height:1px;background:var(--border);margin:8px 0;}
.row{display:flex;align-items:baseline;padding:2px 0;}
.tag{font-size:10px;font-weight:700;padding:0 8px;margin:0 12px;border-radius:3px;flex-shrink:0;font-family:var(--sans);line-height:20px;align-self:center;}
.tag.out{background:var(--blue-bg);color:var(--blue);}
.tag.in{background:var(--green-bg);color:var(--green);}
.tag.ok{background:var(--teal-bg);color:var(--teal);}
.tag.err{background:var(--red-bg);color:var(--red);}
.txt.out{color:var(--blue);}.txt.in{color:var(--green);}
.txt.ok{color:var(--teal);font-weight:600;}.txt.err{color:var(--red);}
.foot{max-width:660px;margin:20px auto 0;font-size:11px;color:var(--text3);text-align:center;}
</style></head><body>
<div class="hdr"><div class="ttl">⟨/⟩ Interaction Trace</div>
<div class="meta">
<span class="chip">🕐 )"; html += now; html += R"(</span>
<span class="chip">🔒 )"; html += HtmlEsc(secret_preview); html += R"(</span>
<span class="chip">⚙ )"; html += HtmlEsc(interp_name); html += R"(</span>
<span class="chip">📊 질의 )"; html += std::to_string(q_cnt); html += R"(회</span>
</div></div>
<div class="card">
<div class="card-h"><span class="card-hl">인터랙션 로그</span>
<span class="card-hr">)"; html += std::to_string(steps.size()); html += R"(개 이벤트</span></div>
<div class="trace">)"; html += rows; html += R"(</div></div>
<div class="foot">generated by interactive problem simulator</div>
</body></html>)";
    return html;
}

/* ══════════════════════════════════════════════════════════════════════════
   GDI helpers  (brushes / pens cached per HWND lifetime)
   ══════════════════════════════════════════════════════════════════════════ */
struct BrushCache {
    std::vector<std::pair<COLORREF,HBRUSH>> v;
    HBRUSH get(COLORREF c) {
        for (auto& p : v) if (p.first==c) return p.second;
        HBRUSH b = CreateSolidBrush(c); v.push_back({c,b}); return b;
    }
    ~BrushCache() { for (auto& p:v) DeleteObject(p.second); }
} g_brushes;

/* ══════════════════════════════════════════════════════════════════════════
   Custom edit subclass  —  Ctrl+A 전체선택 + 배경색
   ══════════════════════════════════════════════════════════════════════════ */
static WNDPROC g_origEdit = nullptr;
static LRESULT CALLBACK EditSubclass(HWND hw, UINT msg, WPARAM wp, LPARAM lp) {
    if (msg == WM_KEYDOWN && wp == 'A' && (GetKeyState(VK_CONTROL) & 0x8000)) {
        SendMessageW(hw, EM_SETSEL, 0, -1);   // select all
        return 0;
    }
    if (msg == WM_ERASEBKGND) {
        RECT rc; GetClientRect(hw, &rc);
        FillRect((HDC)wp, &rc, g_brushes.get(COL_BG));
        return 1;
    }
    return CallWindowProcW(g_origEdit, hw, msg, wp, lp);
}

/* ══════════════════════════════════════════════════════════════════════════
   Custom button
   ══════════════════════════════════════════════════════════════════════════ */
struct BtnState { bool hover=false; bool pressed=false; bool enabled=true; };

struct CustomBtn {
    HWND hw = nullptr;
    std::wstring text;
    COLORREF bg, fg, hover_bg;
    BtnState state;
    std::function<void()> onClick;
    static WNDPROC orig;

    static LRESULT CALLBACK Proc(HWND hw, UINT msg, WPARAM wp, LPARAM lp) {
        CustomBtn* btn = (CustomBtn*)GetWindowLongPtrW(hw, GWLP_USERDATA);
        if (!btn) return CallWindowProcW(orig, hw, msg, wp, lp);
        switch(msg) {
        case WM_PAINT: {
            PAINTSTRUCT ps; HDC dc = BeginPaint(hw, &ps);
            RECT rc; GetClientRect(hw, &rc);
            COLORREF bg = (!btn->state.enabled) ? COL_BG3 :
                           btn->state.hover      ? btn->hover_bg : btn->bg;
            FillRect(dc, &rc, g_brushes.get(bg));
            SetBkMode(dc, TRANSPARENT);
            SetTextColor(dc, btn->state.enabled ? btn->fg : COL_TEXT3);
            HFONT fnt = (HFONT)GetStockObject(DEFAULT_GUI_FONT);
            HFONT old = (HFONT)SelectObject(dc, fnt);
            DrawTextW(dc, btn->text.c_str(), -1, &rc, DT_CENTER|DT_VCENTER|DT_SINGLELINE);
            SelectObject(dc, old);
            EndPaint(hw, &ps); return 0;
        }
        case WM_MOUSEMOVE:
            if (!btn->state.hover) {
                btn->state.hover=true; InvalidateRect(hw,nullptr,FALSE);
                TRACKMOUSEEVENT tme{sizeof(tme),TME_LEAVE,hw,0}; TrackMouseEvent(&tme);
            } return 0;
        case WM_MOUSELEAVE:
            btn->state.hover=false; InvalidateRect(hw,nullptr,FALSE); return 0;
        case WM_LBUTTONDOWN:
            if(btn->state.enabled){ btn->state.pressed=true; SetCapture(hw); } return 0;
        case WM_LBUTTONUP:
            if(btn->state.pressed){
                btn->state.pressed=false; ReleaseCapture();
                POINT pt{LOWORD(lp),HIWORD(lp)};
                RECT rc2; GetClientRect(hw,&rc2);
                if(btn->state.enabled && PtInRect(&rc2,pt) && btn->onClick) btn->onClick();
            } return 0;
        case WM_ENABLE:
            btn->state.enabled=(wp!=0); InvalidateRect(hw,nullptr,FALSE); return 0;
        case WM_ERASEBKGND: return 1;
        }
        return CallWindowProcW(orig, hw, msg, wp, lp);
    }
};
WNDPROC CustomBtn::orig = nullptr;

static HWND MakeBtn(HWND parent, const wchar_t* text,
                    COLORREF bg, COLORREF fg, COLORREF hover_bg,
                    std::function<void()> cb, CustomBtn** out=nullptr) {
    HWND hw = CreateWindowExW(0, L"BUTTON", text,
        WS_CHILD|WS_VISIBLE|BS_OWNERDRAW,
        0,0,0,0, parent, nullptr, GetModuleHandleW(nullptr), nullptr);
    auto* btn = new CustomBtn();
    btn->hw=hw; btn->text=text; btn->bg=bg; btn->fg=fg;
    btn->hover_bg=hover_bg; btn->onClick=std::move(cb);
    SetWindowLongPtrW(hw, GWLP_USERDATA, (LONG_PTR)btn);
    if (!CustomBtn::orig)
        CustomBtn::orig = (WNDPROC)GetWindowLongPtrW(hw, GWLP_WNDPROC);
    SetWindowLongPtrW(hw, GWLP_WNDPROC, (LONG_PTR)CustomBtn::Proc);
    if (out) *out = btn;
    return hw;
}

/* ══════════════════════════════════════════════════════════════════════════
   Fonts
   ══════════════════════════════════════════════════════════════════════════ */
static HFONT g_fontCode = nullptr;   // Cascadia Code 11pt
static HFONT g_fontUI   = nullptr;   // Segoe UI 9pt
static HFONT g_fontUIB  = nullptr;   // Segoe UI 9pt bold
static HFONT g_fontMono = nullptr;   // Cascadia Code 10pt (trace)
static HFONT g_fontTop  = nullptr;   // Cascadia Code 12pt bold (logo)

static void CreateFonts(int dpi) {
    auto MF = [&](const wchar_t* face, int pt, bool bold=false, bool italic=false) -> HFONT {
        return CreateFontW(-MulDiv(pt, dpi, 72), 0,0,0,
            bold?FW_BOLD:FW_NORMAL, italic, FALSE, FALSE,
            DEFAULT_CHARSET, OUT_DEFAULT_PRECIS, CLIP_DEFAULT_PRECIS,
            CLEARTYPE_QUALITY, DEFAULT_PITCH, face);
    };
    g_fontCode  = MF(L"Cascadia Code", 11);
    g_fontUI    = MF(L"Segoe UI",      9);
    g_fontUIB   = MF(L"Segoe UI",      9,  true);
    g_fontMono  = MF(L"Cascadia Code", 10);
    g_fontTop   = MF(L"Cascadia Code", 12, true);
}

/* ══════════════════════════════════════════════════════════════════════════
   Trace pane  (owner-drawn scrollable list)
   ══════════════════════════════════════════════════════════════════════════ */
struct TraceItem { int kind; std::wstring text; };  // 0=out,1=in,2=ok,3=err,4=sep

class TracePane {
public:
    HWND hw = nullptr;
    std::vector<TraceItem> items;
    int scroll_pos = 0;
    int item_h     = 18;
    std::mutex mtx;

    void Create(HWND parent) {
        WNDCLASSEXW wc{};
        wc.cbSize=sizeof(wc); wc.style=CS_HREDRAW|CS_VREDRAW;
        wc.lpfnWndProc=Proc; wc.hInstance=GetModuleHandleW(nullptr);
        wc.hbrBackground=g_brushes.get(COL_BG);
        wc.lpszClassName=L"TracePane";
        RegisterClassExW(&wc);
        hw = CreateWindowExW(0,L"TracePane",nullptr,
            WS_CHILD|WS_VISIBLE|WS_VSCROLL,
            0,0,0,0,parent,nullptr,GetModuleHandleW(nullptr),(LPVOID)this);
    }

    void AddItem(int kind, const std::wstring& text) {
        { std::lock_guard<std::mutex> lk(mtx);
          items.push_back({kind, text}); }
        UpdateScrollRange();
        ScrollToBottom();
        InvalidateRect(hw, nullptr, FALSE);
    }

    void Clear() {
        { std::lock_guard<std::mutex> lk(mtx); items.clear(); }
        scroll_pos=0; UpdateScrollRange();
        InvalidateRect(hw, nullptr, FALSE);
    }

private:
    void UpdateScrollRange() {
        int count; { std::lock_guard<std::mutex> lk(mtx); count=(int)items.size(); }
        RECT rc; GetClientRect(hw, &rc);
        int visible = (rc.bottom - rc.top) / item_h;
        SCROLLINFO si{sizeof(si), SIF_RANGE|SIF_PAGE};
        si.nMin=0; si.nMax=max(0,count-1); si.nPage=visible;
        SetScrollInfo(hw, SB_VERT, &si, TRUE);
    }
    void ScrollToBottom() {
        int count; { std::lock_guard<std::mutex> lk(mtx); count=(int)items.size(); }
        SCROLLINFO si{sizeof(si),SIF_ALL}; GetScrollInfo(hw,SB_VERT,&si);
        si.nPos = max(0, count - (int)si.nPage);
        si.fMask = SIF_POS; SetScrollInfo(hw,SB_VERT,&si,TRUE);
        scroll_pos = si.nPos;
    }

    static LRESULT CALLBACK Proc(HWND hw, UINT msg, WPARAM wp, LPARAM lp) {
        TracePane* tp = (TracePane*)GetWindowLongPtrW(hw, GWLP_USERDATA);
        if (msg==WM_CREATE) {
            tp = (TracePane*)((CREATESTRUCTW*)lp)->lpCreateParams;
            SetWindowLongPtrW(hw, GWLP_USERDATA, (LONG_PTR)tp);
            return 0;
        }
        if (!tp) return DefWindowProcW(hw,msg,wp,lp);
        switch(msg) {
        case WM_SIZE:
            tp->UpdateScrollRange(); return 0;
        case WM_VSCROLL: {
            SCROLLINFO si{sizeof(si),SIF_ALL}; GetScrollInfo(hw,SB_VERT,&si);
            int old=si.nPos;
            switch(LOWORD(wp)){
            case SB_LINEUP:   si.nPos--;break; case SB_LINEDOWN: si.nPos++;break;
            case SB_PAGEUP:   si.nPos-=(int)si.nPage;break;
            case SB_PAGEDOWN: si.nPos+=(int)si.nPage;break;
            case SB_THUMBTRACK: si.nPos=si.nTrackPos;break;
            }
            si.nPos=max(si.nMin,min(si.nPos,si.nMax-(int)si.nPage+1));
            if(si.nPos!=old){ si.fMask=SIF_POS; SetScrollInfo(hw,SB_VERT,&si,TRUE);
                tp->scroll_pos=si.nPos; InvalidateRect(hw,nullptr,FALSE); }
            return 0;
        }
        case WM_MOUSEWHEEL: {
            int delta = GET_WHEEL_DELTA_WPARAM(wp)/WHEEL_DELTA;
            SCROLLINFO si{sizeof(si),SIF_ALL}; GetScrollInfo(hw,SB_VERT,&si);
            si.nPos = max(si.nMin, min(si.nPos - delta*3, si.nMax-(int)si.nPage+1));
            si.fMask=SIF_POS; SetScrollInfo(hw,SB_VERT,&si,TRUE);
            tp->scroll_pos=si.nPos; InvalidateRect(hw,nullptr,FALSE); return 0;
        }
        case WM_PAINT: {
            PAINTSTRUCT ps; HDC dc=BeginPaint(hw,&ps);
            RECT cr; GetClientRect(hw,&cr);
            // double-buffer
            HDC mdc=CreateCompatibleDC(dc);
            HBITMAP bmp=CreateCompatibleBitmap(dc,cr.right,cr.bottom);
            SelectObject(mdc,bmp);
            FillRect(mdc,&cr,g_brushes.get(COL_BG));

            int ih=tp->item_h;
            std::vector<TraceItem> snap;
            { std::lock_guard<std::mutex> lk(tp->mtx); snap=tp->items; }
            int start=tp->scroll_pos;

            HFONT oldFont=(HFONT)SelectObject(mdc,g_fontMono);
            SetBkMode(mdc,TRANSPARENT);

            for(int i=start; i<(int)snap.size(); i++){
                int y=(i-start)*ih;
                if(y>=cr.bottom) break;
                auto& it=snap[i];
                RECT row{0,y,cr.right,y+ih};

                if(it.kind==4){ // separator
                    RECT line{12,y+ih/2,cr.right-12,y+ih/2+1};
                    FillRect(mdc,&line,g_brushes.get(COL_BORDER));
                    continue;
                }

                // tag badge
                const wchar_t* label=L"";
                COLORREF tag_bg=COL_BG3, tag_fg=COL_TEXT3, txt_col=COL_TEXT;
                switch(it.kind){
                case 0: label=L"출력"; tag_bg=COL_BLUE_BG; tag_fg=COL_BLUE;  txt_col=COL_BLUE;  break;
                case 1: label=L"입력"; tag_bg=COL_GREEN_BG;tag_fg=COL_GREEN; txt_col=COL_GREEN; break;
                case 2: label=L"결과"; tag_bg=COL_TEAL_BG; tag_fg=COL_TEAL;  txt_col=COL_TEAL;  break;
                case 3: label=L"오류"; tag_bg=COL_RED_BG;  tag_fg=COL_RED;   txt_col=COL_RED;   break;
                }

                // tag rect (fixed 36px wide)
                SelectObject(mdc,g_fontUI);
                RECT tag_rc{12, y+1, 48, y+ih-1};
                FillRect(mdc,&tag_rc,g_brushes.get(tag_bg));
                SetTextColor(mdc,tag_fg);
                DrawTextW(mdc,label,-1,&tag_rc,DT_CENTER|DT_VCENTER|DT_SINGLELINE);

                // text
                SelectObject(mdc,g_fontMono);
                SetTextColor(mdc,txt_col);
                RECT txt_rc{56, y, cr.right-4, y+ih};
                DrawTextW(mdc,it.text.c_str(),-1,&txt_rc,DT_LEFT|DT_VCENTER|DT_SINGLELINE|DT_NOPREFIX);
            }
            SelectObject(mdc,oldFont);
            BitBlt(dc,0,0,cr.right,cr.bottom,mdc,0,0,SRCCOPY);
            DeleteObject(bmp); DeleteDC(mdc);
            EndPaint(hw,&ps); return 0;
        }
        case WM_ERASEBKGND: return 1;
        }
        return DefWindowProcW(hw,msg,wp,lp);
    }
};

/* ══════════════════════════════════════════════════════════════════════════
   Main window
   ══════════════════════════════════════════════════════════════════════════ */
#define IDC_SOL_EDIT    101
#define IDC_IACT_EDIT   102
#define IDC_SEC_EDIT    103
#define IDC_RUN_BTN     104
#define IDC_EXPORT_BTN  105
#define IDC_INTERP_BTN  106
#define IDC_INTERP_CHG  107
#define WM_ENGINE_STEP  (WM_USER+1)
#define WM_ENGINE_DONE  (WM_USER+2)

struct MainWnd {
    HWND  hw = nullptr;
    HWND  sol_edit = nullptr, iact_edit = nullptr, sec_edit = nullptr;
    HWND  interp_lbl = nullptr;
    TracePane trace;

    CustomBtn* run_btn    = nullptr;
    CustomBtn* export_btn = nullptr;
    CustomBtn* interp_btn = nullptr;
    CustomBtn* chg_btn    = nullptr;

    HWND  q_lbl     = nullptr;
    HWND  status_lbl= nullptr;
    HWND  dot_canvas= nullptr;   // small canvas for status dot
    HWND  splitter_hw= nullptr;  // drag handle between secret and buttons

    // secret pane resizable height
    int   sec_h      = 90;       // current height (px), user can drag
    bool  dragging_splitter = false;
    int   drag_start_y = 0, drag_start_h = 0;
    static constexpr int SEC_H_MIN = 40, SEC_H_MAX = 300;

    std::wstring interp_path;
    bool running = false;
    std::unique_ptr<Engine> engine;
    std::vector<Step> last_steps;
    std::string last_secret, last_interp_name;

    // ── autosave ─────────────────────────────────────────────────────────
    static constexpr UINT_PTR TIMER_AUTOSAVE = 1;
    bool autosave_pending = false;

    std::wstring AutosavePath(const wchar_t* name) {
        wchar_t exepath[MAX_PATH]; GetModuleFileNameW(nullptr, exepath, MAX_PATH);
        PathRemoveFileSpecW(exepath);
        std::wstring p = exepath; p += L"\\"; p += name;
        return p;
    }
    void ScheduleAutosave() {
        // debounce: reset 500ms timer on every change
        SetTimer(hw, TIMER_AUTOSAVE, 500, nullptr);
    }
    void DoAutosave() {
        KillTimer(hw, TIMER_AUTOSAVE);
        WriteUtf8File(AutosavePath(L"autosave_solution.py"),    w2s(GetEditText(sol_edit)));
        WriteUtf8File(AutosavePath(L"autosave_interactor.py"),  w2s(GetEditText(iact_edit)));
    }
    void LoadAutosave() {
        auto sol  = ReadUtf8File(AutosavePath(L"autosave_solution.py"));
        auto iact = ReadUtf8File(AutosavePath(L"autosave_interactor.py"));
        if (!sol.empty())  SetWindowTextW(sol_edit,  s2w(sol).c_str());
        if (!iact.empty()) SetWindowTextW(iact_edit, s2w(iact).c_str());
    }

    // ── status dot ───────────────────────────────────────────────────────
    COLORREF dot_color = COL_TEXT3;
    HWND status_right  = nullptr;

    void SetStatus(const wchar_t* text, COLORREF dot, const wchar_t* right=L"") {
        dot_color = dot;
        InvalidateRect(dot_canvas, nullptr, FALSE);
        SetWindowTextW(status_lbl,   text);
        SetWindowTextW(status_right, right);
    }

    // ── interpreter ──────────────────────────────────────────────────────
    void SetInterp(const std::wstring& path) {
        interp_path = path;
        std::wstring name = PathFindFileNameW(path.c_str());
        SetWindowTextW(interp_lbl, name.c_str());
        run_btn->state.enabled = !path.empty();
        InvalidateRect(run_btn->hw, nullptr, FALSE);
    }

    void ChooseInterp() {
        wchar_t buf[MAX_PATH] = {};
        OPENFILENAMEW ofn{}; ofn.lStructSize=sizeof(ofn); ofn.hwndOwner=hw;
        ofn.lpstrFilter=L"Python / PyPy 실행파일\0*.exe;python*;pypy*\0모든 파일\0*.*\0";
        ofn.lpstrFile=buf; ofn.nMaxFile=MAX_PATH;
        ofn.Flags=OFN_FILEMUSTEXIST|OFN_PATHMUSTEXIST;
        if (GetOpenFileNameW(&ofn)) SetInterp(buf);
    }

    // ── run ──────────────────────────────────────────────────────────────
    void Run() {
        if (running) return;
        if (interp_path.empty() || !PathFileExistsW(interp_path.c_str())) {
            MessageBoxW(hw, L"먼저 인터프리터를 선택하세요.", L"인터프리터 없음", MB_ICONWARNING);
            return;
        }
        running = true;
        run_btn->state.enabled    = false; InvalidateRect(run_btn->hw, nullptr, FALSE);
        export_btn->state.enabled = false; InvalidateRect(export_btn->hw, nullptr, FALSE);
        trace.Clear();
        SetWindowTextW(q_lbl, L"");
        SetStatus(L"실행 중…", COL_AMBER);

        // collect code / secret
        auto sol    = w2s(GetEditText(sol_edit));
        auto iact   = w2s(GetEditText(iact_edit));
        auto secret = w2s(GetEditText(sec_edit));
        last_secret       = secret;
        last_interp_name  = w2s(PathFindFileNameW(interp_path.c_str()));

        engine = std::make_unique<Engine>();
        engine->interp    = interp_path;
        engine->sol_code  = sol;
        engine->iact_code = iact;
        engine->secret    = secret;

        engine->on_step = [this]{
            PostMessageW(hw, WM_ENGINE_STEP, 0, 0);
        };
        engine->on_done = [this]{
            PostMessageW(hw, WM_ENGINE_DONE, 0, 0);
        };
        engine->run_async();
    }

    // ── called on WM_ENGINE_STEP ─────────────────────────────────────────
    int rendered_idx = 0;
    void FlushNewSteps() {
        if (!engine) return;
        std::vector<Step> snap;
        { std::lock_guard<std::mutex> lk(engine->steps_mtx);
          snap = engine->steps; }
        int q = 0;
        for (int i = rendered_idx; i < (int)snap.size(); i++) {
            auto& s = snap[i];
            int kind = s.kind=="output"?0:s.kind=="input"?1:s.kind=="result"?2:
                       s.kind=="error"?3:4;
            if (kind==2) trace.AddItem(4, L"");  // separator before result
            trace.AddItem(kind, s2w(s.text));
            if (s.kind=="output") q++;
        }
        rendered_idx = (int)snap.size();
        // update query count
        int total_q = 0;
        for (auto& s : snap)
            if (s.kind=="output") total_q++;
        if (total_q > 0) {
            SetWindowTextW(q_lbl, (std::to_wstring(total_q)+L"회 질의").c_str());
        }
    }

    void OnDone() {
        FlushNewSteps();  // flush any last steps
        if (!engine) return;
        last_steps.clear();
        { std::lock_guard<std::mutex> lk(engine->steps_mtx); last_steps = engine->steps; }
        int rc = engine->rc;

        if (rc == 0) {
            int q=0; for(auto&s:last_steps) if(s.kind=="output") q++;
            SetStatus(L"완료", COL_GREEN,
                (std::to_wstring(q)+L"회 질의").c_str());
        } else {
            SetStatus(L"오답 / 오류", COL_RED);
        }
        running = false;
        run_btn->state.enabled    = true; InvalidateRect(run_btn->hw, nullptr, FALSE);
        export_btn->state.enabled = true; InvalidateRect(export_btn->hw, nullptr, FALSE);
        rendered_idx = 0;
    }

    // ── export ───────────────────────────────────────────────────────────
    void Export() {
        if (last_steps.empty()) return;
        std::string preview = last_secret;
        size_t nl = preview.find('\n'); if (nl!=std::string::npos) preview=preview.substr(0,nl);
        if (preview.size()>40) preview=preview.substr(0,40);

        std::string html = BuildHtml(last_steps, preview, last_interp_name);

        wchar_t buf[MAX_PATH] = L"trace_export.html";
        OPENFILENAMEW ofn{}; ofn.lStructSize=sizeof(ofn); ofn.hwndOwner=hw;
        ofn.lpstrFilter=L"HTML 파일\0*.html\0";
        ofn.lpstrFile=buf; ofn.nMaxFile=MAX_PATH;
        ofn.lpstrDefExt=L"html";
        ofn.Flags=OFN_OVERWRITEPROMPT;
        if (!GetSaveFileNameW(&ofn)) return;

        std::ofstream f(buf, std::ios::binary);
        f.write(html.c_str(), html.size());
        f.close();

        // open in browser
        ShellExecuteW(nullptr, L"open", buf, nullptr, nullptr, SW_SHOWNORMAL);
    }

    // ── layout ───────────────────────────────────────────────────────────
    // All sidebar positions derived from sec_h so splitter drag auto-reflows.
    static constexpr int TOPBAR_H  = 48;
    static constexpr int BORDER_W  = 1;
    static constexpr int SIDEBAR_W = 320;
    static constexpr int HDR_H     = 56;   // panel header height (two-line)
    static constexpr int SPLITTER_H= 5;    // drag handle height
    static constexpr int BTN_RUN_H = 36;
    static constexpr int BTN_EXP_H = 28;
    static constexpr int TRACE_HDR = 32;
    static constexpr int STATUS_H  = 30;
    static constexpr int PAD       = 14;   // horizontal padding inside sidebar

    void Layout(int W, int H) {
        int body_y = TOPBAR_H + BORDER_W;
        int body_h = H - body_y;
        int col_w  = (W - SIDEBAR_W - 2*BORDER_W) / 2;
        int col2_x = col_w + BORDER_W;
        int sb_x   = col2_x + col_w + BORDER_W;

        // code editors (below header)
        MoveWindow(sol_edit,  0,     body_y + HDR_H, col_w, body_h - HDR_H, TRUE);
        MoveWindow(iact_edit, col2_x,body_y + HDR_H, col_w, body_h - HDR_H, TRUE);

        // ── sidebar ──
        int y = body_y;

        // secret label + edit
        // y+28 = below label text
        MoveWindow(sec_edit, sb_x+PAD, y+28, SIDEBAR_W-PAD*2, sec_h, TRUE);
        y += 28 + sec_h;

        // splitter
        MoveWindow(splitter_hw, sb_x, y, SIDEBAR_W, SPLITTER_H, TRUE);
        y += SPLITTER_H + 8;

        // run btn
        MoveWindow(run_btn->hw, sb_x+PAD, y, SIDEBAR_W-PAD*2, BTN_RUN_H, TRUE);
        y += BTN_RUN_H + 6;

        // export btn
        MoveWindow(export_btn->hw, sb_x+PAD, y, SIDEBAR_W-PAD*2, BTN_EXP_H, TRUE);
        y += BTN_EXP_H + 10;

        // trace header + pane
        MoveWindow(q_lbl, sb_x + SIDEBAR_W - 90, y + 6, 84, 20, TRUE);
        int trace_y = y + TRACE_HDR;
        int trace_h = H - trace_y - STATUS_H;
        if (trace_h < 20) trace_h = 20;
        if (trace.hw) MoveWindow(trace.hw, sb_x, trace_y, SIDEBAR_W, trace_h, TRUE);

        // status bar
        int st_y = H - STATUS_H;
        MoveWindow(dot_canvas,   sb_x+12,  st_y+10, 10, 10, TRUE);
        MoveWindow(status_lbl,   sb_x+28,  st_y+6,  120, 20, TRUE);
        MoveWindow(status_right, sb_x+160, st_y+6,  SIDEBAR_W-170, 20, TRUE);

        // topbar
        MoveWindow(interp_lbl, W-260, 12, 180, 24, TRUE);
        MoveWindow(chg_btn->hw, W-72, 12, 60, 24, TRUE);

        InvalidateRect(hw, nullptr, FALSE);
    }

    // ── Splitter subclass ─────────────────────────────────────────────────
    static WNDPROC s_origSplitter;
    static LRESULT CALLBACK SplitterProc(HWND hw, UINT msg, WPARAM wp, LPARAM lp) {
        MainWnd* wnd = (MainWnd*)GetWindowLongPtrW(GetParent(hw), GWLP_USERDATA);
        switch (msg) {
        case WM_SETCURSOR:
            SetCursor(LoadCursorW(nullptr, IDC_SIZENS)); return TRUE;
        case WM_LBUTTONDOWN:
            if (wnd) {
                wnd->dragging_splitter = true;
                wnd->drag_start_y = GET_Y_LPARAM(lp);
                // convert to screen coords
                POINT pt{0, wnd->drag_start_y};
                ClientToScreen(hw, &pt);
                wnd->drag_start_y = pt.y;
                wnd->drag_start_h = wnd->sec_h;
                SetCapture(hw);
            }
            return 0;
        case WM_MOUSEMOVE:
            if (wnd && wnd->dragging_splitter) {
                POINT pt{0, GET_Y_LPARAM(lp)};
                ClientToScreen(hw, &pt);
                int delta = pt.y - wnd->drag_start_y;
                int new_h = wnd->drag_start_h + delta;
                new_h = max(SEC_H_MIN, min(new_h, SEC_H_MAX));
                if (new_h != wnd->sec_h) {
                    wnd->sec_h = new_h;
                    RECT rc; GetClientRect(GetParent(hw), &rc);
                    wnd->Layout(rc.right, rc.bottom);
                }
            }
            return 0;
        case WM_LBUTTONUP:
            if (wnd) { wnd->dragging_splitter = false; ReleaseCapture(); }
            return 0;
        case WM_PAINT: {
            PAINTSTRUCT ps; HDC dc = BeginPaint(hw, &ps);
            RECT rc; GetClientRect(hw, &rc);
            FillRect(dc, &rc, g_brushes.get(COL_BG3));
            // center grip dots
            int cx = rc.right/2, cy = rc.bottom/2;
            for (int i = -12; i <= 12; i += 6) {
                RECT dot{cx+i-1, cy-1, cx+i+1, cy+1};
                FillRect(dc, &dot, g_brushes.get(COL_BORDER2));
            }
            EndPaint(hw, &ps); return 0;
        }
        case WM_ERASEBKGND: return 1;
        }
        return CallWindowProcW(s_origSplitter, hw, msg, wp, lp);
    }

    // ── WndProc ──────────────────────────────────────────────────────────
    static LRESULT CALLBACK WndProc(HWND hw, UINT msg, WPARAM wp, LPARAM lp) {
        MainWnd* wnd = (MainWnd*)GetWindowLongPtrW(hw, GWLP_USERDATA);
        switch(msg) {
        case WM_CREATE: {
            wnd = (MainWnd*)((CREATESTRUCTW*)lp)->lpCreateParams;
            SetWindowLongPtrW(hw, GWLP_USERDATA, (LONG_PTR)wnd);
            wnd->hw = hw;
            wnd->CreateControls();
            return 0;
        }
        case WM_SIZE:
            if(wnd) wnd->Layout(LOWORD(lp),HIWORD(lp)); return 0;
        case WM_PAINT: {
            if(!wnd) break;
            PAINTSTRUCT ps; HDC dc=BeginPaint(hw,&ps);
            RECT cr; GetClientRect(hw,&cr);
            // topbar
            RECT tb{0,0,cr.right,48};
            FillRect(dc,&tb,g_brushes.get(COL_BG2));
            // logo
            SetBkMode(dc,TRANSPARENT); SetTextColor(dc,COL_BLUE);
            HFONT old=(HFONT)SelectObject(dc,g_fontTop);
            RECT lr{16,10,300,38};
            DrawTextW(dc,L"⟨/⟩ interactive sim",-1,&lr,DT_LEFT|DT_VCENTER|DT_SINGLELINE);
            // interp label static text
            SelectObject(dc,g_fontUI);
            SetTextColor(dc,COL_TEXT3);
            RECT il{cr.right-320,14,cr.right-270,34};
            DrawTextW(dc,L"인터프리터:",-1,&il,DT_LEFT|DT_VCENTER|DT_SINGLELINE);
            SelectObject(dc,old);
            // top border
            RECT brd{0,48,cr.right,49};
            FillRect(dc,&brd,g_brushes.get(COL_BORDER));
            // body bg
            RECT body{0,49,cr.right,cr.bottom};
            FillRect(dc,&body,g_brushes.get(COL_BG));
            // column dividers
            int W=cr.right, H=cr.bottom, SIDEBAR=320, BW=1;
            int col_w=(W-SIDEBAR-2*BW)/2;
            RECT div1{col_w,49,col_w+BW,H};
            FillRect(dc,&div1,g_brushes.get(COL_BORDER));
            RECT div2{col_w+BW+col_w,49,col_w+BW+col_w+BW,H};
            FillRect(dc,&div2,g_brushes.get(COL_BORDER));

            // panel headers
            wnd->DrawPanelHeaders(dc, W, H);
            wnd->DrawSidebar(dc, W, H);
            EndPaint(hw,&ps); return 0;
        }
        case WM_CTLCOLOREDIT:
        case WM_CTLCOLORSTATIC: {
            HDC dc=(HDC)wp; HWND ctrl=(HWND)lp;
            if(!wnd) break;
            SetBkColor(dc, COL_BG); SetTextColor(dc, COL_TEXT);
            SetBkMode(dc, OPAQUE);
            return (LRESULT)g_brushes.get(COL_BG);
        }
        case WM_DRAWITEM: {
            // dot canvas
            if (!wnd) break;
            auto* dis=(DRAWITEMSTRUCT*)lp;
            if(dis->hwndItem==wnd->dot_canvas){
                FillRect(dis->hDC,&dis->rcItem,g_brushes.get(COL_BG));
                HBRUSH br=g_brushes.get(wnd->dot_color);
                SelectObject(dis->hDC,br);
                SelectObject(dis->hDC,GetStockObject(NULL_PEN));
                Ellipse(dis->hDC,0,0,9,9);
            }
            return TRUE;
        }
        case WM_COMMAND: {
            if (!wnd) break;
            UINT notif = HIWORD(wp);
            HWND ctrl  = (HWND)lp;
            if (notif == EN_CHANGE &&
                (ctrl == wnd->sol_edit || ctrl == wnd->iact_edit))
                wnd->ScheduleAutosave();
            break;
        }
        case WM_TIMER:
            if (wnd && wp == MainWnd::TIMER_AUTOSAVE) { wnd->DoAutosave(); return 0; }
            break;
        case WM_ENGINE_STEP:
            if(wnd) wnd->FlushNewSteps(); return 0;
        case WM_ENGINE_DONE:
            if(wnd) wnd->OnDone(); return 0;
        case WM_KEYDOWN:
            if(wp==VK_RETURN && (GetKeyState(VK_CONTROL)&0x8000) && wnd && !wnd->running)
                wnd->Run();
            return 0;
        case WM_DESTROY:
            if(wnd) { wnd->DoAutosave(); }   // final save on close
            if(wnd && wnd->engine) wnd->engine->kill_flag=true;
            PostQuitMessage(0); return 0;
        case WM_ERASEBKGND: return 1;
        }
        return DefWindowProcW(hw,msg,wp,lp);
    }

    void DrawPanelHeaders(HDC dc, int W, int H) {
        int BW=1;
        int col_w=(W-SIDEBAR_W-2*BW)/2;
        int body_y = TOPBAR_H + BW;
        int hdr_bot = body_y + HDR_H;

        auto DrawOneHeader = [&](int x, int w, const wchar_t* ko_title,
                                  const wchar_t* en_sub, const wchar_t* badge,
                                  COLORREF badge_col) {
            // header bg
            RECT hbg{x, body_y, x+w, hdr_bot};
            FillRect(dc, &hbg, g_brushes.get(COL_BG2));
            // bottom border
            RECT hbd{x, hdr_bot-1, x+w, hdr_bot};
            FillRect(dc, &hbd, g_brushes.get(COL_BORDER));

            SetBkMode(dc, TRANSPARENT);

            // Korean title — large, bold, top line
            HFONT oldF = (HFONT)SelectObject(dc, g_fontUIB);
            SetTextColor(dc, COL_TEXT);
            RECT rko{x+12, body_y+6, x+w-8, body_y+28};
            DrawTextW(dc, ko_title, -1, &rko, DT_LEFT|DT_VCENTER|DT_SINGLELINE);

            // English subtitle — smaller, muted
            SelectObject(dc, g_fontUI);
            SetTextColor(dc, COL_TEXT3);
            RECT ren{x+12, body_y+28, x+120, hdr_bot-4};
            DrawTextW(dc, en_sub, -1, &ren, DT_LEFT|DT_VCENTER|DT_SINGLELINE);

            // badge (filename)
            SelectObject(dc, g_fontMono);
            SetTextColor(dc, badge_col);
            RECT rb{x+w-130, body_y+28, x+w-6, hdr_bot-4};
            DrawTextW(dc, badge, -1, &rb, DT_RIGHT|DT_VCENTER|DT_SINGLELINE);

            SelectObject(dc, oldF);
        };

        DrawOneHeader(0,      col_w, L"정답 코드",  L"SOLUTION",   L"solution.py",   COL_BLUE);
        DrawOneHeader(col_w+BW, col_w, L"인터랙터 코드", L"INTERACTOR", L"interactor.py", COL_GREEN);
    }

    void DrawSidebar(HDC dc, int W, int H) {
        int sb_x = W - SIDEBAR_W;
        int body_y = TOPBAR_H + BORDER_W;

        // sidebar bg
        RECT sb{sb_x,body_y,W,H}; FillRect(dc,&sb,g_brushes.get(COL_BG2));

        auto hdiv=[&](int y){ RECT r{sb_x,y,W,y+1}; FillRect(dc,&r,g_brushes.get(COL_BORDER)); };

        HFONT oldf=(HFONT)SelectObject(dc,g_fontUIB);
        SetBkMode(dc,TRANSPARENT);

        // secret label
        SetTextColor(dc,COL_TEXT3);
        RECT sl{sb_x+PAD, body_y+6, W-PAD, body_y+24};
        DrawTextW(dc,L"비밀 시나리오 (sys.argv[1])",-1,&sl,DT_LEFT|DT_VCENTER|DT_SINGLELINE);

        // positions mirroring Layout()
        int y = body_y + 28 + sec_h + SPLITTER_H + 8 + BTN_RUN_H + 6 + BTN_EXP_H + 10;

        hdiv(y);  // above trace header

        // trace header
        RECT th{sb_x,y,W,y+TRACE_HDR}; FillRect(dc,&th,g_brushes.get(COL_BG3));
        SelectObject(dc,g_fontUIB); SetTextColor(dc,COL_TEXT3);
        RECT thl{sb_x+PAD,y+4,W-100,y+TRACE_HDR-4};
        DrawTextW(dc,L"인터랙션 트레이스",-1,&thl,DT_LEFT|DT_VCENTER|DT_SINGLELINE);
        hdiv(y+TRACE_HDR);

        // status bar
        int st_y=H-STATUS_H;
        RECT stb{sb_x,st_y-1,W,st_y}; FillRect(dc,&stb,g_brushes.get(COL_BORDER));
        RECT stbb{sb_x,st_y,W,H}; FillRect(dc,&stbb,g_brushes.get(COL_BG));
        SelectObject(dc,oldf);
    }

    void CreateControls() {
        HINSTANCE inst = GetModuleHandleW(nullptr);

        // code editors
        sol_edit = CreateWindowExW(0,L"EDIT",nullptr,
            WS_CHILD|WS_VISIBLE|WS_VSCROLL|ES_MULTILINE|ES_AUTOVSCROLL|ES_WANTRETURN,
            0,85,0,0,hw,(HMENU)IDC_SOL_EDIT,inst,nullptr);
        iact_edit = CreateWindowExW(0,L"EDIT",nullptr,
            WS_CHILD|WS_VISIBLE|WS_VSCROLL|ES_MULTILINE|ES_AUTOVSCROLL|ES_WANTRETURN,
            0,85,0,0,hw,(HMENU)IDC_IACT_EDIT,inst,nullptr);

        for (HWND e : {sol_edit, iact_edit}) {
            SendMessageW(e, WM_SETFONT, (WPARAM)g_fontCode, TRUE);
            SendMessageW(e, EM_SETBKGNDCOLOR, 0, COL_BG);
            // subclass: Ctrl+A 전체선택
            if (!g_origEdit)
                g_origEdit = (WNDPROC)GetWindowLongPtrW(e, GWLP_WNDPROC);
            SetWindowLongPtrW(e, GWLP_WNDPROC, (LONG_PTR)EditSubclass);
        }

        // secret edit
        sec_edit = CreateWindowExW(0,L"EDIT",nullptr,
            WS_CHILD|WS_VISIBLE|WS_VSCROLL|ES_MULTILINE|ES_AUTOVSCROLL|ES_WANTRETURN,
            0,0,0,0,hw,(HMENU)IDC_SEC_EDIT,inst,nullptr);
        SendMessageW(sec_edit,EM_SETBKGNDCOLOR,0,COL_BG3);
        SendMessageW(sec_edit,WM_SETFONT,(WPARAM)g_fontCode,TRUE);
        // subclass secret edit too (Ctrl+A)
        SetWindowLongPtrW(sec_edit, GWLP_WNDPROC, (LONG_PTR)EditSubclass);
        SetWindowTextW(sec_edit, L"15");

        // splitter between secret and buttons
        splitter_hw = CreateWindowExW(0, L"STATIC", nullptr,
            WS_CHILD|WS_VISIBLE|SS_NOTIFY,
            0,0,0,0, hw, nullptr, inst, nullptr);
        if (!s_origSplitter)
            s_origSplitter = (WNDPROC)GetWindowLongPtrW(splitter_hw, GWLP_WNDPROC);
        SetWindowLongPtrW(splitter_hw, GWLP_WNDPROC, (LONG_PTR)SplitterProc);

        // interpreter label
        interp_lbl = CreateWindowExW(0,L"STATIC",L"선택 안 됨",
            WS_CHILD|WS_VISIBLE,0,0,0,0,hw,(HMENU)IDC_INTERP_BTN,inst,nullptr);
        SendMessageW(interp_lbl,WM_SETFONT,(WPARAM)g_fontMono,TRUE);

        // change button
        MakeBtn(hw,L"변경…",COL_BG3,COL_TEXT2,COL_BG4,[this]{ChooseInterp();},&chg_btn);
        // run button
        MakeBtn(hw,L"▶  실행  (Ctrl+Enter)",COL_BLUE,RGB(255,255,255),C(0x3a,0x7d,0xe8),[this]{Run();},&run_btn);
        run_btn->state.enabled = false;
        // export button
        MakeBtn(hw,L"↓  인터랙션 내보내기 (HTML)",COL_BG3,COL_TEXT2,COL_BG4,[this]{Export();},&export_btn);
        export_btn->state.enabled = false;

        // q_lbl
        q_lbl = CreateWindowExW(0,L"STATIC",L"",WS_CHILD|WS_VISIBLE,
            0,0,0,0,hw,nullptr,inst,nullptr);
        SendMessageW(q_lbl,WM_SETFONT,(WPARAM)g_fontMono,TRUE);

        // status
        dot_canvas = CreateWindowExW(0,L"BUTTON",nullptr,
            WS_CHILD|WS_VISIBLE|BS_OWNERDRAW,0,0,10,10,hw,nullptr,inst,nullptr);
        status_lbl = CreateWindowExW(0,L"STATIC",L"대기 중",WS_CHILD|WS_VISIBLE,
            0,0,0,0,hw,nullptr,inst,nullptr);
        SendMessageW(status_lbl,WM_SETFONT,(WPARAM)g_fontUI,TRUE);
        status_right = CreateWindowExW(0,L"STATIC",L"",WS_CHILD|WS_VISIBLE|SS_RIGHT,
            0,0,0,0,hw,nullptr,inst,nullptr);
        SendMessageW(status_right,WM_SETFONT,(WPARAM)g_fontMono,TRUE);

        // trace pane
        trace.item_h = 20;
        trace.Create(hw);

        // default texts
        SetWindowTextW(sol_edit,
            L"p=[2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71]\r\n"
            L"x=1\r\nprevx=1\r\n"
            L"for i in p:\r\n\tk=1\r\n\twhile 1:\r\n\t\tk*=i\r\n"
            L"\t\tif prevx*k>72:break\r\n\t\tprint(f'? {k}')\r\n"
            L"\t\ttry:v=int(input())\r\n\t\texcept:exit(1)\r\n"
            L"\t\tif not v:break\r\n\t\tx*=i\r\n\tprevx=x\r\nprint(f'! {x}')");

        SetWindowTextW(iact_edit,
            L"import sys\r\n\r\ndef main():\r\n"
            L"    if len(sys.argv) < 2:\r\n"
            L"        print('에러: 비밀 파일 경로가 없습니다.', file=sys.stderr)\r\n"
            L"        sys.exit(1)\r\n"
            L"    try:\r\n"
            L"        secret_n = int(open(sys.argv[1]).readline().strip())\r\n"
            L"        if secret_n <= 0: raise ValueError\r\n"
            L"    except Exception as e:\r\n"
            L"        print(f'에러: {e}', file=sys.stderr); sys.exit(1)\r\n\r\n"
            L"    MAX_QUERIES = 20\r\n    qcount = 0\r\n"
            L"    while True:\r\n"
            L"        line = sys.stdin.readline()\r\n"
            L"        if not line:\r\n"
            L"            print('에러: EOF', file=sys.stderr); sys.exit(1)\r\n"
            L"        parts = line.strip().split()\r\n"
            L"        if not parts: continue\r\n"
            L"        cmd = parts[0]\r\n"
            L"        if cmd == '?':\r\n"
            L"            if qcount >= MAX_QUERIES:\r\n"
            L"                print('오답: 질문 횟수 초과', file=sys.stderr); sys.exit(1)\r\n"
            L"            A = int(parts[1]); qcount += 1\r\n"
            L"            print(1 if secret_n % A == 0 else 0, flush=True)\r\n"
            L"        elif cmd == '!':\r\n"
            L"            ans = int(parts[1])\r\n"
            L"            if ans == secret_n: sys.exit(0)\r\n"
            L"            print(f'오답: 정답은 {secret_n}, 제출은 {ans}', file=sys.stderr); sys.exit(1)\r\n"
            L"        else:\r\n"
            L"            print(f'알 수 없는 명령어', file=sys.stderr); sys.exit(1)\r\n\r\n"
            L"if __name__ == '__main__':\r\n    main()");

        // load autosave (overwrites default text if files exist)
        LoadAutosave();

        // find pypy3.11.exe next to sim.exe
        wchar_t exepath[MAX_PATH]; GetModuleFileNameW(nullptr,exepath,MAX_PATH);
        PathRemoveFileSpecW(exepath);
        wchar_t cands[3][MAX_PATH];
        for(auto& c:cands) wcscpy_s(c,exepath);
        PathAppendW(cands[0],L"pypy3.11.exe");
        PathAppendW(cands[1],L"pypy3.exe");
        PathAppendW(cands[2],L"pypy.exe");
        for(auto& c:cands) if(PathFileExistsW(c)){SetInterp(c);break;}
        if(interp_path.empty()) { // fallback to python in PATH
            wchar_t python[MAX_PATH]=L"python.exe";
            if(SearchPathW(nullptr,L"python.exe",nullptr,MAX_PATH,python,nullptr)>0)
                SetInterp(python);
        }
    }
};
WNDPROC MainWnd::s_origSplitter = nullptr;

/* ══════════════════════════════════════════════════════════════════════════
   WinMain
   ══════════════════════════════════════════════════════════════════════════ */
int WINAPI WinMain(HINSTANCE inst, HINSTANCE, LPSTR, int) {
    // DPI awareness — load dynamically so it compiles against any SDK version
    {
        HMODULE u32 = GetModuleHandleW(L"user32.dll");
        if (u32) {
            typedef BOOL (WINAPI *PFN)(HANDLE);
            auto fn = (PFN)GetProcAddress(u32, "SetProcessDpiAwarenessContext");
            // DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 = (HANDLE)-4
            if (fn) fn((HANDLE)(LONG_PTR)-4);
        }
    }

    InitCommonControls();

    int dpi = 96;
    {HWND d=GetDesktopWindow(); HDC dc=GetDC(d); dpi=GetDeviceCaps(dc,LOGPIXELSX); ReleaseDC(d,dc);}
    CreateFonts(dpi);

    WNDCLASSEXW wc{};
    wc.cbSize=sizeof(wc); wc.style=CS_HREDRAW|CS_VREDRAW;
    wc.lpfnWndProc=MainWnd::WndProc;
    wc.hInstance=inst;
    wc.hbrBackground=g_brushes.get(COL_BG);
    wc.hCursor=LoadCursorW(nullptr,IDC_ARROW);
    wc.lpszClassName=L"InteractiveSim";
    RegisterClassExW(&wc);

    MainWnd wnd;

    HWND hw = CreateWindowExW(0, L"InteractiveSim",
        L"Interactive Problem Simulator",
        WS_OVERLAPPEDWINDOW,
        CW_USEDEFAULT,CW_USEDEFAULT, 1200, 780,
        nullptr, nullptr, inst, &wnd);

    ShowWindow(hw, SW_SHOW);
    UpdateWindow(hw);

    MSG msg;
    while (GetMessageW(&msg,nullptr,0,0)>0) {
        TranslateMessage(&msg);
        DispatchMessageW(&msg);
    }
    return (int)msg.wParam;
}