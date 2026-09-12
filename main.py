# Welcome to
# __________         __    __  .__                               __
# \______   \_____ _/  |__/  |_|  |   ____   ______ ____ _____  |  | __ ____
#  |    |  _/\__  \\   __\   __\  | _/ __ \ /  ___//    \\__  \ |  |/ // __ \
#  |    |   \ / __ \|  |  |  | |  |_\  ___/ \___ \|   |  \/ __ \|    <\  ___/
#  |________/(______/__|  |__| |____/\_____>______>___|__(______/__|__\\_____>
#
# This file can be a nice home for your Battlesnake logic and helper functions.
#
# To get you started we've included code to prevent your Battlesnake from moving backwards.
# For more info see docs.battlesnake.com

import random
import typing


# info is called when you create your Battlesnake on play.battlesnake.com
# and controls your Battlesnake's appearance
# TIP: If you open your Battlesnake URL in a browser you should see this data
def info() -> typing.Dict:
    print("INFO")

    return {
        "apiversion": "1",
        "author": "",  # TODO: Your Battlesnake Username
        "color": "#888888",  # TODO: Choose color
        "head": "default",  # TODO: Choose head
        "tail": "default",  # TODO: Choose tail
    }


# start is called when your Battlesnake begins a game
def start(game_state: typing.Dict):
    print("GAME START")


# end is called when your Battlesnake finishes a game
def end(game_state: typing.Dict):
    print("GAME OVER\n")


