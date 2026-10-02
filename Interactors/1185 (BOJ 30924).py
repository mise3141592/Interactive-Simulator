# 숨긴 A, B 를 질문으로 맞히게 하고 A+B 검증
import sys

MAX_QUERIES = 19997  # 질문 횟수 제한


def fail(msg):
    print(msg, file=sys.stderr)
    sys.exit(1)


with open(sys.argv[1]) as f:
    A, B = map(int, f.read().split())

for _ in range(MAX_QUERIES):
    raw = sys.stdin.readline()
    if raw == "":
        fail("출력 없음 (제출 프로그램이 아무것도 출력하지 않고 끝났습니다)")
    line = raw.split()
    if not line:
        continue  # 빈 줄은 넘어간다
    op = line[0]
    if op == '?':
        if len(line) != 3:
            fail(f"잘못된 질문 형식입니다. '? A 값' 또는 '? B 값' 이어야 합니다: {raw.strip()!r}")
        who = line[1]
        if who not in ('A', 'B'):
            fail(f"질문 대상은 A 또는 B 여야 합니다: {who!r}")
        try:
            val = int(line[2])
        except ValueError:
            fail(f"질문 값이 정수가 아닙니다: {line[2]!r}")
        cur = A if who == 'A' else B
        print(1 if cur == val else 0, flush=True)
    elif op == '!':
        if len(line) != 2:
            fail(f"잘못된 정답 형식입니다. '! 값' 이어야 합니다: {raw.strip()!r}")
        try:
            ans = int(line[1])
        except ValueError:
            fail(f"정답이 정수가 아닙니다: {line[1]!r}")
        if ans == A + B:
            sys.exit(0)            # 정답
        fail(f"오답: {ans} != {A + B}")
    else:
        fail(f"잘못된 입력입니다. '?' 또는 '!' 로 시작해야 합니다: {raw.strip()!r}")

fail("질문 횟수 초과")
