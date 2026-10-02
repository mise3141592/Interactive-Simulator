import sys

with open(sys.argv[1]) as f:
    secret = int(f.read().split()[0])

LIMIT = 20
queries = 0
while True:
    line = sys.stdin.readline()
    if not line:
        print("제출 프로그램이 아무것도 출력하지 않았습니다", file=sys.stderr)
        sys.exit(1)
    line = line.strip()
    if line == "":
        continue
    try:
        guess = int(line)
    except ValueError:
        print(f"정수가 아닌 출력: {line!r}", file=sys.stderr)
        sys.exit(1)
    queries += 1
    if queries > LIMIT:
        print(f"질문 횟수 {LIMIT}회 초과", file=sys.stderr)
        sys.exit(1)
    if guess == secret:
        print("=", flush=True)
        sys.exit(0)
    elif secret < guess:
        print("<", flush=True)
    else:
        print(">", flush=True)
