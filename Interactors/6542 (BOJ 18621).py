import sys


def main():
    if len(sys.argv) < 2:
        print("Usage: interactor_cloyster.py <scenario_file>", file=sys.stderr)
        sys.exit(1)

    scenario_path = sys.argv[1]
    with open(scenario_path, "r") as f:
        data = f.read().split()

    idx = 0
    n = int(data[idx]); idx += 1

    grid = [[0] * (n + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        for j in range(1, n + 1):
            grid[i][j] = int(data[idx]); idx += 1

    # 모든 값이 서로 다른지 확인 (문제 조건)
    flat = [grid[i][j] for i in range(1, n + 1) for j in range(1, n + 1)]
    if len(set(flat)) != len(flat):
        print("Invalid scenario: duplicate shell sizes", file=sys.stderr)
        sys.exit(1)

    # 리더(최댓값) 위치 계산
    leader_i, leader_j = 1, 1
    for i in range(1, n + 1):
        for j in range(1, n + 1):
            if grid[i][j] > grid[leader_i][leader_j]:
                leader_i, leader_j = i, j

    max_queries = 3 * n + 210

    # 학생 프로그램에게 n 전달
    print(n, flush=True)

    query_count = 0

    for raw_line in sys.stdin:
        parts = raw_line.split()
        if not parts:
            continue

        cmd = parts[0]

        if cmd == "?":
            if len(parts) != 3:
                print(f"Malformed query: {raw_line.strip()}", file=sys.stderr)
                sys.exit(1)
            try:
                i, j = int(parts[1]), int(parts[2])
            except ValueError:
                print(f"Malformed query: {raw_line.strip()}", file=sys.stderr)
                sys.exit(1)

            if not (1 <= i <= n and 1 <= j <= n):
                print(f"Query out of bounds: {i} {j} (n={n})", file=sys.stderr)
                sys.exit(1)

            query_count += 1
            if query_count > max_queries:
                print(
                    f"Query limit exceeded: used {query_count}, limit {max_queries}",
                    file=sys.stderr,
                )
                sys.exit(1)

            print(grid[i][j], flush=True)

        elif cmd == "!":
            if len(parts) != 3:
                print(f"Malformed answer: {raw_line.strip()}", file=sys.stderr)
                sys.exit(1)
            try:
                i, j = int(parts[1]), int(parts[2])
            except ValueError:
                print(f"Malformed answer: {raw_line.strip()}", file=sys.stderr)
                sys.exit(1)

            if i == leader_i and j == leader_j:
                sys.exit(0)
            else:
                given_val = grid[i][j] if (1 <= i <= n and 1 <= j <= n) else None
                print(
                    f"Wrong answer: answered ({i},{j})"
                    + (f" value={given_val}" if given_val is not None else " (out of bounds)")
                    + f", expected leader at ({leader_i},{leader_j}) value={grid[leader_i][leader_j]}"
                    + f"; queries used = {query_count}/{max_queries}",
                    file=sys.stderr,
                )
                sys.exit(1)

        else:
            print(f"Unknown command: {raw_line.strip()}", file=sys.stderr)
            sys.exit(1)

    # 답을 내지 않고 입력이 끝난 경우
    print("No answer ('!') was given before EOF", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()