# move is called on every turn and returns your next move
# Valid moves are "up", "down", "left", or "right"
# See https://docs.battlesnake.com/api/example-move for available data
def move(game_state: typing.Dict) -> typing.Dict:

    is_move_safe = {"up": True, "down": True, "left": True, "right": True}

    # We've included code to prevent your Battlesnake from moving backwards
    my_head = game_state["you"]["body"][0]  # Coordinates of your head
    my_neck = game_state["you"]["body"][1]  # Coordinates of your "neck"

    if my_neck["x"] < my_head["x"]:  # Neck is left of head, don't move left
        is_move_safe["left"] = False

    elif my_neck["x"] > my_head["x"]:  # Neck is right of head, don't move right
        is_move_safe["right"] = False

    elif my_neck["y"] < my_head["y"]:  # Neck is below head, don't move down
        is_move_safe["down"] = False

    elif my_neck["y"] > my_head["y"]:  # Neck is above head, don't move up
        is_move_safe["up"] = False

    # ---------------------------------------------------------
    # PHASE 1: STRICT SAFETY FILTER (Walls, Neck, Bodies)
    # Safety must ALWAYS come first!
    # ---------------------------------------------------------
    board_width = game_state["board"]["width"]
    board_height = game_state["board"]["height"]
    my_body = game_state["you"]["body"]
    my_length = len(my_body)

    # Calculate the future coordinate for all 4 moves
    future_head_positions = {
        "up": {"x": my_head["x"], "y": my_head["y"] + 1},
        "down": {"x": my_head["x"], "y": my_head["y"] - 1},
        "left": {"x": my_head["x"] - 1, "y": my_head["y"]},
        "right": {"x": my_head["x"] + 1, "y": my_head["y"]},
    }

    # 1. Prevent moving out of bounds (off the board edge)
    if my_head["x"] == 0:
        is_move_safe["left"] = False
    if my_head["x"] == board_width - 1:
        is_move_safe["right"] = False
    if my_head["y"] == 0:
        is_move_safe["down"] = False
    if my_head["y"] == board_height - 1:
        is_move_safe["up"] = False

    # 2. Prevent colliding with our own body
    for direction, future_coord in future_head_positions.items():
        if future_coord in my_body:
            is_move_safe[direction] = False

    # 3. Prevent colliding with opponent snake bodies
    opponents = game_state["board"]["snakes"]
    for opponent in opponents:
        for direction, future_coord in future_head_positions.items():
            if future_coord in opponent["body"]:
                is_move_safe[direction] = False

    # Build a fast lookup set of all obstacle coordinates (our body + opponents)
    all_obstacles = set()
    for segment in my_body:
        all_obstacles.add((segment["x"], segment["y"]))
    for opponent in opponents:
        for segment in opponent["body"]:
            all_obstacles.add((segment["x"], segment["y"]))

    # Full board reachable space counter (no artificial 30-tile cap!)
    def count_reachable_space(start_coord, max_limit=None):
        if max_limit is None:
            max_limit = board_width * board_height

        visited = set()
        queue = [(start_coord["x"], start_coord["y"])]
        visited.add((start_coord["x"], start_coord["y"]))

        while queue and len(visited) < max_limit:
            cx, cy = queue.pop(0)
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                nx, ny = cx + dx, cy + dy
                if 0 <= nx < board_width and 0 <= ny < board_height:
                    if (nx, ny) not in all_obstacles and (nx, ny) not in visited:
                        visited.add((nx, ny))
                        queue.append((nx, ny))
        return len(visited)

    # Collect only the moves that are 100% physically safe this turn
    safe_moves = [direction for direction, is_safe in is_move_safe.items() if is_safe]

    # ---------------------------------------------------------
    # EMERGENCY FALLBACK: If completely boxed in (safe_moves is empty)
    # Never blindly crash into a wall or neck! Pick whichever direction
    # has the most open space or chases our vacating tail!
    # ---------------------------------------------------------
    if len(safe_moves) == 0:
        in_bounds_moves = []
        for direction, coord in future_head_positions.items():
            if 0 <= coord["x"] < board_width and 0 <= coord["y"] < board_height:
                if coord != my_neck:
                    in_bounds_moves.append(direction)

        if not in_bounds_moves:
            in_bounds_moves = list(future_head_positions.keys())

        my_tail = my_body[-1]

        def calculate_escape_score(direction):
            coord = future_head_positions[direction]
            score = 0
            if coord == my_tail:
                score += 50
            score += count_reachable_space(coord, max_limit=15)
            return score

        best_escape_move = max(in_bounds_moves, key=calculate_escape_score)
        print(f"MOVE {game_state['turn']}: TRAPPED! No safe moves. Picked highest open-space escape: {best_escape_move} (Score: {calculate_escape_score(best_escape_move)})")
        return {"move": best_escape_move}

    # ---------------------------------------------------------
    # PHASE 2: REAL FLOOD-FILL & TRAP AVOIDANCE
    # Never walk into a pocket smaller than our snake's body!
    # ---------------------------------------------------------
    # Count the TRUE total reachable area for every safe move
    space_by_move = {m: count_reachable_space(future_head_positions[m]) for m in safe_moves}
    max_available_space = max(space_by_move.values())

    # A move is genuinely safe from being a trap if:
    # 1. It has enough room to comfortably fit our entire body (>= my_length), OR
    # 2. It has at least 70% of the maximum available space on the entire board
    spacious_safe_moves = [
        m for m in safe_moves
        if space_by_move[m] >= my_length or space_by_move[m] >= (max_available_space * 0.70)
    ]

    # Priority rule: If moves with large open space exist, STRICTLY ELIMINATE moves
    # that lead into small shrinking pockets, even if food is in that pocket!
    candidate_moves = spacious_safe_moves if spacious_safe_moves else [max(safe_moves, key=lambda m: space_by_move[m])]

    # ---------------------------------------------------------
    # PHASE 3: FOOD SEEKING (Only among verified safe, non-trap moves)
    # ---------------------------------------------------------
    my_health = game_state["you"]["health"]
    food_list = game_state["board"]["food"]

    if food_list:
        def get_distance(a, b):
            return abs(a["x"] - b["x"]) + abs(a["y"] - b["y"])

        # Find the closest food item to our head
        nearest_food = min(food_list, key=lambda f: get_distance(my_head, f))

        # Calculate distance to food for each candidate move
        min_dist_to_food = min(
            get_distance(future_head_positions[m], nearest_food) for m in candidate_moves
        )

        # Filter candidate moves to only those that minimize distance to nearest food
        best_food_moves = [
            m for m in candidate_moves
            if get_distance(future_head_positions[m], nearest_food) == min_dist_to_food
        ]

        next_move = random.choice(best_food_moves)
        print(f"MOVE {game_state['turn']}: Safe food path to ({nearest_food['x']}, {nearest_food['y']}) with {next_move} (Health: {my_health}, Room: {space_by_move[next_move]})")
        return {"move": next_move}

    # If no food, pick the candidate move with the most open space
    next_move = max(candidate_moves, key=lambda m: space_by_move[m])
    print(f"MOVE {game_state['turn']}: Wandering safely into open space with {next_move}")
    return {"move": next_move}


# Start server when `python main.py` is run
if __name__ == "__main__":
    from server import run_server

    run_server({"info": info, "start": start, "move": move, "end": end})
