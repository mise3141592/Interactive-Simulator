
import sys
def main():
    # 1. 인자 확인 및 비밀 시나리오 파일 읽기
    if len(sys.argv) < 2:
        print("에러: 비밀 시나리오 파일 경로가 지정되지 않았습니다.", file=sys.stderr)
        print("사용법: python interactor.py <scenario_file_path>", file=sys.stderr)
        sys.exit(1)
        
    secret_file_path = sys.argv[1]
    
    try:
        with open(secret_file_path, 'r') as f:
            # 파일의 첫 줄에서 정답(양의 정수)을 읽어옴
            secret_n = int(f.readline().strip())
            if secret_n <= 0:
                print(f"에러: 비밀 정수는 양의 정수여야 합니다. (입력값: {secret_n})", file=sys.stderr)
                sys.exit(1)
    except Exception as e:
        print(f"에러: 시나리오 파일을 읽는 중 오류가 발생했습니다: {e}", file=sys.stderr)
        sys.exit(1)

    # 2. 상수가 정의된 제한 조건
    MAX_QUERIES = 20
    query_count = 0

    # 3. 상호작용 루프 시작
    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                print("에러: 참가자 프로그램이 정답을 맞추지 못하고 종료되었거나 EOF를 보냈습니다.", file=sys.stderr)
                sys.exit(1)
            
            parts = line.strip().split()
            if not parts:
                continue  # 빈 줄은 건너뜁니다.
                
            cmd_type = parts[0]
            
            # [Case 1] 질문 인 경우: "? A"
            if cmd_type == '?':
                if query_count >= MAX_QUERIES:
                    print(f"오답 (Wrong Answer): 질문 횟수 제한({MAX_QUERIES}회)을 초과했습니다.", file=sys.stderr)
                    sys.exit(1)
                    
                if len(parts) != 2:
                    print("에러: 질문 형식이 올바르지 않습니다. '? A' 형식이어야 합니다.", file=sys.stderr)
                    sys.exit(1)
                    
                try:
                    A = int(parts[1])
                    if A <= 0:
                        raise ValueError
                except ValueError:
                    print("에러: 질문할 수(A)는 양의 정수여야 합니다.", file=sys.stderr)
                    sys.exit(1)
                
                # 질문 처리 및 응답 출력
                query_count += 1
                if secret_n % A == 0:
                    print(1, flush=True)
                else:
                    print(0, flush=True)
                    
            # [Case 2] 정답 제출인 경우: "! n"
            elif cmd_type == '!':
                if len(parts) != 2:
                    print("에러: 정답 제출 형식이 올바르지 않습니다. '! n' 형식이어야 합니다.", file=sys.stderr)
                    sys.exit(1)
                    
                try:
                    user_ans = int(parts[1])
                except ValueError:
                    print("에러: 제출한 정답은 정수여야 합니다.", file=sys.stderr)
                    sys.exit(1)
                    
                # 정답 판정
                if user_ans == secret_n:
                    # 성공적으로 정답을 맞춤 (질문 횟수 조건도 만족함)
                    sys.exit(0)
                else:
                    print(f"오답 (Wrong Answer): 정답은 {secret_n}이지만, 제출한 값은 {user_ans}입니다.", file=sys.stderr)
                    sys.exit(1)
                    
            # [Case 3] 그 외 잘못된 명령어인 경우
            else:
                print(f"에러: 정의되지 않은 명령어 접두사 '{cmd_type}' 입니다. ('?' 또는 '!'만 가능)", file=sys.stderr)
                sys.exit(1)
                
        except Exception as e:
            print(f"에러: 인터랙션 중 예기치 못한 오류가 발생했습니다: {e}", file=sys.stderr)
            sys.exit(1)

if __name__ == "__main__":
    main()