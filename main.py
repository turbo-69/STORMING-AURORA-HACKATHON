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
from collections import deque
import time


def compute_voronoi_control(
    cand_head: typing.Dict[str, int],
    opp_head: typing.Dict[str, int],
    board_width: int,
    board_height: int,
    all_obstacles: typing.Set[typing.Tuple[int, int]]
) -> typing.Tuple[int, int, int]:
    """
    Calculates Voronoi-style area control for a 1v1 duel.
    For every empty tile on the board:
    1. Shortest distance from cand_head using BFS.
    2. Shortest distance from opp_head using BFS.
    3. Counts tile as 'mine' if my_dist <= opp_dist (reaches faster or contests),
       otherwise 'theirs'.
    Returns: (my_tiles, opp_tiles, relative_score) where relative_score = my_tiles - opp_tiles.
    """
    cand_coord = (cand_head["x"], cand_head["y"])
    opp_coord = (opp_head["x"], opp_head["y"])

    # BFS 1: From my simulated candidate head
    my_dist = {cand_coord: 0}
    queue_my = deque([cand_coord])

    while queue_my:
        cx, cy = queue_my.popleft()
        d = my_dist[(cx, cy)]
        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            nx, ny = cx + dx, cy + dy
            if 0 <= nx < board_width and 0 <= ny < board_height:
                if (nx, ny) not in all_obstacles and (nx, ny) not in my_dist:
                    my_dist[(nx, ny)] = d + 1
                    queue_my.append((nx, ny))

    # BFS 2: From opponent's current head
    # Opponent cannot traverse through our existing body or our new head (cand_coord)
    opp_dist = {opp_coord: 0}
    queue_opp = deque([opp_coord])

    while queue_opp:
        cx, cy = queue_opp.popleft()
        d = opp_dist[(cx, cy)]
        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            nx, ny = cx + dx, cy + dy
            if 0 <= nx < board_width and 0 <= ny < board_height:
                if (nx, ny) not in all_obstacles and (nx, ny) not in opp_dist:
                    opp_dist[(nx, ny)] = d + 1
                    # Opponent can reach cand_coord, but cannot pass through our head
                    if (nx, ny) != cand_coord:
                        queue_opp.append((nx, ny))

    # All empty board tiles
    all_empty_tiles = {
        (x, y) for x in range(board_width) for y in range(board_height)
        if (x, y) not in all_obstacles
    }

    my_tiles = 0
    opp_tiles = 0

    for tile in all_empty_tiles:
        d_m = my_dist.get(tile, float("inf"))
        d_o = opp_dist.get(tile, float("inf"))

        if d_m == float("inf") and d_o == float("inf"):
            continue

        if d_m <= d_o:
            my_tiles += 1
        else:
            opp_tiles += 1

    return my_tiles, opp_tiles, my_tiles - opp_tiles


