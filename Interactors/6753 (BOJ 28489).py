#!/usr/bin/env python3
"""
2048 인터랙티브 문제 인터랙터

사용법: python3 interactor.py <비밀_시나리오_파일_경로>
  - stdin  : 학생 프로그램이 출력한 이동 방향(UP/DOWN/LEFT/RIGHT)
  - stdout : 인터랙터가 학생에게 보내는 응답 (2가 생성될 칸 번호, 종료 시 -1)
  - 정답(최종 최댓값 블록 >= 2048) -> exit(0)
  - 오답 -> stderr 에 사유 출력 후 exit(1)

비밀 시나리오 파일 형식
------------------------
공백/개행으로 구분된 음이 아닌 정수들의 나열.
각 "2가 적힌 블록 생성" 이벤트가 발생할 때마다 시퀀스에서 정수를 하나씩
순서대로 꺼내 (그 시점의 "빈 칸 개수")로 나눈 나머지를 사용해,
현재 빈 칸들을 칸 번호 오름차순으로 나열했을 때 몇 번째 칸을 선택할지 결정한다.

즉 실제 값 자체는 중요하지 않고 "나머지 연산으로 방향을 결정하는 난수 시퀀스"
역할만 하므로, 그냥 충분히 긴 난수열을 저장해두면 된다.
(값의 크기 제한 없음. 정수이기만 하면 됨.)

한 게임에서 필요한 정수 개수는 "성공적으로 처리된 이동 횟수 + 1(시작 스폰)"이다.
정확한 상한을 알 수 없으므로 여유 있게 (예: 5000개 이상) 준비해 두는 것을 권장한다.
시퀀스를 다 소모하면 인터랙터는 오류로 간주하고 강제로 오답 처리한다
(출제 시 시퀀스 길이를 넉넉히 잡아 이런 상황이 발생하지 않도록 해야 한다).

각 테스트케이스(총 16개)마다:
  - 입력 칸: 위 형식의 난수 시퀀스 (테스트케이스마다 다른 시드로 생성해 서로 다른 게임이 되게 한다)
  - 출력 칸: 비워둠 (인터랙티브 문제이므로 정해진 출력이 없음)
"""

import sys


def read_secret(path):
    with open(path) as f:
        data = f.read().split()
    return [int(x) for x in data]


def main():
    if len(sys.argv) < 2:
        print("usage: interactor.py <secret_file>", file=sys.stderr)
        sys.exit(1)

    secret = read_secret(sys.argv[1])
    sidx = 0

    def next_choice(n):
        nonlocal sidx
        if sidx >= len(secret):
            print("secret sequence exhausted", file=sys.stderr)
            sys.exit(1)
        v = secret[sidx] % n
        sidx += 1
        return v

    # board[0..15] : 1행1열 ~ 4행4열 (row-major), 0 = 빈 칸
    board = [0] * 16

    def empty_cells():
        return [i for i in range(16) if board[i] == 0]

    def spawn():
        """새 블록(2)을 생성. 성공하면 True, 더 이상 빈 칸이 없으면 -1을 출력하고 False."""
        cells = empty_cells()
        if not cells:
            print(-1, flush=True)
            return False
        idx = next_choice(len(cells))
        pos = cells[idx]
        board[pos] = 2
        print(pos + 1, flush=True)  # 1-indexed 좌표로 출력
        return True

    def compress_merge(line):
        """길이 4 리스트를 index 0 쪽으로 밀며, 같은 값은 한 번만 합쳐서 반환."""
        vals = [v for v in line if v != 0]
        merged = []
        i = 0
        while i < len(vals):
            if i + 1 < len(vals) and vals[i] == vals[i + 1]:
                merged.append(vals[i] * 2)
                i += 2
            else:
                merged.append(vals[i])
                i += 1
        merged += [0] * (4 - len(merged))
        return merged

    def get_line(direction, i):
        if direction in ("LEFT", "RIGHT"):
            row = board[i * 4: i * 4 + 4]
            if direction == "RIGHT":
                row = row[::-1]
            return row
        else:
            col = [board[i + 4 * k] for k in range(4)]
            if direction == "DOWN":
                col = col[::-1]
            return col

    def set_line(direction, i, line):
        if direction in ("LEFT", "RIGHT"):
            if direction == "RIGHT":
                line = line[::-1]
            board[i * 4: i * 4 + 4] = line
        else:
            if direction == "DOWN":
                line = line[::-1]
            for k in range(4):
                board[i + 4 * k] = line[k]

    def apply_move(direction):
        changed = False
        for i in range(4):
            line = get_line(direction, i)
            new_line = compress_merge(line)
            if new_line != line:
                changed = True
            set_line(direction, i, new_line)
        return changed

    # 게임 시작: 블록 1개 생성
    if not spawn():
        # 빈 보드에서 스폰이 실패할 일은 없음
        print("initial spawn failed unexpectedly", file=sys.stderr)
        sys.exit(1)

    while True:
        raw = sys.stdin.readline()
        if not raw:
            print("unexpected EOF from solution", file=sys.stderr)
            sys.exit(1)
        move = raw.strip()

        if move not in ("UP", "DOWN", "LEFT", "RIGHT"):
            print(-1, flush=True)
            break

        changed = apply_move(move)
        if not changed:
            print(-1, flush=True)
            break

        if not spawn():
            break  # 보드가 가득 차서 spawn 내부에서 -1을 이미 출력함

    score = max(board)
    if score <= 8:
        score = 0

    if score >= 2048:
        sys.exit(0)
    else:
        print(f"failed: max tile = {score}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()