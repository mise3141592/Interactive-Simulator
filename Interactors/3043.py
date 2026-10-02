import sys
import os

def main():
    if len(sys.argv) < 2:
        print("Error: Scenario file path not provided.", file=sys.stderr)
        sys.exit(1)
        
    scenario_path = sys.argv[1]
    if not os.path.exists(scenario_path):
        print(f"Error: Scenario file not found at {scenario_path}", file=sys.stderr)
        sys.exit(1)
        
    with open(scenario_path, 'r') as f:
        lines = [line.strip() for line in f if line.strip()]

    try:
        n, m = map(int, lines[0].split())
        cat_y, cat_x = map(int, lines[1].split())
        maze = []
        for i in range(2, 2 + n):
            maze.append(list(map(int, lines[i].split())))
    except Exception as e:
        print(f"Error parsing scenario file: {e}", file=sys.stderr)
        sys.exit(1)

    bot_y, bot_x = 0, 0
    battery_limit = 5000
    move_count = 0

    # 방향 데이터: (명령어, dy, dx, 현재 칸 벽 비트, 다음 칸 벽 비트)
    # 위(1), 아래(2), 왼쪽(4), 오른쪽(8)
    directions = [
        ('up', -1, 0, 1, 2),
        ('down', 1, 0, 2, 1),
        ('left', 0, -1, 4, 8),
        ('right', 0, 1, 8, 4)
    ]

    # 실제 벽을 만날 때까지의 거리를 반환하는 올바른 초음파 센서 함수
    def get_distances(cy, cx):
        res = []
        for cmd, dy, dx, curr_bit, next_bit in directions:
            dist = 0
            curr_y, curr_x = cy, cx
            while True:
                # 1. 현재 칸 자체의 해당 방향 벽이 막혀있으면 더 이상 못 감
                if maze[curr_y][curr_x] & curr_bit:
                    break
                
                ny, nx = curr_y + dy, curr_x + dx
                # 2. 격자 바깥으로 나가는 경우 경계면이 벽임
                if not (0 <= ny < n and 0 <= nx < m):
                    break
                
                # 3. 다음 칸의 반대쪽 벽이 막혀있는 경우도 못 감
                if maze[ny][nx] & next_bit:
                    break
                
                # 벽이 없으므로 한 칸 전진 가능
                dist += 1
                curr_y, curr_x = ny, nx
                
            res.append(str(dist))
        return " ".join(res)

    print(f"{n} {m}", flush=True)

    while True:
        if bot_y == cat_y and bot_x == cat_x:
            print("Success", flush=True)
            sys.exit(0)

        if move_count >= battery_limit:
            print("No battery", flush=True)
            print("Wrong Answer: Battery limit exceeded (5000 moves).", file=sys.stderr)
            sys.exit(1)

        sensor_info = get_distances(bot_y, bot_x)
        print(sensor_info, flush=True)

        try:
            command = sys.stdin.readline().strip()
        except Exception:
            print("Wrong Answer: Failed to read command.", file=sys.stderr)
            sys.exit(1)

        if not command:
            print("Wrong Answer: Empty command received.", file=sys.stderr)
            sys.exit(1)

        # 학생의 이동 명령에 따른 벽 충돌 여부 정밀 검증
        valid_move = False
        for cmd, dy, dx, curr_bit, next_bit in directions:
            if command == cmd:
                # 현재 칸 벽 체크
                if maze[bot_y][bot_x] & curr_bit:
                    print(f"Wrong Answer: Crashed into the {cmd.upper()} wall (Current cell blocked).", file=sys.stderr)
                    sys.exit(1)
                
                ny, nx = bot_y + dy, bot_x + dx
                # 맵 이탈 체크
                if not (0 <= ny < n and 0 <= nx < m):
                    print(f"Wrong Answer: Crashed into the {cmd.upper()} wall (Out of bounds).", file=sys.stderr)
                    sys.exit(1)
                
                # 다음 칸 벽 체크
                if maze[ny][nx] & next_bit:
                    print(f"Wrong Answer: Crashed into the {cmd.upper()} wall (Next cell blocked).", file=sys.stderr)
                    sys.exit(1)
                
                # 모두 통과하면 이동
                bot_y, bot_x = ny, nx
                move_count += 1
                valid_move = True
                break
        
        if not valid_move:
            print(f"Wrong Answer: Invalid command '{command}'.", file=sys.stderr)
            sys.exit(1)

if __name__ == "__main__":
    main()