# STRATEGY GRADIENT: with 4 snakes alive, pure survival heuristics (above)
# are what matters -- there's no room for territorial play with that many
# bodies on the board. Once it's down to a 1v1, full minimax kicks in
# (see PART 2 below). This function fills the middle tier: exactly one
# other opponent remains alongside 2+ opponents (i.e. 3 snakes total) --
# too many for cheap minimax, but few enough that territory control
# starts to matter. Generalizes compute_voronoi_control to N opponents
# via a multi-source BFS (every opponent head expands simultaneously;
# a tile counts as "theirs" if ANY opponent reaches it at least as fast
# as we do).
def compute_multi_voronoi_control(
    cand_head: typing.Dict[str, int],
    opp_heads: typing.List[typing.Dict[str, int]],
    board_width: int,
    board_height: int,
    all_obstacles: typing.Set[typing.Tuple[int, int]]
) -> typing.Tuple[int, int, int]:
    cand_coord = (cand_head["x"], cand_head["y"])

    my_dist = {cand_coord: 0}
    queue_my = deque([cand_coord])
    while queue_my:
        cx, cy = queue_my.popleft()
        d = my_dist[(cx, cy)]
        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            nx, ny = cx + dx, cy + dy
            if 0 <= nx < board_width and 0 <= ny < board_height:
                if (nx, ny) not in all_obstacles and (nx, ny) not in my_dist:
                    my_dist[(nx, ny)] = d + 1
                    queue_my.append((nx, ny))

    # Multi-source BFS: all opponent heads expand at once, each tile keeps
    # the distance from whichever opponent reaches it first.
    opp_dist = {}
    queue_opp = deque()
    for h in opp_heads:
        coord = (h["x"], h["y"])
        if coord not in opp_dist:
            opp_dist[coord] = 0
            queue_opp.append(coord)
    while queue_opp:
        cx, cy = queue_opp.popleft()
        d = opp_dist[(cx, cy)]
        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            nx, ny = cx + dx, cy + dy
            if 0 <= nx < board_width and 0 <= ny < board_height:
                if (nx, ny) not in all_obstacles and (nx, ny) not in opp_dist:
                    if (nx, ny) != cand_coord:
                        opp_dist[(nx, ny)] = d + 1
                        queue_opp.append((nx, ny))

    all_empty_tiles = {
        (x, y) for x in range(board_width) for y in range(board_height)
        if (x, y) not in all_obstacles
    }

    my_tiles = 0
    opp_tiles = 0
    for tile in all_empty_tiles:
        d_m = my_dist.get(tile, float("inf"))
        d_o = opp_dist.get(tile, float("inf"))
        if d_m == float("inf") and d_o == float("inf"):
            continue
        if d_m <= d_o:
            my_tiles += 1
        else:
            opp_tiles += 1

    return my_tiles, opp_tiles, my_tiles - opp_tiles


# ---------------------------------------------------------
# PART 1: AREA-CONTROL SCORING FUNCTION WITH EDGE/CORNER WEIGHTING
# ---------------------------------------------------------
def evaluate_board_state(
    my_head: typing.Tuple[int, int],
    my_body: typing.List[typing.Tuple[int, int]],
    opp_head: typing.Tuple[int, int],
    opp_body: typing.List[typing.Tuple[int, int]],
    board_width: int,
    board_height: int,
) -> float:
    """
    Given a 1v1 board state, returns a single heuristic score (higher is better for us):
    1. For every empty tile, calculates shortest BFS distance from my head and opp head.
    2. Tile is 'mine' if my_dist <= opp_dist (reaches faster or equal/contests), else 'theirs'.
    3. Adds bonus for edge tiles (+0.5) and corner tiles (+1.0) because edge-control limits
       the opponent's escape routes.
    """
    all_obstacles = set(my_body) | set(opp_body)

    # BFS from my head
    my_dist = {my_head: 0}
    q_my = deque([my_head])
    while q_my:
        curr = q_my.popleft()
        d = my_dist[curr]
        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            nx, ny = curr[0] + dx, curr[1] + dy
            if 0 <= nx < board_width and 0 <= ny < board_height:
                if (nx, ny) not in all_obstacles and (nx, ny) not in my_dist:
                    my_dist[(nx, ny)] = d + 1
                    q_my.append((nx, ny))

    # BFS from opponent head
    opp_dist = {opp_head: 0}
    q_opp = deque([opp_head])
    while q_opp:
        curr = q_opp.popleft()
        d = opp_dist[curr]
        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            nx, ny = curr[0] + dx, curr[1] + dy
            if 0 <= nx < board_width and 0 <= ny < board_height:
                if (nx, ny) not in all_obstacles and (nx, ny) not in opp_dist:
                    opp_dist[(nx, ny)] = d + 1
                    q_opp.append((nx, ny))

    # Calculate weighted ownership
    my_score = 0.0
    opp_score = 0.0

    all_empty = {
        (x, y) for x in range(board_width) for y in range(board_height)
        if (x, y) not in all_obstacles
    }

    for x, y in all_empty:
        d_m = my_dist.get((x, y), float("inf"))
        d_o = opp_dist.get((x, y), float("inf"))

        if d_m == float("inf") and d_o == float("inf"):
            continue

        # Weighting: standard = 1.0, edge = 1.5 (+0.5), corner = 2.0 (+1.0)
        is_corner = (x in (0, board_width - 1) and y in (0, board_height - 1))
        is_edge = (x == 0 or x == board_width - 1 or y == 0 or y == board_height - 1)

        if is_corner:
            weight = 2.0
        elif is_edge:
            weight = 1.5
        else:
            weight = 1.0

        if d_m <= d_o:
            my_score += weight
        else:
            opp_score += weight

    return my_score - opp_score


