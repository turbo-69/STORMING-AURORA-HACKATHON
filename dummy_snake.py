# Simple dummy/starter opponent snake for local practice
import random
from flask import Flask, request
import logging

app = Flask("DummySnake")

@app.get("/")
def on_info():
    return {
        "apiversion": "1",
        "author": "DummyBot",
        "color": "#E74C3C",  # Red
        "head": "evil",
        "tail": "curled"
    }

@app.post("/start")
def on_start():
    return "ok"

@app.post("/move")
def on_move():
    game_state = request.get_json()
    my_head = game_state["you"]["body"][0]
    board_width = game_state["board"]["width"]
    board_height = game_state["board"]["height"]
    my_body = game_state["you"]["body"]

    # Basic boundary & body check only (dumb random snake)
    is_safe = {"up": True, "down": True, "left": True, "right": True}
    if my_head["x"] == 0: is_safe["left"] = False
    if my_head["x"] == board_width - 1: is_safe["right"] = False
    if my_head["y"] == 0: is_safe["down"] = False
    if my_head["y"] == board_height - 1: is_safe["up"] = False

    future = {
        "up": {"x": my_head["x"], "y": my_head["y"] + 1},
        "down": {"x": my_head["x"], "y": my_head["y"] - 1},
        "left": {"x": my_head["x"] - 1, "y": my_head["y"]},
        "right": {"x": my_head["x"] + 1, "y": my_head["y"]}
    }
    for move, coord in future.items():
        if coord in my_body:
            is_safe[move] = False

    safe_moves = [m for m, safe in is_safe.items() if safe]
    next_move = random.choice(safe_moves) if safe_moves else "down"
    return {"move": next_move}

@app.post("/end")
def on_end():
    return "ok"

if __name__ == "__main__":
    logging.getLogger("werkzeug").setLevel(logging.ERROR)
    print("Dummy Opponent Snake running on http://localhost:8001")
    app.run(host="0.0.0.0", port=8001)
