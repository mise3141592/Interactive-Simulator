import sys

def main():
    # 1. 비밀 시나리오 파일 경로 확인
    if len(sys.argv) < 2:
        print("시스템 오류: 비밀 시나리오 파일 경로가 제공되지 않았습니다.", file=sys.stderr)
        sys.exit(1)

    secret_file = sys.argv[1]

    # 2. 비밀 시나리오 읽기
    try:
        with open(secret_file, 'r') as f:
            lines = f.read().split()
            if len(lines) < 2:
                print("시스템 오류: 시나리오 파일 형식이 올바르지 않습니다.", file=sys.stderr)
                sys.exit(1)
            
            period = int(lines[0])
            pattern_chars = lines[1]
    except Exception as e:
        print(f"시스템 오류: 시나리오 파일을 읽는 중 문제 발생 ({e})", file=sys.stderr)
        sys.exit(1)

    total_rounds = 2500
    min_required_correct = 2450
    correct_guesses = 0

    # 3. 2500번의 하키 퍽 방어 시작
    for i in range(total_rounds):
        # 이번 턴에 Glungus가 날릴 방향 계산
        actual_char = pattern_chars[i % period]
        actual_move = "Up" if actual_char == 'U' else "Down"

        # 학생(Nexus)의 예측 읽기
        try:
            guess = sys.stdin.readline().strip()
            
            if not guess:
                print(f"오답 [Turn {i+1}]: 학생 프로그램의 출력이 끊겼습니다.", file=sys.stderr)
                sys.exit(1)
            
            if guess not in ("Up", "Down"):
                print(f"오답 [Turn {i+1}]: 잘못된 출력 포맷입니다. ('Up' 또는 'Down'만 가능) 입력값: {guess}", file=sys.stderr)
                sys.exit(1)

        except EOFError:
            print(f"오답 [Turn {i+1}]: 예상치 못한 EOF 발생.", file=sys.stderr)
            sys.exit(1)

        # 정답 여부 기록
        if guess == actual_move:
            correct_guesses += 1

        # Glungus의 실제 공격 방향을 학생에게 전달 (매우 중요: 버퍼 비우기)
        print(actual_move, flush=True)

    # 4. 최종 결과 판정
    if correct_guesses >= min_required_correct:
        print(f"정답! Nexus가 완벽하게 방어했습니다. (정답 횟수: {correct_guesses}/{total_rounds})", file=sys.stderr)
        sys.exit(0)
    else:
        print(f"오답: 방어 실패. (정답 횟수: {correct_guesses}/{total_rounds}, 통과 기준: {min_required_correct})", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()