# ---------------------------------------------------------
# PART 2: ITERATIVE DEEPENING MINIMAX WITH ALPHA-BETA PRUNING & MOVE ORDERING
# ---------------------------------------------------------
class SearchTimeout(Exception):
    """Raised when the search reaches the allocated time budget."""
    pass


DIRECTIONS = {
    "up": (0, 1),
    "down": (0, -1),
    "left": (-1, 0),
    "right": (1, 0),
}


def get_legal_sim_moves(head, body, other_body, board_width, board_height):
    """
    Returns legal directions for a snake in simulation, preventing out-of-bounds,
    neck reversals, and collisions with solid body segments (taking tail vacancy into account).
    """
    legal = []
    neck = body[1] if len(body) > 1 else None
    solid_obstacles = set(body[:-1]) | set(other_body[:-1])

    for move_name, (dx, dy) in DIRECTIONS.items():
        nx, ny = head[0] + dx, head[1] + dy
        if 0 <= nx < board_width and 0 <= ny < board_height:
            if neck and (nx, ny) == neck:
                continue
            if (nx, ny) not in solid_obstacles:
                legal.append(move_name)
    return legal


def order_moves_max(moves, my_body, opp_body, food, board_width, board_height, pv_move=None):
    """
    Orders MAX moves: Principal Variation (PV) move from previous depth first,
    then descending by 1-ply area-control evaluation.
    """
    if not moves or len(moves) == 1:
        return moves

    my_head = my_body[0]
    opp_head = opp_body[0]

    def score_move(m):
        dx, dy = DIRECTIONS[m]
        new_head = (my_head[0] + dx, my_head[1] + dy)
        new_body = [new_head] + (my_body if new_head in food else my_body[:-1])
        return evaluate_board_state(new_head, new_body, opp_head, opp_body, board_width, board_height)

    sorted_moves = sorted(moves, key=score_move, reverse=True)

    # Promote PV move to the front to trigger earliest possible alpha-beta cutoffs
    if pv_move and pv_move in sorted_moves:
        sorted_moves.remove(pv_move)
        sorted_moves.insert(0, pv_move)

    return sorted_moves


def order_moves_min(moves, opp_body, my_body, food, board_width, board_height):
    """
    Orders MIN moves: ascending by our board score (best move for opponent first).
    """
    if not moves or len(moves) == 1:
        return moves

    my_head = my_body[0]
    opp_head = opp_body[0]

    def score_move(m):
        dx, dy = DIRECTIONS[m]
        new_head = (opp_head[0] + dx, opp_head[1] + dy)
        new_body = [new_head] + (opp_body if new_head in food else opp_body[:-1])
        return evaluate_board_state(my_head, my_body, new_head, new_body, board_width, board_height)

    return sorted(moves, key=score_move)


