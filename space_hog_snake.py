# Space-maximizer (territory hog) reference opponent Battlesnake for local benchmarking
import os
import random
import logging
from collections import deque
from flask import Flask, request

app = Flask("SpaceHogSnake")

@app.get("/")
def on_info():
    return {
        "apiversion": "1",
        "author": "SpaceHogBot",
        "color": "#9B59B6",  # Distinct deep purple
        "head": "fang",
        "tail": "block-bum"
    }

@app.post("/start")
def on_start():
    return "ok"

@app.post("/move")
def on_move():
    game_state = request.get_json()
    you = game_state.get("you", {})
    my_body = you.get("body", [])
    if not my_body:
        return {"move": "down"}

    my_head = my_body[0]
    my_neck = my_body[1] if len(my_body) > 1 else my_head
    my_health = you.get("health", 100)

    board = game_state.get("board", {})
    board_width = board.get("width", 11)
    board_height = board.get("height", 11)
    opponents = board.get("snakes", [])
    food_list = board.get("food", [])

    is_safe = {"up": True, "down": True, "left": True, "right": True}

    # 1. Prevent moving backward into own neck
    if my_neck["x"] < my_head["x"]:
        is_safe["left"] = False
    elif my_neck["x"] > my_head["x"]:
        is_safe["right"] = False
    elif my_neck["y"] < my_head["y"]:
        is_safe["down"] = False
    elif my_neck["y"] > my_head["y"]:
        is_safe["up"] = False

    future_coords = {
        "up": {"x": my_head["x"], "y": my_head["y"] + 1},
        "down": {"x": my_head["x"], "y": my_head["y"] - 1},
        "left": {"x": my_head["x"] - 1, "y": my_head["y"]},
        "right": {"x": my_head["x"] + 1, "y": my_head["y"]}
    }

    # 2. Prevent moving off board boundaries
    if my_head["x"] == 0:
        is_safe["left"] = False
    if my_head["x"] == board_width - 1:
        is_safe["right"] = False
    if my_head["y"] == 0:
        is_safe["down"] = False
    if my_head["y"] == board_height - 1:
        is_safe["up"] = False

    # Collect obstacles: own body + all opponent bodies
    all_obstacles = set()
    for seg in my_body:
        all_obstacles.add((seg["x"], seg["y"]))

    my_id = you.get("id")
    for opp in opponents:
        if opp.get("id") == my_id:
            continue
        for seg in opp.get("body", []):
            all_obstacles.add((seg["x"], seg["y"]))

    # 3 & 4. Prevent colliding with own or opponent bodies
    for move, coord in future_coords.items():
        if (coord["x"], coord["y"]) in all_obstacles:
            is_safe[move] = False

    safe_moves = [m for m, safe in is_safe.items() if safe]

    # Emergency fallback if boxed in
    if not safe_moves:
        in_bounds = [
            m for m, coord in future_coords.items()
            if 0 <= coord["x"] < board_width and 0 <= coord["y"] < board_height and coord != my_neck
        ]
        return {"move": in_bounds[0] if in_bounds else "down"}

    # Starvation override: if health < 30, prioritize nearest food by Manhattan distance
    if my_health < 30 and food_list:
        def food_distance_key(m):
            coord = future_coords[m]
            return min(abs(coord["x"] - f["x"]) + abs(coord["y"] - f["y"]) for f in food_list)

        best_move = min(safe_moves, key=food_distance_key)
        return {"move": best_move}

    # Territory Maximization: BFS flood-fill reachable space from each candidate move
    def count_open_space(start_coord):
        start_t = (start_coord["x"], start_coord["y"])
        visited = {start_t}
        queue = deque([start_t])
        max_limit = board_width * board_height

        while queue and len(visited) < max_limit:
            cx, cy = queue.popleft()
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                nx, ny = cx + dx, cy + dy
                if 0 <= nx < board_width and 0 <= ny < board_height:
                    coord = (nx, ny)
                    if coord not in all_obstacles and coord not in visited:
                        visited.add(coord)
                        queue.append(coord)
        return len(visited)

    best_move = max(safe_moves, key=lambda m: count_open_space(future_coords[m]))
    return {"move": best_move}

@app.post("/end")
def on_end():
    return "ok"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8003"))
    logging.getLogger("werkzeug").setLevel(logging.ERROR)
    print(f"Space Hog Opponent Snake running on http://127.0.0.1:{port}")
    app.run(host="0.0.0.0", port=port, threaded=True)
