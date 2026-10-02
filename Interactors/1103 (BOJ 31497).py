import sys

# 문제의 실제 질문 횟수 제한값으로 바꿔서 사용하세요 (문제 지문에서 N가 가려진 값).
MAX_QUERIES = 1000


def fail(msg):
    print(msg, file=sys.stderr)
    sys.exit(1)


def main():
    if len(sys.argv) < 2:
        fail("no scenario file given")

    with open(sys.argv[1], "r") as f:
        lines = [line.strip() for line in f if line.strip() != ""]

    idx = 0
    try:
        n = int(lines[idx]); idx += 1
        names = []
        for _ in range(n):
            names.append(lines[idx]); idx += 1
        birthday_name = lines[idx]; idx += 1
        lie_at = int(lines[idx]); idx += 1  # birthday_name에 대한 질문 중 몇 번째에서 거짓말할지 (0=거짓말 안함)
    except (IndexError, ValueError):
        fail("malformed scenario file")

    name_set = set(names)
    if birthday_name not in name_set:
        fail("scenario error: birthday_name not in names")

    # 학생 프로그램에게 초기 입력(N, 이름 목록)을 전달한다.
    print(n, flush=True)
    for name in names:
        print(name, flush=True)

    query_count = 0
    birthday_query_count = 0

    while True:
        line = sys.stdin.readline()
        if line == "":
            fail("unexpected EOF from participant (protocol violation)")
        line = line.strip()
        if line == "":
            continue

        tokens = line.split()
        cmd = tokens[0]

        if cmd == "?":
            if len(tokens) != 2:
                fail(f"malformed query: {line}")
            queried = tokens[1]

            if queried not in name_set:
                fail(f"queried name not in list: {queried}")

            query_count += 1
            if query_count > MAX_QUERIES:
                fail(f"exceeded max queries ({MAX_QUERIES})")

            if queried == birthday_name:
                birthday_query_count += 1
                # birthday_name에 대한 질문 중 lie_at번째에서만 거짓말(0)로 답한다.
                if birthday_query_count == lie_at:
                    answer = 0
                else:
                    answer = 1
            else:
                answer = 0

            print(answer, flush=True)

        elif cmd == "!":
            if len(tokens) != 2:
                fail(f"malformed answer: {line}")
            guessed = tokens[1]

            if guessed == birthday_name:
                sys.exit(0)
            else:
                fail(f"wrong answer: guessed '{guessed}', correct '{birthday_name}'")

        else:
            fail(f"unknown command: {line}")


if __name__ == "__main__":
    main()