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
        my_tail = my_body[-1]
        my_tail_coord = (my_tail["x"], my_tail["y"])

        # BUGFIX (Bug #4): only consider moves that are in-bounds, not our own
        # neck, AND not a guaranteed-fatal collision (any snake's body) --
        # except our own tail cell, which is handled specially below since it
        # actually vacates this turn (unless we just ate).
        in_bounds_moves = []
        for direction, coord in future_head_positions.items():
            if 0 <= coord["x"] < board_width and 0 <= coord["y"] < board_height:
                if coord != my_neck:
                    coord_tuple = (coord["x"], coord["y"])
                    if coord_tuple not in all_obstacles or coord_tuple == my_tail_coord:
                        in_bounds_moves.append(direction)

        if not in_bounds_moves:
            # No non-fatal option exists at all -- true last resort, fall back
            # to the original bounds+neck-only filter (may still be fatal).
            in_bounds_moves = []
            for direction, coord in future_head_positions.items():
                if 0 <= coord["x"] < board_width and 0 <= coord["y"] < board_height:
                    if coord != my_neck:
                        in_bounds_moves.append(direction)

        if not in_bounds_moves:
            in_bounds_moves = list(future_head_positions.keys())

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
    # PHASE 3: HEAD-TO-HEAD COLLISION AVOIDANCE
    # If an opponent is equal or longer than us, avoid tiles they can move into!
    # If an opponent is strictly shorter than us, it's safe/good to contest that tile.
    # ---------------------------------------------------------
    dangerous_head_zones = set()
    my_id = game_state["you"].get("id")

    for opponent in opponents:
        if opponent.get("id") == my_id:
            continue

        opp_body = opponent["body"]
        opp_length = len(opp_body)
        opp_head = opp_body[0]

        # If opponent is equal or longer than us, a head-on collision kills or ties us
        if opp_length >= my_length:
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                dangerous_head_zones.add((opp_head["x"] + dx, opp_head["y"] + dy))

    # Filter out moves that step into a larger/equal snake's strike zone
    h2h_safe_moves = [
        m for m in candidate_moves
        if (future_head_positions[m]["x"], future_head_positions[m]["y"]) not in dangerous_head_zones
    ]

    # If we have moves that avoid head-on danger, strictly use those!
    # (If all moves are threatened, fall back to candidate_moves and hope opponent turns away)
    post_h2h_moves = h2h_safe_moves if h2h_safe_moves else candidate_moves

    # ---------------------------------------------------------
    # PHASE 4 & 5: HAZARD AVOIDANCE & INTELLIGENT FOOD SEEKING
    # Food seeking happens normally when safely outside hazard zones.
    # Hazard avoidance is only prioritized when actually near or in a hazard.
    # ---------------------------------------------------------
    hazards = game_state.get("board", {}).get("hazards", [])
    hazard_coords = {(h["x"], h["y"]) for h in hazards}
    center_coord = {"x": board_width // 2, "y": board_height // 2}

    def get_coord_distance(a, b):
        return abs(a["x"] - b["x"]) + abs(a["y"] - b["y"])

    my_health = game_state["you"]["health"]
    food_list = game_state["board"]["food"]
    all_food_coords = {(f["x"], f["y"]) for f in food_list}
    safe_food_coords = {(f["x"], f["y"]) for f in food_list if (f["x"], f["y"]) not in hazard_coords}

    # Proximity checks to storm / hazard tiles
    head_pos = (my_head["x"], my_head["y"])
    is_in_hazard = head_pos in hazard_coords
    is_near_hazard = any(
        (head_pos[0] + dx, head_pos[1] + dy) in hazard_coords
        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]
    )
    is_safely_outside = (not is_in_hazard) and (not is_near_hazard)

    # Classify safe moves by hazard status
    non_hazard_moves = [
        m for m in post_h2h_moves
        if (future_head_positions[m]["x"], future_head_positions[m]["y"]) not in hazard_coords
    ]
    hazard_moves = [
        m for m in post_h2h_moves
        if (future_head_positions[m]["x"], future_head_positions[m]["y"]) in hazard_coords
    ]

    # BFS Walkable Path Distance to Food (navigating around bodies/obstacles)
    def find_food_distance_bfs(start_coord, target_food_coords):
        if not target_food_coords:
            return float("inf")
        start = (start_coord["x"], start_coord["y"])
        if start in target_food_coords:
            return 0
        visited = {start}
        queue = [(start[0], start[1], 0)]
        while queue:
            cx, cy, dist = queue.pop(0)
            if dist >= 30:
                break
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                nx, ny = cx + dx, cy + dy
                if 0 <= nx < board_width and 0 <= ny < board_height:
                    if (nx, ny) not in all_obstacles and (nx, ny) not in visited:
                        if (nx, ny) in target_food_coords:
                            return dist + 1
                        visited.add((nx, ny))
                        queue.append((nx, ny, dist + 1))
        return float("inf")

    # BUGFIX (Bug #5): BFS walkable distance from `start_coord` to the nearest
    # non-hazard cell, navigating around obstacles. This replaces straight-line
    # (Manhattan) distance-to-board-center, which ignores walls/bodies that can
    # block the direct path and silently cost extra hazard-damage turns while
    # "closing the distance" to a center that isn't actually reachable that way.
    def find_hazard_escape_distance_bfs(start_coord):
        start = (start_coord["x"], start_coord["y"])
        if start not in hazard_coords:
            return 0
        visited = {start}
        queue = [(start[0], start[1], 0)]
        while queue:
            cx, cy, dist = queue.pop(0)
            if dist >= 30:
                break
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                nx, ny = cx + dx, cy + dy
                if 0 <= nx < board_width and 0 <= ny < board_height:
                    if (nx, ny) not in all_obstacles and (nx, ny) not in visited:
                        if (nx, ny) not in hazard_coords:
                            return dist + 1
                        visited.add((nx, ny))
                        queue.append((nx, ny, dist + 1))
        return float("inf")

    # Helper to choose best move towards food among candidate moves
    def pick_food_move(moves_to_choose_from, preferred_foods):
        # 1. First see if any move immediately eats food this turn
        immediate_food_moves = [
            m for m in moves_to_choose_from
            if (future_head_positions[m]["x"], future_head_positions[m]["y"]) in preferred_foods
        ]
        if immediate_food_moves:
            return max(immediate_food_moves, key=lambda m: space_by_move[m])

        # 2. Check BFS walkable distance to nearest preferred food
        food_distances = {
            m: find_food_distance_bfs(future_head_positions[m], preferred_foods)
            for m in moves_to_choose_from
        }
        min_bfs_dist = min(food_distances.values())

        if min_bfs_dist < float("inf"):
            best_moves = [m for m in moves_to_choose_from if food_distances[m] == min_bfs_dist]
            return max(best_moves, key=lambda m: space_by_move[m])

        # 3. If BFS can't find food within search radius, fall back to Manhattan distance
        if preferred_foods:
            closest_food = min(
                preferred_foods,
                key=lambda f: min(get_coord_distance(future_head_positions[m], {"x": f[0], "y": f[1]}) for m in moves_to_choose_from)
            )
            min_manhattan = min(
                get_coord_distance(future_head_positions[m], {"x": closest_food[0], "y": closest_food[1]})
                for m in moves_to_choose_from
            )
            best_moves = [
                m for m in moves_to_choose_from
                if get_coord_distance(future_head_positions[m], {"x": closest_food[0], "y": closest_food[1]}) == min_manhattan
            ]
            return max(best_moves, key=lambda m: space_by_move[m])

        # 4. Fall back to largest open space
        return max(moves_to_choose_from, key=lambda m: space_by_move[m])

    # ---------------------------------------------------------
    # CASE 1: INSIDE HAZARD (Actively taking storm damage)
    # Primary goal: Escape to safety! But an immediate food restores 100 health.
    # ---------------------------------------------------------
    if is_in_hazard:
        # Life-saver check: Eating food resets health to 100 and buys survival time
        immediate_food = [
            m for m in post_h2h_moves
            if (future_head_positions[m]["x"], future_head_positions[m]["y"]) in all_food_coords
        ]
        if immediate_food and my_health < 50:
            best_move = max(immediate_food, key=lambda m: space_by_move[m])
            print(f"MOVE {game_state['turn']}: IN STORM (Health: {my_health}) - Life-saving food eaten with {best_move}!")
            return {"move": best_move}

        # Priority: Escape storm into non-hazard safe zone
        if non_hazard_moves:
            # If safe food is reachable from an escape move, steer towards it
            if safe_food_coords:
                best_move = pick_food_move(non_hazard_moves, safe_food_coords)
            else:
                # Steer toward center of safe zone
                best_move = min(
                    non_hazard_moves,
                    key=lambda m: get_coord_distance(future_head_positions[m], center_coord)
                )
            print(f"MOVE {game_state['turn']}: IN STORM (Health: {my_health}) - Escaping to safe zone with {best_move}")
            return {"move": best_move}
        else:
            # BUGFIX (Bug #5): all moves still in hazard. Previously this steered
            # by straight-line (Manhattan) distance to the board center, which
            # ignores obstacles blocking the direct path and can cost extra
            # hazard-damage turns while "making progress" toward a center that
            # isn't actually reachable that way. Use real BFS walkable distance
            # to the nearest non-hazard cell instead.
            escape_distances = {
                m: find_hazard_escape_distance_bfs(future_head_positions[m])
                for m in post_h2h_moves
            }
            min_escape_dist = min(escape_distances.values())
            if min_escape_dist < float("inf"):
                best_candidates = [m for m in post_h2h_moves if escape_distances[m] == min_escape_dist]
                best_move = max(best_candidates, key=lambda m: space_by_move.get(m, 0))
            else:
                # BFS couldn't find a way out within its search radius (30 tiles) --
                # fall back to straight-line distance to center as a last resort.
                best_move = min(
                    post_h2h_moves,
                    key=lambda m: get_coord_distance(future_head_positions[m], center_coord)
                )
            print(f"MOVE {game_state['turn']}: DEEP IN STORM - BFS escape route with {best_move} (dist: {escape_distances.get(best_move)})")
            return {"move": best_move}

    # ---------------------------------------------------------
    # CASE 2: NEAR HAZARD (On the border of the storm)
    # Hazard avoidance is active: avoid stepping into the hazard!
    # Exception: If critically starving (health <= 25) and an adjacent hazard tile
    # has food, take it to reset health to 100 (+86 net health!).
    # ---------------------------------------------------------
    if is_near_hazard:
        candidate_moves = list(non_hazard_moves)

        # Emergency starvation lifeline: If starving to death and food is on an adjacent hazard tile
        if my_health <= 25:
            hazard_food_moves = [
                m for m in hazard_moves
                if (future_head_positions[m]["x"], future_head_positions[m]["y"]) in all_food_coords
            ]
            if hazard_food_moves:
                print(f"MOVE {game_state['turn']}: CRITICAL STARVATION (Health: {my_health}) NEAR STORM - Emergency hazard food lifeline activated!")
                candidate_moves.extend(hazard_food_moves)

        # If all non-hazard moves were blocked, fall back to hazard moves heading to center
        if not candidate_moves:
            candidate_moves = post_h2h_moves

        # Target safe food in safe zone; if none exists and health < 50, target any food
        target_foods = safe_food_coords if safe_food_coords else (all_food_coords if my_health < 50 else set())
        best_move = pick_food_move(candidate_moves, target_foods)
        print(f"MOVE {game_state['turn']}: NEAR STORM (Health: {my_health}) - Moving safely with {best_move}")
        return {"move": best_move}

    # ---------------------------------------------------------
    # CASE 3: SAFELY OUTSIDE HAZARDS
    # Food seeking happens NORMALLY without aggressive hazard deprioritization!
    # ---------------------------------------------------------
    # In the safe zone, all candidate moves are safe from hazards
    candidate_moves = post_h2h_moves

    # Target food in safe zone; if safe zone is depleted, target closest food on board
    target_foods = safe_food_coords if safe_food_coords else all_food_coords

    if target_foods:
        best_move = pick_food_move(candidate_moves, target_foods)
        print(f"MOVE {game_state['turn']}: SAFELY OUTSIDE HAZARD - Seeking food with {best_move} (Health: {my_health}, Room: {space_by_move[best_move]})")
        return {"move": best_move}

    # If no food on board, wander into maximum open space
    best_move = max(candidate_moves, key=lambda m: space_by_move[m])
    print(f"MOVE {game_state['turn']}: SAFELY OUTSIDE HAZARD - Wandering open space with {best_move}")
    return {"move": best_move}


# Start server when `python main.py` is run
if __name__ == "__main__":
    from server import run_server

    run_server({"info": info, "start": start, "move": move, "end": end})
