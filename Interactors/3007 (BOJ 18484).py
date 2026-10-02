import sys

def main():
    # 1. 인자값 및 비밀 시나리오 파일 확인
    if len(sys.argv) < 2:
        print("에러: 비밀 시나리오 파일 경로가 지정되지 않았습니다.", file=sys.stderr)
        print("사용법: python interactor.py <scenario_file_path>", file=sys.stderr)
        sys.exit(1)

    scenario_path = sys.argv[1]

    try:
        with open(scenario_path, 'r') as f:
            lines = f.read().splitlines()
    except Exception as e:
        print(f"에러: 시나리오 파일을 읽을 수 없습니다. ({e})", file=sys.stderr)
        sys.exit(1)

    # 데이터 파싱
    if len(lines) < 2:
        print("에러: 시나리오 파일의 형식이 올바르지 않습니다. (최소 2줄 필요)", file=sys.stderr)
        sys.exit(1)

    try:
        n, k = map(int, lines[0].split())
        secret_array = list(map(int, lines[1].split()))
    except ValueError:
        print("에러: 시나리오 파일의 숫자가 올바른 정수 형식이 아닙니다.", file=sys.stderr)
        sys.exit(1)

    if len(secret_array) != n:
        print(f"에러: 설정된 n({n})과 실제 정답 배열의 개수({len(secret_array)})가 일치하지 않습니다.", file=sys.stderr)
        sys.exit(1)

    # 2. 나의 프로그램으로 최초 n, k 송신
    print(f"{n} {k}", flush=True)

    current_idx = 0
    query_count = 0
    max_queries = 2600

    # 3. 인터랙션 루프 개시
    while current_idx < n:
        # 나의 프로그램으로부터 질문(x) 입력받기
        line = sys.stdin.readline()
        
        # EOF (프로그램이 중간에 꺼진 경우)
        if not line:
            print("오답 (Wrong Answer): 나의 프로그램이 정답을 다 찾기 전에 종료되었습니다.", file=sys.stderr)
            sys.exit(1)

        query_count += 1
        
        # 질문 횟수 제한(2600회) 초과 여부 검증
        if query_count > max_queries:
            print(f"오답 (Wrong Answer): 질문 횟수 제한을 초과했습니다. ({query_count}회)", file=sys.stderr)
            sys.exit(1)

        # 입력 데이터 정수 변환 및 유효성 검증
        try:
            x = int(line.strip())
        except ValueError:
            print(f"오답 (Wrong Answer): 올바른 정수가 아닌 값 입력: '{line.strip()}'", file=sys.stderr)
            sys.exit(1)

        if not (1 <= x <= k):
            print(f"오답 (Wrong Answer): 질문 범위 초과 (1 <= x <= {k} 범위를 벗어난 {x} 입력)", file=sys.stderr)
            sys.exit(1)

        # 비밀 숫자와 비교 후 응답
        target = secret_array[current_idx]
        if target > x:
            print(">", flush=True)
        elif target < x:
            print("<", flush=True)
        else:
            print("=", flush=True)
            current_idx += 1  # 정답을 맞췄으므로 다음 숫자로 이동

    # 4. 최종 정답 검증 성공
    sys.exit(0)

if __name__ == '__main__':
    main()