def minimax_alpha_beta(
    my_body: typing.List[typing.Tuple[int, int]],
    opp_body: typing.List[typing.Tuple[int, int]],
    food: typing.Set[typing.Tuple[int, int]],
    board_width: int,
    board_height: int,
    depth: int,
    alpha: float,
    beta: float,
    is_maximizing: bool,
    start_time: float,
    time_limit: float,
) -> float:
    """
    Minimax search with alpha-beta pruning and move ordering.
    Raises SearchTimeout when the elapsed time exceeds time_limit.
    """
    if time.perf_counter() - start_time > time_limit:
        raise SearchTimeout()

    if depth == 0:
        return evaluate_board_state(
            my_body[0], my_body, opp_body[0], opp_body, board_width, board_height
        )

    my_head = my_body[0]
    opp_head = opp_body[0]

    if is_maximizing:
        # MAX: My turn
        legal_moves = get_legal_sim_moves(my_head, my_body, opp_body, board_width, board_height)
        if not legal_moves:
            return -100000.0 + depth  # Loss: trapped/collided

        # Move ordering: best moves evaluated first
        ordered_moves = order_moves_max(legal_moves, my_body, opp_body, food, board_width, board_height)

        max_eval = -float("inf")
        for m in ordered_moves:
            dx, dy = DIRECTIONS[m]
            new_head = (my_head[0] + dx, my_head[1] + dy)

            if new_head in food:
                new_my_body = [new_head] + my_body
                new_food = food - {new_head}
            else:
                new_my_body = [new_head] + my_body[:-1]
                new_food = food

            score = minimax_alpha_beta(
                new_my_body, opp_body, new_food, board_width, board_height,
                depth - 1, alpha, beta, False, start_time, time_limit
            )
            max_eval = max(max_eval, score)
            alpha = max(alpha, score)
            if beta <= alpha:
                break  # Beta cutoff
        return max_eval

    else:
        # MIN: Opponent's turn
        legal_moves = get_legal_sim_moves(opp_head, opp_body, my_body, board_width, board_height)
        if not legal_moves:
            return 100000.0 - depth  # Win: opponent trapped/collided

        # Move ordering: opponent's best moves evaluated first
        ordered_moves = order_moves_min(legal_moves, opp_body, my_body, food, board_width, board_height)

        min_eval = float("inf")
        for m in ordered_moves:
            dx, dy = DIRECTIONS[m]
            new_head = (opp_head[0] + dx, opp_head[1] + dy)

            # Head-to-head collision resolution
            if new_head == my_head:
                if len(my_body) > len(opp_body):
                    score = 100000.0 - depth  # We win head-to-head
                else:
                    score = -100000.0 + depth  # We lose head-to-head
            else:
                if new_head in food:
                    new_opp_body = [new_head] + opp_body
                    new_food = food - {new_head}
                else:
                    new_opp_body = [new_head] + opp_body[:-1]
                    new_food = food

                score = minimax_alpha_beta(
                    my_body, new_opp_body, new_food, board_width, board_height,
                    depth - 1, alpha, beta, True, start_time, time_limit
                )

            min_eval = min(min_eval, score)
            beta = min(beta, score)
            if beta <= alpha:
                break  # Alpha cutoff
        return min_eval


def select_best_minimax_move(
    candidate_moves: typing.List[str],
    my_body: typing.List[typing.Tuple[int, int]],
    opp_body: typing.List[typing.Tuple[int, int]],
    food: typing.Set[typing.Tuple[int, int]],
    board_width: int,
    board_height: int,
    time_limit: float = 0.200,
    max_depth: int = 10,
) -> typing.Tuple[str, float, int, float, typing.Dict[str, float]]:
    """
    Iterative Deepening Minimax with Move Ordering.
    Searches depth 1, 2, 3, ... using the available time budget (target 200ms).
    Leaves a massive 300ms buffer under Battlesnake's 500ms hard limit.
    Guarantees a safe fallback move is always available.
    Returns: (best_move, best_score, reached_depth, duration_ms, scores_by_move)
    """
    start_time = time.perf_counter()
    my_head = my_body[0]

    # Critical fallback requirement: always have a valid candidate move ready
    best_overall_move = candidate_moves[0]
    best_overall_score = -float("inf")
    reached_depth = 1
    scores_by_move = {}
    pv_move = candidate_moves[0]

    for depth in range(1, max_depth + 1):
        elapsed = time.perf_counter() - start_time
        # If elapsed exceeds 40% of time limit or >90ms, do not risk starting next depth
        if elapsed > time_limit * 0.40 or elapsed > 0.090:
            break

        try:
            # Move ordering at root: PV move first, then remaining candidate moves
            ordered_moves = order_moves_max(
                candidate_moves, my_body, opp_body, food, board_width, board_height, pv_move=pv_move
            )

            depth_best_move = ordered_moves[0]
            depth_best_score = -float("inf")
            alpha = -float("inf")
            beta = float("inf")
            current_depth_scores = {}

            for m in ordered_moves:
                if time.perf_counter() - start_time > time_limit:
                    raise SearchTimeout()

                dx, dy = DIRECTIONS[m]
                new_head = (my_head[0] + dx, my_head[1] + dy)

                if new_head in food:
                    new_my_body = [new_head] + my_body
                    new_food = food - {new_head}
                else:
                    new_my_body = [new_head] + my_body[:-1]
                    new_food = food

                score = minimax_alpha_beta(
                    new_my_body, opp_body, new_food, board_width, board_height,
                    depth - 1, alpha, beta, False, start_time, time_limit
                )
                current_depth_scores[m] = score

                if score > depth_best_score:
                    depth_best_score = score
                    depth_best_move = m
                alpha = max(alpha, depth_best_score)

            # Successfully completed this depth: update best overall results
            best_overall_move = depth_best_move
            best_overall_score = depth_best_score
            reached_depth = depth
            scores_by_move = current_depth_scores
            pv_move = depth_best_move

            # Terminal win detected: stop deepening early
            if best_overall_score >= 90000:
                break

        except SearchTimeout:
            # Timed out mid-iteration: safely stop and use results from last completed depth
            break

    duration_ms = (time.perf_counter() - start_time) * 1000
    return best_overall_move, best_overall_score, reached_depth, duration_ms, scores_by_move


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
    # 1v1 VORONOI AREA-CONTROL EVALUATION
    # For duels against a single opponent, evaluate territorial control:
    # 1. Shortest distance from our candidate head to each empty tile
    # 2. Shortest distance from opponent head to each empty tile
    # 3. Controlled area = my_tiles - opp_tiles (relative advantage)
    # ---------------------------------------------------------
    alive_opponents = [s for s in opponents if s.get("id") != my_id]
    is_1v1 = (len(alive_opponents) == 1)
    opp_snake = alive_opponents[0] if is_1v1 else None
    opp_head = opp_snake["body"][0] if is_1v1 else None

    my_body_tuples = [(segment["x"], segment["y"]) for segment in my_body]
    opp_body_tuples = [(segment["x"], segment["y"]) for segment in opp_snake["body"]] if is_1v1 else []

    voronoi_stats = {}
    if is_1v1:
        for m in safe_moves:
            cand_head = future_head_positions[m]
            m_tiles, o_tiles, score = compute_voronoi_control(
                cand_head, opp_head, board_width, board_height, all_obstacles
            )
            voronoi_stats[m] = {
                "my_tiles": m_tiles,
                "opp_tiles": o_tiles,
                "score": score,
            }

    # STRATEGY GRADIENT (middle tier): exactly 3 snakes alive total (us +
    # 2 opponents). Too many for cheap minimax, but few enough that territory
    # control is worth factoring in rather than pure single-snake space.
    # Uses the same Voronoi-style scoring as 1v1, generalized via multi-source
    # BFS across both opponents. 4-snake play (below this) is untouched --
    # pure survival heuristics, no territorial reasoning.
    is_three_snake = (len(alive_opponents) == 2)
    if is_three_snake:
        opp_heads = [opp["body"][0] for opp in alive_opponents]
        for m in safe_moves:
            cand_head = future_head_positions[m]
            m_tiles, o_tiles, score = compute_multi_voronoi_control(
                cand_head, opp_heads, board_width, board_height, all_obstacles
            )
            voronoi_stats[m] = {
                "my_tiles": m_tiles,
                "opp_tiles": o_tiles,
                "score": score,
            }

    # Helper scoring key: in 1v1 or 3-snake play, prefer moves maximizing
    # relative controlled area; with 4 snakes, fall back to raw single-snake
    # reachable space (pure survival, no territorial contest).
    def move_preference_key(m):
        if (is_1v1 or is_three_snake) and m in voronoi_stats:
            return (voronoi_stats[m]["score"], voronoi_stats[m]["my_tiles"])
        return (space_by_move.get(m, 0), 0)

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

    # Helper to choose best move towards food among candidate moves
    def pick_food_move(moves_to_choose_from, preferred_foods):
        # 1. First see if any move immediately eats food this turn
        immediate_food_moves = [
            m for m in moves_to_choose_from
            if (future_head_positions[m]["x"], future_head_positions[m]["y"]) in preferred_foods
        ]
        if immediate_food_moves:
            return max(immediate_food_moves, key=move_preference_key)

        # 2. Check BFS walkable distance to nearest preferred food
        food_distances = {
            m: find_food_distance_bfs(future_head_positions[m], preferred_foods)
            for m in moves_to_choose_from
        }
        min_bfs_dist = min(food_distances.values())

        if min_bfs_dist < float("inf"):
            best_moves = [m for m in moves_to_choose_from if food_distances[m] == min_bfs_dist]
            return max(best_moves, key=move_preference_key)

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
            return max(best_moves, key=move_preference_key)

        # 4. Fall back to highest relative area-control or open space
        return max(moves_to_choose_from, key=move_preference_key)

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
            best_move = max(immediate_food, key=move_preference_key)
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
            # All moves still in hazard: steer towards center to escape storm
            best_move = min(
                post_h2h_moves,
                key=lambda m: get_coord_distance(future_head_positions[m], center_coord)
            )
            print(f"MOVE {game_state['turn']}: DEEP IN STORM - Steering towards center with {best_move}")
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

        # In 1v1 near storm, if healthy, dominate area control safely inside non-hazard using Iterative Minimax
        if is_1v1 and my_health > 35 and candidate_moves:
            best_move, score, reached_depth, duration_ms, all_scores = select_best_minimax_move(
                candidate_moves, my_body_tuples, opp_body_tuples, all_food_coords,
                board_width, board_height, time_limit=0.200
            )
            print(f"MOVE {game_state['turn']} (1v1 NEAR STORM ITERATIVE MINIMAX): Selected {best_move} (Score: {score:.1f}, Reached Depth: {reached_depth}, Time: {duration_ms:.1f}ms, Choices: {all_scores})", flush=True)
            return {"move": best_move}

        # Target safe food in safe zone; if none exists and health < 50, target any food
        target_foods = safe_food_coords if safe_food_coords else (all_food_coords if my_health < 50 else set())
        best_move = pick_food_move(candidate_moves, target_foods)
        print(f"MOVE {game_state['turn']}: NEAR STORM (Health: {my_health}) - Moving safely with {best_move}", flush=True)
        return {"move": best_move}

    # ---------------------------------------------------------
    # CASE 3: SAFELY OUTSIDE HAZARDS
    # ---------------------------------------------------------
    candidate_moves = post_h2h_moves

    # BUGFIX (Royale hazard/starvation deaths): previously this phase did pure
    # food-seeking with zero awareness of the storm, even in Royale. Testing
    # showed 44% of deaths at 11x11 and 73% at 19x19 were from hazard damage
    # or starvation -- snakes were reacting to the storm only once already
    # near/inside it, by which point they're sometimes too deep in a region
    # to escape before health runs out. We have no visibility into exactly
    # when the storm next shrinks, so instead of reacting, we proactively
    # drift toward the board center whenever we're comfortably healthy and
    # currently far from it -- keeping us closer to safety by the time the
    # storm actually arrives. Applies before the 1v1 minimax branch below
    # since positioning safety takes priority over tactical play; only
    # applies in the royale ruleset, standard mode is unaffected.
    #
    # REGRESSION FOUND AND FIXED: originally gated only on ruleset, this
    # engaged from turn 0 even with zero hazards anywhere on the board --
    # every snake (all comfortably healthy and far from center at spawn)
    # beelined straight for the exact center simultaneously and collided in
    # an entirely unforced pile-up (confirmed via a real match: 4 snakes,
    # 0 hazards the whole game, all walked in a straight line to center,
    # died in a mutual collision on turn 8). Now also requires the storm to
    # have actually started (hazard_coords non-empty) before drifting --
    # still proactive relative to OUR position, just not before there's any
    # storm on the board at all.
    is_royale_ruleset = game_state.get("game", {}).get("ruleset", {}).get("name") == "royale"
    if is_royale_ruleset and hazard_coords:
        my_dist_from_center = get_coord_distance(my_head, center_coord)
        DRIFT_HEALTH_THRESHOLD = 80
        DRIFT_DISTANCE_THRESHOLD = max(board_width, board_height) // 4

        if my_health > DRIFT_HEALTH_THRESHOLD and my_dist_from_center > DRIFT_DISTANCE_THRESHOLD:
            # Don't skip a free meal that's right next to us on the way
            immediate_food_moves = [
                m for m in candidate_moves
                if (future_head_positions[m]["x"], future_head_positions[m]["y"]) in all_food_coords
            ]
            if immediate_food_moves:
                best_move = max(immediate_food_moves, key=lambda m: space_by_move[m])
                print(f"MOVE {game_state['turn']}: SAFELY OUTSIDE HAZARD - Grabbing adjacent food with {best_move}", flush=True)
                return {"move": best_move}

            best_move = min(
                candidate_moves,
                key=lambda m: get_coord_distance(future_head_positions[m], center_coord)
            )
            print(f"MOVE {game_state['turn']}: SAFELY OUTSIDE HAZARD - Proactively drifting toward center with {best_move} (dist_from_center: {my_dist_from_center}, health: {my_health})", flush=True)
            return {"move": best_move}

    # Target food in safe zone; if safe zone is depleted, target closest food on board
    target_foods = safe_food_coords if safe_food_coords else all_food_coords

    # 1v1 DUEL LOGIC: Iterative Deepening Minimax with Move Ordering
    if is_1v1 and candidate_moves:
        opp_length = len(opp_snake["body"])

        # 1. Starvation urgency: When health is low, seeking food is top priority
        if my_health <= 35 and target_foods:
            best_move = pick_food_move(candidate_moves, target_foods)
            stats = voronoi_stats.get(best_move, {})
            print(f"MOVE {game_state['turn']} (1v1 HUNGRY): Seeking food with {best_move} (Health: {my_health})", flush=True)
            return {"move": best_move}

        # 2. Opportunistic growth: If adjacent safe food exists and we are equal/shorter than opponent
        immediate_safe_food = [
            m for m in candidate_moves
            if (future_head_positions[m]["x"], future_head_positions[m]["y"]) in target_foods
        ]
        if immediate_safe_food and my_length <= opp_length:
            best_move, score, reached_depth, duration_ms, all_scores = select_best_minimax_move(
                immediate_safe_food, my_body_tuples, opp_body_tuples, all_food_coords,
                board_width, board_height, time_limit=0.200
            )
            print(f"MOVE {game_state['turn']} (1v1 GROWTH ITERATIVE MINIMAX): Eating food with {best_move} (Score: {score:.1f}, Depth: {reached_depth}, Time: {duration_ms:.1f}ms)", flush=True)
            return {"move": best_move}

        # 3. Tactical Domination: Iterative Deepening Minimax with move ordering
        best_move, score, reached_depth, duration_ms, all_scores = select_best_minimax_move(
            candidate_moves, my_body_tuples, opp_body_tuples, all_food_coords,
            board_width, board_height, time_limit=0.200
        )
        print(f"MOVE {game_state['turn']} (1v1 ITERATIVE MINIMAX): Selected {best_move} (Score: {score:.1f}, Reached Depth: {reached_depth}, Time: {duration_ms:.1f}ms, Choices: {all_scores})", flush=True)
        return {"move": best_move}

    # MULTI-SNAKE LOGIC (Standard qualifying round with > 1 opponent)
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
