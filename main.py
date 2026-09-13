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
import os


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
# ROYALE HAZARD SHRINK TIMING HELPERS
# ---------------------------------------------------------
def get_shrink_interval(game_state: typing.Dict) -> int:
    """
    Checks game_state for the ruleset's 'royale.shrinkEveryNTurns' setting,
    or defaults to assuming every 25 turns if that field isn't available.
    """
    ruleset = game_state.get("game", {}).get("ruleset", {})
    if not ruleset and "ruleset" in game_state:
        ruleset = game_state.get("ruleset", {})

    settings = ruleset.get("settings", {}) if isinstance(ruleset, dict) else {}

    # 1. Flat key format: "royale.shrinkEveryNTurns"
    if "royale.shrinkEveryNTurns" in settings:
        try:
            return int(settings["royale.shrinkEveryNTurns"])
        except (ValueError, TypeError):
            pass

    # 2. Nested dict format: {"royale": {"shrinkEveryNTurns": ...}}
    royale_settings = settings.get("royale", {})
    if isinstance(royale_settings, dict) and "shrinkEveryNTurns" in royale_settings:
        try:
            return int(royale_settings["shrinkEveryNTurns"])
        except (ValueError, TypeError):
            pass

    # Default to assuming every 25 turns
    return 25


def get_turns_until_shrink(game_state: typing.Dict) -> int:
    """
    Calculates turns remaining until the next Royale hazard shrink event:
    1. Tracks current turn modulo the shrink interval.
    2. Immediately after a shrink occurs, plenty of time remains before the next.
    """
    turn = game_state.get("turn", 0)
    shrink_interval = get_shrink_interval(game_state)
    if shrink_interval <= 0:
        shrink_interval = 25

    turns_into_cycle = turn % shrink_interval
    return shrink_interval - turns_into_cycle if turns_into_cycle != 0 else shrink_interval


def get_hazard_damage_per_turn(game_state: dict) -> int:
    """Reads ruleset settings for hazard damage-per-turn (checks both a flat
    'damagePerTurn' key and a nested {'royale': {'damagePerTurn': ...}} key).
    Defaults to 15 if not present (PRD Section 6 flags the real figure as an
    open question — default to the higher/more-conservative end)."""
    ruleset = game_state.get("game", {}).get("ruleset", {})
    if not ruleset and "ruleset" in game_state:
        ruleset = game_state.get("ruleset", {})
    settings = ruleset.get("settings", {}) if isinstance(ruleset, dict) else {}
    if "damagePerTurn" in settings:
        try:
            return max(1, int(settings["damagePerTurn"]))
        except (ValueError, TypeError):
            pass
    royale_settings = settings.get("royale", {})
    if isinstance(royale_settings, dict) and "damagePerTurn" in royale_settings:
        try:
            return max(1, int(royale_settings["damagePerTurn"]))
        except (ValueError, TypeError):
            pass
    return 15


def bfs_distance_to_safe_tile(start_coord, hazard_coords, obstacles, board_width, board_height, max_search=None) -> float:
    """BFS from start_coord to the nearest tile NOT in hazard_coords, routing
    around obstacles (hazard tiles themselves are passable). Returns 0 if
    start_coord is already safe, float('inf') if no safe tile is reachable
    within max_search steps (defaults to board_width * board_height)."""
    if start_coord not in hazard_coords:
        return 0
    if max_search is None:
        max_search = board_width * board_height
    visited = {start_coord}
    queue = deque([(start_coord[0], start_coord[1], 0)])
    while queue:
        cx, cy, dist = queue.popleft()
        if dist >= max_search:
            continue
        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            nx, ny = cx + dx, cy + dy
            coord = (nx, ny)
            if 0 <= nx < board_width and 0 <= ny < board_height:
                if coord not in obstacles and coord not in visited:
                    if coord not in hazard_coords:
                        return dist + 1
                    visited.add(coord)
                    queue.append((nx, ny, dist + 1))
    return float("inf")



# ---------------------------------------------------------
# OPPONENT MODELING (PERSISTENT TRACKER)
# ---------------------------------------------------------
# Stores up to 5 turns of opponent movement history per game
OPPONENT_TRACKER: typing.Dict[str, typing.Any] = {
    "game_id": None,
    "last_opp_head": None,
    "last_food": [],
    "recent_moves": deque(maxlen=5),  # boolean: True if move was towards nearest food
}


def reset_opponent_tracker(game_id: typing.Optional[str] = None):
    """Safely resets or re-initializes the opponent tracker."""
    OPPONENT_TRACKER["game_id"] = game_id
    OPPONENT_TRACKER["last_opp_head"] = None
    OPPONENT_TRACKER["last_food"] = []
    OPPONENT_TRACKER["recent_moves"].clear()


def update_opponent_tracker(
    game_state: typing.Dict,
    opp_head: typing.Optional[typing.Tuple[int, int]],
    current_food: typing.Optional[typing.List[typing.Tuple[int, int]]],
) -> bool:
    """
    Tracks opponent movement relative to food over the last 4-5 turns.
    Returns True if the opponent exhibits a naive/greedy food-chasing pattern.
    Fails safely back to False on ANY unexpected data or exception.
    """
    try:
        if not opp_head or current_food is None:
            return False

        current_game_id = game_state.get("game", {}).get("id")
        if OPPONENT_TRACKER["game_id"] != current_game_id:
            reset_opponent_tracker(current_game_id)

        last_head = OPPONENT_TRACKER["last_opp_head"]
        last_food = OPPONENT_TRACKER["last_food"]

        if last_head is not None and last_food:
            # Measure distance from previous head to nearest food on that turn
            prev_min_dist = min(abs(last_head[0] - fx) + abs(last_head[1] - fy) for fx, fy in last_food)
            # Measure distance from new head to that same food
            new_min_dist = min(abs(opp_head[0] - fx) + abs(opp_head[1] - fy) for fx, fy in last_food)

            # Did opponent step closer to food or eat food?
            moved_towards_food = (new_min_dist < prev_min_dist or opp_head in last_food)
            OPPONENT_TRACKER["recent_moves"].append(moved_towards_food)

        # Update last known state for next turn
        OPPONENT_TRACKER["last_opp_head"] = opp_head
        OPPONENT_TRACKER["last_food"] = list(current_food)

        # Naive check: At least 3 observed moves, and >= 75% of them were direct food-chasing
        moves = list(OPPONENT_TRACKER["recent_moves"])
        if len(moves) >= 3 and (sum(moves) / len(moves)) >= 0.75:
            return True
        return False
    except Exception:
        # 100% fail-safe fallback
        return False


# HOLE #3 FIX: the naive-food-chaser detector above only ever ran for the
# single 1v1 opponent, even though head-to-head prediction (the still-largest
# cause of death in 4-snake play) needs exactly this signal the most -- right
# now every equal-or-longer opponent gets treated as equally unpredictable,
# marking all 4 cells around their head as dangerous regardless of whether
# they're actually just going to beeline for the nearest food. This
# generalizes the same tracking logic to every alive opponent by id, so a
# detected-naive opponent's danger zone can be narrowed to their one
# most-likely cell instead of all 4, freeing up real options elsewhere
# without weakening safety against any opponent NOT flagged naive.
OPPONENT_TRACKERS: typing.Dict[str, typing.Dict[str, typing.Any]] = {}


def reset_opponent_trackers():
    OPPONENT_TRACKERS.clear()


def update_opponent_tracker_multi(
    game_id: typing.Optional[str],
    opp_id: str,
    opp_head: typing.Optional[typing.Tuple[int, int]],
    current_food: typing.Optional[typing.List[typing.Tuple[int, int]]],
) -> bool:
    """Same naive-food-chaser detection as update_opponent_tracker, but keyed
    per opponent id so it works for every alive opponent, not just a single
    1v1 duel partner. Fails safely back to False on any unexpected data."""
    try:
        if not opp_head or current_food is None:
            return False

        tracker = OPPONENT_TRACKERS.get(opp_id)
        if tracker is None or tracker.get("game_id") != game_id:
            tracker = {
                "game_id": game_id,
                "last_opp_head": None,
                "last_food": [],
                "recent_moves": deque(maxlen=5),
            }
            OPPONENT_TRACKERS[opp_id] = tracker

        last_head = tracker["last_opp_head"]
        last_food = tracker["last_food"]

        if last_head is not None and last_food:
            prev_min_dist = min(abs(last_head[0] - fx) + abs(last_head[1] - fy) for fx, fy in last_food)
            new_min_dist = min(abs(opp_head[0] - fx) + abs(opp_head[1] - fy) for fx, fy in last_food)
            moved_towards_food = (new_min_dist < prev_min_dist or opp_head in last_food)
            tracker["recent_moves"].append(moved_towards_food)

        tracker["last_opp_head"] = opp_head
        tracker["last_food"] = list(current_food)

        moves = list(tracker["recent_moves"])
        if len(moves) >= 3 and (sum(moves) / len(moves)) >= 0.75:
            return True
        return False
    except Exception:
        return False


# ---------------------------------------------------------
# SURVIVAL MODE HELPERS (Disadvantaged / Shortest Snake State)
# ---------------------------------------------------------
def check_survival_mode(my_length: int, alive_opponents: typing.List[typing.Dict]) -> bool:
    """
    Checks whether the snake should enter Survival Mode this turn:
    1. My snake is the shortest (or tied shortest) among all alive opponents, OR
    2. My snake is more than a small margin (> 1.0) shorter than the average opponent length.
    Returns False if no opponents are alive or upon any error.
    """
    try:
        if not alive_opponents:
            return False
        opp_lengths = [len(s.get("body", [])) for s in alive_opponents if s.get("body")]
        if not opp_lengths:
            return False

        min_opp_len = min(opp_lengths)
        if my_length <= min_opp_len:
            return True

        avg_opp_len = sum(opp_lengths) / float(len(opp_lengths))
        if my_length < (avg_opp_len - 1.0):
            return True

        return False
    except Exception:
        return False


def select_survival_mode_move(
    candidate_moves: typing.List[str],
    future_head_positions: typing.Dict[str, typing.Dict[str, int]],
    space_by_move: typing.Dict[str, int],
    alive_opponents: typing.List[typing.Dict],
    target_foods: typing.Set[typing.Tuple[int, int]],
    hazard_coords: typing.Set[typing.Tuple[int, int]],
    board_width: int,
    board_height: int,
    turns_until_shrink: int,
    find_food_distance_bfs_fn: typing.Callable,
) -> str:
    """
    Survival Mode Move Selection:
    1. Skips dominance-seeking and Minimax lookahead.
    2. Prioritizes food seeking and health restoration to grow out of disadvantage.
    3. Adds an extra avoidance buffer: strongly favors moves maximizing distance
       from ALL opponent heads (actively steering away).
    4. Ensures open space via flood fill and proactive Royale center bias.
    """
    if not candidate_moves:
        return "up"
    if len(candidate_moves) == 1:
        return candidate_moves[0]

    center_coord = {"x": board_width // 2, "y": board_height // 2}
    opp_heads = [
        (s["body"][0]["x"], s["body"][0]["y"])
        for s in alive_opponents if s.get("body")
    ]

    def survival_score(m: str) -> float:
        pos = future_head_positions[m]
        coord = (pos["x"], pos["y"])
        score = 0.0

        # Safety: Severe penalty for stepping into a hazard
        if coord in hazard_coords:
            score -= 500.0

        # 1. Opponent Head Distance Buffer (actively steer away from ANY opponent head)
        if opp_heads:
            min_opp_dist = min(abs(pos["x"] - ox) + abs(pos["y"] - oy) for ox, oy in opp_heads)
            # Heavy penalty if adjacent (strike zone danger)
            if min_opp_dist <= 1:
                score -= 150.0
            elif min_opp_dist == 2:
                score -= 20.0
            # Progressive reward for keeping extra distance (up to 6 tiles)
            score += min(6, min_opp_dist) * 20.0

        # 2. Food-Seeking Priority (growth is the path to safety)
        if target_foods:
            max_dim = board_width + board_height
            if coord in target_foods:
                score += (max_dim * 10.0) + 150.0  # Immediate food eating is top priority!
            else:
                dist = find_food_distance_bfs_fn(pos, target_foods)
                if dist < float("inf"):
                    score += (max_dim - min(max_dim, dist)) * 8.0
                else:
                    min_manhattan = min(abs(pos["x"] - fx) + abs(pos["y"] - fy) for fx, fy in target_foods)
                    score += (max_dim - min(max_dim, min_manhattan)) * 4.0

        # 3. Flood-Fill Reachable Space (Trap Avoidance)
        available_space = space_by_move.get(m, 0)
        score += min(available_space, board_width * board_height) * 0.5

        # 4. Royale Hazard Countdown Center Bias
        if turns_until_shrink <= 10:
            dist_to_center = abs(pos["x"] - center_coord["x"]) + abs(pos["y"] - center_coord["y"])
            max_c_dist = (board_width // 2) + (board_height // 2)
            c_closeness = (max_c_dist - dist_to_center) / max_c_dist if max_c_dist > 0 else 1.0
            urgency = (10 - max(1, turns_until_shrink) + 1) / 10.0
            score += c_closeness * 15.0 * urgency

        return score

    return max(candidate_moves, key=survival_score)


# ---------------------------------------------------------
# DOMINANCE MODE HELPERS (Meaningful Length Advantage State)
# ---------------------------------------------------------
def check_dominance_mode(my_length: int, alive_opponents: typing.List[typing.Dict], margin: float = 2.0) -> bool:
    """
    Dominance Mode Trigger Condition:
    Calculates my snake's length vs. every alive opponent snake's length.
    Triggers if:
    1. My snake is the strictly longest (or tied longest) among all alive opponents, AND
    2. My snake has a meaningful length margin (>= margin, default 2.0) over the average opponent.
    Returns False if no opponents are alive or upon any error.
    """
    try:
        if not alive_opponents:
            return False
        opp_lengths = [len(s.get("body", [])) for s in alive_opponents if s.get("body")]
        if not opp_lengths:
            return False

        max_opp_len = max(opp_lengths)
        if my_length < max_opp_len:
            return False

        avg_opp_len = sum(opp_lengths) / float(len(opp_lengths))
        if (my_length - avg_opp_len) < margin:
            return False

        return True
    except Exception:
        return False


def check_opportunist_mode(my_length: int, alive_opponents: typing.List[typing.Dict]) -> bool:
    """
    Opportunist Mode Trigger Condition:
    1. At least 3 snakes are still alive total (meaning len(alive_opponents) >= 2).
    2. Neither Survival Mode (shortest or disadvantaged) nor Dominance Mode (longest with margin >= 2.0)
       is currently active.
    i.e. My snake is roughly mid-pack with no clear advantage yet.
    Returns False if fewer than 2 opponents are alive (drops to 1v1).
    """
    try:
        if not alive_opponents or len(alive_opponents) < 2:
            return False
        if check_survival_mode(my_length, alive_opponents):
            return False
        if check_dominance_mode(my_length, alive_opponents):
            return False
        return True
    except Exception:
        return False


def determine_behavior_mode(my_length: int, alive_opponents: typing.List[typing.Dict]) -> str:
    """
    Determines the active high-level behavior mode across all 4 states in priority order:
    1. SURVIVAL: Safety-critical (shortest or below average length by margin)
    2. DOMINANCE: Meaningful length advantage (longest with >= 2.0 margin)
    3. OPPORTUNIST: 3+ snakes alive, mid-pack, third-party avoidance
    4. DEFAULT: 1v1 neutral duel or standard minimax
    Guarantees strict 4-way mutual exclusivity.
    """
    if check_survival_mode(my_length, alive_opponents):
        return "SURVIVAL"
    if check_dominance_mode(my_length, alive_opponents):
        return "DOMINANCE"
    if check_opportunist_mode(my_length, alive_opponents):
        return "OPPORTUNIST"
    return "DEFAULT"


def select_dominance_mode_move(
    candidate_moves: typing.List[str],
    future_head_positions: typing.Dict[str, typing.Dict[str, int]],
    space_by_move: typing.Dict[str, int],
    alive_opponents: typing.List[typing.Dict],
    all_obstacles: typing.Set[typing.Tuple[int, int]],
    board_width: int,
    board_height: int,
    my_health: int,
    target_foods: typing.Set[typing.Tuple[int, int]],
    hazard_coords: typing.Set[typing.Tuple[int, int]],
    turns_until_shrink: int,
    my_body_tuples: typing.List[typing.Tuple[int, int]],
    time_limit: float = 0.140,
) -> str:
    """
    Dominance Mode Move Selection:
    1. Actively prioritizes area-control and territory-denial over pure food-seeking.
    2. In 1v1: Uses Voronoi territory constriction (-1.6x on opponent tiles) and proximity squeeze.
    3. In Multiplayer (2+ opponents): Pinches shared corridors between opponents, constricting
       their space and forcing them into collisions.
    4. Food-seeking is suppressed unless starving (health <= 30).
    """
    if not candidate_moves:
        return "up"
    if len(candidate_moves) == 1:
        return candidate_moves[0]

    center_coord = {"x": board_width // 2, "y": board_height // 2}
    is_1v1 = (len(alive_opponents) == 1)

    # Emergency starvation check: If health is critically low (<= 30), allow food seeking
    if my_health <= 30 and target_foods:
        immediate_food = [m for m in candidate_moves if (future_head_positions[m]["x"], future_head_positions[m]["y"]) in target_foods]
        if immediate_food:
            return immediate_food[0]

    if is_1v1:
        opp_snake = alive_opponents[0]
        opp_body = [(s["x"], s["y"]) for s in opp_snake.get("body", [])]
        opp_head = opp_snake.get("body", [{}])[0]

        def dominance_1v1_score(m: str) -> float:
            cand = future_head_positions[m]
            coord = (cand["x"], cand["y"])
            if coord in hazard_coords:
                return -9999.0

            my_tiles, opp_tiles, rel_score = compute_voronoi_control(
                cand, opp_head, board_width, board_height, all_obstacles
            )
            # Territory Denial Metric: Heavily penalize opponent tiles (-1.6x)
            denial_score = (my_tiles * 1.0) - (opp_tiles * 1.6)

            # Proximity squeeze: get closer to the opponent head to compress their maneuverability
            dist_to_opp = abs(cand["x"] - opp_head["x"]) + abs(cand["y"] - opp_head["y"])
            max_d = board_width + board_height
            if max_d > 0:
                denial_score += ((max_d - dist_to_opp) / max_d) * 8.0

            # Edge / Corner perimeter weighting
            if cand["x"] in (0, board_width - 1) or cand["y"] in (0, board_height - 1):
                denial_score += 1.5

            # Royale center bias
            if turns_until_shrink <= 10:
                dist_c = abs(cand["x"] - center_coord["x"]) + abs(cand["y"] - center_coord["y"])
                max_c = (board_width // 2) + (board_height // 2)
                closeness = (max_c - dist_c) / max_c if max_c > 0 else 1.0
                urgency = (10 - max(1, turns_until_shrink) + 1) / 10.0
                denial_score += closeness * 8.0 * urgency

            return denial_score

        try:
            best_move, score, depth, dur, choices = select_best_minimax_move(
                candidate_moves, my_body_tuples, opp_body, set(),
                board_width, board_height, time_limit=time_limit,
                turns_until_shrink=turns_until_shrink, opp_is_naive=True
            )
            return max(candidate_moves, key=lambda m: dominance_1v1_score(m) + (choices.get(m, 0) * 0.5))
        except Exception:
            return max(candidate_moves, key=dominance_1v1_score)

    else:
        # MULTIPLAYER DOMINANCE (2+ opponents alive):
        # Constrict shared open space between multiple opponents.
        opp_heads = [(s["body"][0]["x"], s["body"][0]["y"]) for s in alive_opponents if s.get("body")]

        def dominance_multi_score(m: str) -> float:
            cand = future_head_positions[m]
            coord = (cand["x"], cand["y"])
            if coord in hazard_coords:
                return -9999.0

            score = float(space_by_move.get(m, 0))

            if len(opp_heads) >= 2:
                # Calculate distance to all opponent heads
                dists = [abs(cand["x"] - ox) + abs(cand["y"] - oy) for ox, oy in opp_heads]
                dists_sorted = sorted(dists)
                d_first, d_second = dists_sorted[0], dists_sorted[1]
                # Pinch bonus: close to both opponents to block their mutual open space
                shared_proximity = (d_first + d_second)
                max_d = (board_width + board_height) * 2
                score += ((max_d - shared_proximity) / max_d) * 25.0

            # Royale center bias
            if turns_until_shrink <= 10:
                dist_c = abs(cand["x"] - center_coord["x"]) + abs(cand["y"] - center_coord["y"])
                max_c = (board_width // 2) + (board_height // 2)
                closeness = (max_c - dist_c) / max_c if max_c > 0 else 1.0
                urgency = (10 - max(1, turns_until_shrink) + 1) / 10.0
                score += closeness * 10.0 * urgency

            return score

        return max(candidate_moves, key=dominance_multi_score)


# ---------------------------------------------------------
# OPPORTUNIST MODE MOVE SELECTION (Peripheral / Mid-Pack Strategy)
# ---------------------------------------------------------
def select_opportunist_mode_move(
    candidate_moves: typing.List[str],
    future_head_positions: typing.Dict[str, typing.Dict[str, int]],
    space_by_move: typing.Dict[str, int],
    alive_opponents: typing.List[typing.Dict],
    all_obstacles: typing.Set[typing.Tuple[int, int]],
    board_width: int,
    board_height: int,
    my_health: int,
    target_foods: typing.Set[typing.Tuple[int, int]],
    hazard_coords: typing.Set[typing.Tuple[int, int]],
    turns_until_shrink: int,
    find_food_distance_bfs_fn: typing.Callable,
) -> str:
    """
    Opportunist Mode Behavior:
    1. Third-Party / Cluster Avoidance: Stay peripheral and away from where other snakes are
       densely clustered or actively fighting each other.
    2. Head-to-Head Avoidance: Avoid initiating ANY head-to-head collision zones (even against
       shorter snakes), letting opponents fight each other instead.
    3. Normal Food & Health Management: Pursue food at moderate distance to steadily grow without
       over-committing to contested tiles.
    4. Trap Avoidance: Always maintain high flood-fill reachable space.
    5. Royale Storm Timing: Center-bias when shrink countdown <= 10.
    """
    if not candidate_moves:
        return "up"
    if len(candidate_moves) == 1:
        return candidate_moves[0]

    center_coord = {"x": board_width // 2, "y": board_height // 2}
    opp_heads = [
        (s["body"][0]["x"], s["body"][0]["y"])
        for s in alive_opponents
        if s.get("body") and len(s["body"]) > 0
    ]

    # Calculate centroid of all opponent heads (epicenter of opponent activity)
    if opp_heads:
        centroid_x = sum(h[0] for h in opp_heads) / float(len(opp_heads))
        centroid_y = sum(h[1] for h in opp_heads) / float(len(opp_heads))
    else:
        centroid_x, centroid_y = center_coord["x"], center_coord["y"]

    # All opponent strike zones (tiles adjacent to ANY opponent head)
    all_opp_strike_zones = set()
    for ox, oy in opp_heads:
        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            all_opp_strike_zones.add((ox + dx, oy + dy))

    max_dist = board_width + board_height

    def opportunist_score(m: str) -> float:
        cand = future_head_positions[m]
        cand_coord = (cand["x"], cand["y"])

        if cand_coord in hazard_coords:
            return -9999.0

        score = 0.0

        # 1. Voluntary Conflict Avoidance:
        # Do not step into adjacent tiles of ANY opponent head unless forced!
        if cand_coord in all_opp_strike_zones:
            score -= 60.0

        # 2. Cluster / Centroid Avoidance:
        # Reward distance away from opponent centroid (staying peripheral)
        dist_to_centroid = abs(cand["x"] - centroid_x) + abs(cand["y"] - centroid_y)
        score += (dist_to_centroid / max_dist) * 20.0

        # 3. Normal Food Seeking & Health Management
        # Prioritize food when health is moderate/low, or when safe food is nearby
        food_dist = find_food_distance_bfs_fn(cand, target_foods)
        if food_dist != float("inf"):
            urgency_mult = 35.0 if my_health <= 40 else 15.0
            score += max(0.0, (max_dist - food_dist) / max_dist) * urgency_mult
            if cand_coord in target_foods:
                score += 25.0

        # 4. Open Space / Trap Avoidance
        available_space = space_by_move.get(m, 0)
        score += min(available_space, board_width * board_height) * 0.4

        # 5. Royale Hazard Countdown Center Bias
        if turns_until_shrink <= 10:
            dist_to_center = abs(cand["x"] - center_coord["x"]) + abs(cand["y"] - center_coord["y"])
            max_c_dist = (board_width // 2) + (board_height // 2)
            c_closeness = (max_c_dist - dist_to_center) / max_c_dist if max_c_dist > 0 else 1.0
            urgency = (10 - max(1, turns_until_shrink) + 1) / 10.0
            score += c_closeness * 15.0 * urgency

        return score

    return max(candidate_moves, key=opportunist_score)


# ---------------------------------------------------------
# PART 1: AREA-CONTROL SCORING FUNCTION WITH EDGE/CORNER WEIGHTING & HAZARD-TIMING BIAS
# ---------------------------------------------------------
def evaluate_board_state(
    my_head: typing.Tuple[int, int],
    my_body: typing.List[typing.Tuple[int, int]],
    opp_head: typing.Tuple[int, int],
    opp_body: typing.List[typing.Tuple[int, int]],
    board_width: int,
    board_height: int,
    turns_until_shrink: typing.Optional[int] = None,
    opp_is_naive: bool = False,
) -> float:
    """
    Given a 1v1 board state, returns a heuristic evaluation score (higher is better for us):
    1. Area Control: BFS distance from my head vs opp head for every empty tile.
    2. Edge/Corner Weighting: +0.5 for edge tiles, +1.0 for corner tiles (perimeter choke control).
    3. Hazard-Timing Center Bias (Royale): When countdown to the next shrink event is close
       (<= 10 turns), adds a scaled bonus for board positions closer to the center of the board.
    4. Opponent Modeling: If opponent exhibits naive food-chasing, applies an aggression multiplier
       and territorial squeeze bonus to punish predictable play.
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

    base_score = my_score - opp_score

    # Opponent modeling: If opponent is naive, apply small aggression multiplier to positive advantage
    if opp_is_naive and base_score > 0:
        base_score *= 1.15
        if len(my_body) >= len(opp_body):
            dist_to_opp = abs(my_head[0] - opp_head[0]) + abs(my_head[1] - opp_head[1])
            max_d = board_width + board_height
            if max_d > 0:
                base_score += ((max_d - dist_to_opp) / max_d) * 3.0

    # Hazard-timing center bias (Royale countdown awareness)
    # Activates when next shrink is within 10 turns; scales up as countdown gets closer to 1.
    # Has zero effect right after a shrink (plenty of time before the next).
    if turns_until_shrink is not None and turns_until_shrink <= 10:
        urgency = (10 - max(1, turns_until_shrink) + 1) / 10.0
        center_x = (board_width - 1) * 0.5
        center_y = (board_height - 1) * 0.5
        max_dist = center_x + center_y

        if max_dist > 0:
            my_dist_to_center = abs(my_head[0] - center_x) + abs(my_head[1] - center_y)
            opp_dist_to_center = abs(opp_head[0] - center_x) + abs(opp_head[1] - center_y)
            inv_max = 1.0 / max_dist
            my_closeness = (max_dist - my_dist_to_center) * inv_max
            opp_closeness = (max_dist - opp_dist_to_center) * inv_max
            return base_score + (my_closeness + 0.5 * (my_closeness - opp_closeness)) * (6.0 * urgency)

    return base_score


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


def order_moves_max(moves, my_body, opp_body, food, board_width, board_height, pv_move=None, turns_until_shrink=None, opp_is_naive=False):
    """
    Orders MAX moves: Principal Variation (PV) move from previous depth first,
    then descending by 1-ply area-control evaluation with hazard-timing awareness.
    """
    if not moves or len(moves) == 1:
        return moves

    my_head = my_body[0]
    opp_head = opp_body[0]

    def score_move(m):
        dx, dy = DIRECTIONS[m]
        new_head = (my_head[0] + dx, my_head[1] + dy)
        new_body = [new_head] + (my_body if new_head in food else my_body[:-1])
        return evaluate_board_state(
            new_head, new_body, opp_head, opp_body, board_width, board_height,
            turns_until_shrink=turns_until_shrink, opp_is_naive=opp_is_naive
        )

    sorted_moves = sorted(moves, key=score_move, reverse=True)

    # Promote PV move to the front to trigger earliest possible alpha-beta cutoffs
    if pv_move and pv_move in sorted_moves:
        sorted_moves.remove(pv_move)
        sorted_moves.insert(0, pv_move)

    return sorted_moves


def order_moves_min(moves, opp_body, my_body, food, board_width, board_height, turns_until_shrink=None, opp_is_naive=False):
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
        return evaluate_board_state(
            my_head, my_body, new_head, new_body, board_width, board_height,
            turns_until_shrink=turns_until_shrink, opp_is_naive=opp_is_naive
        )

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
    turns_until_shrink: typing.Optional[int] = None,
    opp_is_naive: bool = False,
) -> float:
    """
    Minimax search with alpha-beta pruning and move ordering.
    Raises SearchTimeout when the elapsed time exceeds time_limit.
    """
    if time.perf_counter() - start_time > time_limit:
        raise SearchTimeout()

    if depth == 0:
        return evaluate_board_state(
            my_body[0], my_body, opp_body[0], opp_body, board_width, board_height,
            turns_until_shrink=turns_until_shrink, opp_is_naive=opp_is_naive
        )

    my_head = my_body[0]
    opp_head = opp_body[0]

    if is_maximizing:
        # MAX: My turn
        legal_moves = get_legal_sim_moves(my_head, my_body, opp_body, board_width, board_height)
        if not legal_moves:
            return -100000.0 + depth  # Loss: trapped/collided

        # Move ordering: best moves evaluated first
        ordered_moves = order_moves_max(
            legal_moves, my_body, opp_body, food, board_width, board_height,
            turns_until_shrink=turns_until_shrink, opp_is_naive=opp_is_naive
        )

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
                depth - 1, alpha, beta, False, start_time, time_limit,
                turns_until_shrink=turns_until_shrink, opp_is_naive=opp_is_naive
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
        ordered_moves = order_moves_min(
            legal_moves, opp_body, my_body, food, board_width, board_height,
            turns_until_shrink=turns_until_shrink, opp_is_naive=opp_is_naive
        )

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
                    depth - 1, alpha, beta, True, start_time, time_limit,
                    turns_until_shrink=turns_until_shrink, opp_is_naive=opp_is_naive
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
    time_limit: float = 0.140,
    max_depth: int = 10,
    turns_until_shrink: typing.Optional[int] = None,
    opp_is_naive: bool = False,
) -> typing.Tuple[str, float, int, float, typing.Dict[str, float]]:
    """
    Iterative Deepening Minimax with Move Ordering & Hazard-Timing Awareness.
    Searches depth 1, 2, 3, ... using the available time budget (target 140ms).
    Leaves an enormous 360ms buffer under Battlesnake's 500ms hard limit.
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
        # Conservative depth-break safeguard:
        # Each minimax ply typically increases search time by ~2.5x to 3x.
        # If elapsed exceeds 55ms (or 35% of time_limit), do not risk starting next depth.
        if elapsed > 0.055 or elapsed > (time_limit * 0.35):
            break

        try:
            # Move ordering at root: PV move first, then remaining candidate moves
            ordered_moves = order_moves_max(
                candidate_moves, my_body, opp_body, food, board_width, board_height,
                pv_move=pv_move, turns_until_shrink=turns_until_shrink, opp_is_naive=opp_is_naive
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
                    depth - 1, alpha, beta, False, start_time, time_limit,
                    turns_until_shrink=turns_until_shrink, opp_is_naive=opp_is_naive
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
    reset_opponent_tracker(game_state.get("game", {}).get("id"))
    reset_opponent_trackers()
    print("GAME START")


# end is called when your Battlesnake finishes a game
def end(game_state: typing.Dict):
    reset_opponent_tracker()
    reset_opponent_trackers()
    print("GAME OVER\n")


# move is called on every turn and returns your next move
# Valid moves are "up", "down", "left", or "right"
# See https://docs.battlesnake.com/api/example-move for available data
def move(game_state: typing.Dict) -> typing.Dict:

    is_move_safe = {"up": True, "down": True, "left": True, "right": True}

    # We've included code to prevent your Battlesnake from moving backwards
    you_info = game_state.get("you", {})
    my_body = you_info.get("body", [{"x": 0, "y": 0}])
    my_head = my_body[0]
    my_neck = my_body[1] if len(my_body) > 1 else {"x": my_head["x"], "y": my_head["y"]}

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
    board_width = game_state.get("board", {}).get("width", 11)
    board_height = game_state.get("board", {}).get("height", 11)
    my_handicap = int(os.environ.get("TEST_HANDICAP_MY_LENGTH", "0"))
    if my_handicap > 0:
        tail = my_body[-1]
        my_body = list(my_body) + [tail] * my_handicap
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
    opponents = game_state.get("board", {}).get("snakes", [])
    handicap = int(os.environ.get("TEST_HANDICAP_OPPONENT_LENGTH", "0"))
    if handicap > 0:
        for opp in opponents:
            if opp.get("id") != game_state.get("you", {}).get("id") and opp.get("body"):
                tail = opp["body"][-1]
                opp["body"] = list(opp["body"]) + [tail] * handicap
                opp["length"] = len(opp["body"])
                # In multiplayer matches, handicap only one opponent so mid-pack distribution is created
                if len(opponents) > 2:
                    break
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

    # Full board reachable space counter (dynamic for any board dimensions)
    def count_reachable_space(start_coord, max_limit=None):
        if max_limit is None:
            max_limit = board_width * board_height

        start_tuple = (start_coord["x"], start_coord["y"])
        visited = {start_tuple}
        queue = deque([start_tuple])

        while queue and len(visited) < max_limit:
            cx, cy = queue.popleft()
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                nx, ny = cx + dx, cy + dy
                if 0 <= nx < board_width and 0 <= ny < board_height:
                    if (nx, ny) not in all_obstacles and (nx, ny) not in visited:
                        visited.add((nx, ny))
                        queue.append((nx, ny))
        return len(visited)

    # FUNNEL-TRAP FIX: can we still loop back to our own tail from a given
    # cell? A cell can look "spacious enough" (Phase 2 below) right now and
    # still be a trap: as our body continues to fill in behind us each turn,
    # a pocket with no path back to the tail strictly shrinks until we run
    # out of room, even though the one-ply space count looked fine when we
    # committed to it. This is the standard, well-established Battlesnake
    # technique for catching that class of death (confirmed this session:
    # "healthy-HP" collisions from a slowly-closing corridor the plain
    # flood-fill count can't see coming). The tail cell itself is treated as
    # passable, since it vacates by the time a full loop back around would
    # reach it (approximate, but the standard assumption for this check).
    def can_reach_own_tail(start_coord, tail_coord, obstacles):
        """BFS from start_coord; True if tail_coord is reachable. Whether the
        tail cell itself counts as passable is entirely up to the caller via
        `obstacles` (exclude it to treat it as passable, include it to treat
        it as a real permanent obstacle) -- no special-casing here, so this
        gives the correct answer (always False) when the tail genuinely can't
        be used, instead of a hard-coded shortcut that ignored `obstacles`."""
        if start_coord == tail_coord:
            return True
        if start_coord in obstacles:
            return False
        visited = {start_coord}
        queue = deque([start_coord])
        while queue:
            cx, cy = queue.popleft()
            if (cx, cy) == tail_coord:
                return True
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                nx, ny = cx + dx, cy + dy
                coord = (nx, ny)
                if 0 <= nx < board_width and 0 <= ny < board_height:
                    if coord not in obstacles and coord not in visited:
                        visited.add(coord)
                        queue.append(coord)
        return False

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

    # FUNNEL-TRAP FIX: among the spacious candidates, further prefer ones that
    # can still loop back to our own tail. A "spacious enough right now" cell
    # can still be the first step into a pocket that closes over the next
    # several turns as our body fills in behind us -- tail-reachability is
    # what actually distinguishes a real, sustainable space from that trap.
    #
    # EDGE CASE: the tail is only actually passable if we didn't just eat --
    # health resets to exactly 100 on the turn we eat, and a snake that just
    # ate does NOT vacate its tail cell that turn (it grows instead). Treating
    # the tail as passable in that specific case would be an over-optimistic
    # answer to "is this really safe," the same class of error Bug #4 fixed
    # in the opposite direction.
    my_tail_coord = (my_body[-1]["x"], my_body[-1]["y"])
    just_ate = game_state.get("you", {}).get("health", 100) == 100
    obstacles_for_tail_check = all_obstacles if just_ate else (all_obstacles - {my_tail_coord})
    tail_safe_moves = [
        m for m in candidate_moves
        if can_reach_own_tail(
            (future_head_positions[m]["x"], future_head_positions[m]["y"]),
            my_tail_coord,
            obstacles_for_tail_check,
        )
    ]
    if tail_safe_moves:
        candidate_moves = tail_safe_moves

    # ---------------------------------------------------------
    # PHASE 3: HEAD-TO-HEAD COLLISION AVOIDANCE
    # If an opponent is equal or longer than us, avoid tiles they can move into!
    # If an opponent is strictly shorter than us, it's safe/good to contest that tile.
    # ---------------------------------------------------------
    dangerous_head_zones = set()
    opp_strike_zones = []
    my_id = game_state["you"].get("id")
    current_game_id = game_state.get("game", {}).get("id")
    food_coords_for_modeling = [(f["x"], f["y"]) for f in game_state.get("board", {}).get("food", [])]

    for opponent in opponents:
        if opponent.get("id") == my_id:
            continue

        opp_body = opponent["body"]
        opp_length = len(opp_body)
        opp_head = opp_body[0]

        # If opponent is equal or longer than us, a head-on collision kills or ties us
        if opp_length >= my_length:
            # HOLE #3 FIX: an opponent detected as a naive/predictable food-
            # chaser doesn't need all 4 neighbor cells treated as equally
            # dangerous -- narrow it to just their one most-likely next cell
            # (toward the nearest food) instead, freeing up the other 3 as
            # real options. Any opponent not confidently flagged naive keeps
            # the original, fully conservative treatment -- this only ever
            # removes over-caution, never adds risk.
            opp_id = opponent.get("id")
            opp_head_coord = (opp_head["x"], opp_head["y"])
            opp_is_naive_multi = (
                opp_id is not None
                and update_opponent_tracker_multi(current_game_id, opp_id, opp_head_coord, food_coords_for_modeling)
            )

            opp_zone = set()
            if opp_is_naive_multi and food_coords_for_modeling:
                nearest_food = min(
                    food_coords_for_modeling,
                    key=lambda f: abs(opp_head["x"] - f[0]) + abs(opp_head["y"] - f[1]),
                )
                best_dir, best_dist = None, None
                for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                    nx, ny = opp_head["x"] + dx, opp_head["y"] + dy
                    dist = abs(nx - nearest_food[0]) + abs(ny - nearest_food[1])
                    if best_dist is None or dist < best_dist:
                        best_dist, best_dir = dist, (nx, ny)
                if best_dir is not None:
                    opp_zone.add(best_dir)
                    dangerous_head_zones.add(best_dir)
                print(f"MOVE {game_state['turn']}: OPPONENT MODELING -> {opp_id} is a naive food-seeker, narrowing their danger zone to 1 cell", flush=True)
            else:
                for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                    coord = (opp_head["x"] + dx, opp_head["y"] + dy)
                    opp_zone.add(coord)
                    dangerous_head_zones.add(coord)
            opp_strike_zones.append(opp_zone)

    # Filter out moves that step into a larger/equal snake's strike zone
    h2h_safe_moves = [
        m for m in candidate_moves
        if (future_head_positions[m]["x"], future_head_positions[m]["y"]) not in dangerous_head_zones
    ]

    # If we have moves that avoid head-on danger, strictly use those!
    if h2h_safe_moves:
        post_h2h_moves = h2h_safe_moves
    elif candidate_moves:
        # Fallback tier: every candidate move steps into at least one opponent's strike zone.
        # Instead of falling back blindly and hoping the opponent turns away, score each move by:
        # 1. How many distinct equal-or-longer opponents could kill us there (fewer is better)
        # 2. Among ties, prefer the move that leaves the MOST reachable open space afterward
        h2h_killer_counts = {}
        for m in candidate_moves:
            cand_coord = (future_head_positions[m]["x"], future_head_positions[m]["y"])
            h2h_killer_counts[m] = sum(1 for zone in opp_strike_zones if cand_coord in zone)

        min_killers = min(h2h_killer_counts.values()) if h2h_killer_counts else 0
        min_killer_moves = [m for m in candidate_moves if h2h_killer_counts[m] == min_killers]

        if len(min_killer_moves) == 1:
            post_h2h_moves = min_killer_moves
        elif min_killer_moves:
            # Tiebreak by reachable space
            max_space = max(
                space_by_move.get(m, count_reachable_space(future_head_positions[m]))
                for m in min_killer_moves
            )
            best_space_moves = [
                m for m in min_killer_moves
                if space_by_move.get(m, count_reachable_space(future_head_positions[m])) == max_space
            ]
            post_h2h_moves = best_space_moves if best_space_moves else min_killer_moves
        else:
            post_h2h_moves = candidate_moves

        print(
            f"MOVE {game_state.get('turn', 0)}: H2H FALLBACK -> all moves threatened! "
            f"Filtered candidates to {post_h2h_moves} "
            f"(min_killers={min_killers}, evaluated {len(candidate_moves)} moves)",
            flush=True,
        )
    else:
        post_h2h_moves = candidate_moves

    hazards = game_state.get("board", {}).get("hazards", [])
    hazard_coords = {(h["x"], h["y"]) for h in hazards}
    food_list = game_state.get("board", {}).get("food", [])
    all_food_coords = {(f["x"], f["y"]) for f in food_list}
    safe_food_coords = {(f["x"], f["y"]) for f in food_list if (f["x"], f["y"]) not in hazard_coords}
    shrink_interval = get_shrink_interval(game_state)
    turns_until_shrink = get_turns_until_shrink(game_state)

    # BFS Walkable Path Distance to Food (navigating around bodies/obstacles, dynamic for any board size)
    def find_food_distance_bfs(start_coord, target_food_coords):
        if not target_food_coords:
            return float("inf")
        start = (start_coord["x"], start_coord["y"])
        if start in target_food_coords:
            return 0
        visited = {start}
        queue = deque([(start[0], start[1], 0)])
        max_search_dist = board_width + board_height
        while queue:
            cx, cy, dist = queue.popleft()
            if dist >= max_search_dist:
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

    alive_opponents = [s for s in opponents if s.get("id") != my_id]

    # ---------------------------------------------------------
    # BEHAVIOR MODE DISPATCH: SURVIVAL vs DOMINANCE vs DEFAULT
    # Checked once per turn, clean separate mutually-exclusive branches.
    # ---------------------------------------------------------
    mode = determine_behavior_mode(my_length, alive_opponents)

    turn_num = game_state.get("turn", 0)
    opp_lengths = [len(s.get("body", [])) for s in alive_opponents]
    max_opp_l = max(opp_lengths) if opp_lengths else 0
    avg_opp_l = (sum(opp_lengths) / len(opp_lengths)) if opp_lengths else 0.0

    if mode == "SURVIVAL":
        print(f"Turn {turn_num}: SURVIVAL MODE ACTIVE (My Length: {my_length}, Opp Max: {max_opp_l}, Opp Avg: {avg_opp_l:.1f})", flush=True)
    elif mode == "DOMINANCE":
        print(f"Turn {turn_num}: DOMINANCE MODE ACTIVE (My Length: {my_length}, Opp Max: {max_opp_l}, Opp Avg: {avg_opp_l:.1f})", flush=True)
    elif mode == "OPPORTUNIST":
        print(f"Turn {turn_num}: OPPORTUNIST MODE ACTIVE (My Length: {my_length}, Opp Max: {max_opp_l}, Alive Opps: {len(alive_opponents)})", flush=True)
    else:
        print(f"Turn {turn_num}: default behavior (My Length: {my_length}, Opp Max: {max_opp_l}, Opp Avg: {avg_opp_l:.1f})", flush=True)

    # ---------------------------------------------------------
    # BRANCH 1: SURVIVAL MODE (Shortest or Disadvantaged Snake)
    # ---------------------------------------------------------
    if mode == "SURVIVAL" and post_h2h_moves:
        survival_candidates = [
            m for m in post_h2h_moves
            if (future_head_positions[m]["x"], future_head_positions[m]["y"]) not in hazard_coords
        ]
        if not survival_candidates:
            survival_candidates = post_h2h_moves

        # Starvation lifeline: if critical health (<= 25) and food on hazard tile
        my_health = game_state.get("you", {}).get("health", 100)
        if my_health <= 25:
            for m in post_h2h_moves:
                pos = future_head_positions[m]
                if (pos["x"], pos["y"]) in all_food_coords and m not in survival_candidates:
                    survival_candidates.append(m)

        survival_foods = safe_food_coords if safe_food_coords else all_food_coords
        best_survival_move = select_survival_mode_move(
            candidate_moves=survival_candidates,
            future_head_positions=future_head_positions,
            space_by_move=space_by_move,
            alive_opponents=alive_opponents,
            target_foods=survival_foods,
            hazard_coords=hazard_coords,
            board_width=board_width,
            board_height=board_height,
            turns_until_shrink=turns_until_shrink,
            find_food_distance_bfs_fn=find_food_distance_bfs,
        )
        print(f"MOVE {game_state['turn']} (SURVIVAL MODE): Shortest/disadvantaged (Length: {my_length}) -> Selected {best_survival_move} (Distance Buffer Active, Seeking Food)", flush=True)
        return {"move": best_survival_move}

    # ---------------------------------------------------------
    # BRANCH 2: DOMINANCE MODE (Longest with Meaningful Margin)
    # ---------------------------------------------------------
    elif mode == "DOMINANCE" and post_h2h_moves:
        dominance_candidates = [
            m for m in post_h2h_moves
            if (future_head_positions[m]["x"], future_head_positions[m]["y"]) not in hazard_coords
        ]
        if not dominance_candidates:
            dominance_candidates = post_h2h_moves

        my_health = game_state.get("you", {}).get("health", 100)
        my_body_tuples = [(segment["x"], segment["y"]) for segment in my_body]
        best_dominance_move = select_dominance_mode_move(
            candidate_moves=dominance_candidates,
            future_head_positions=future_head_positions,
            space_by_move=space_by_move,
            alive_opponents=alive_opponents,
            all_obstacles=all_obstacles,
            board_width=board_width,
            board_height=board_height,
            my_health=my_health,
            target_foods=safe_food_coords if safe_food_coords else all_food_coords,
            hazard_coords=hazard_coords,
            turns_until_shrink=turns_until_shrink,
            my_body_tuples=my_body_tuples,
            time_limit=0.140,
        )
        print(f"MOVE {game_state['turn']} (DOMINANCE MODE): Longest with margin (Length: {my_length}) -> Selected {best_dominance_move} (Area-Control/Territory-Denial Active)", flush=True)
        return {"move": best_dominance_move}

    # ---------------------------------------------------------
    # BRANCH 3: OPPORTUNIST MODE (3+ Snakes Alive, Mid-Pack State)
    # ---------------------------------------------------------
    elif mode == "OPPORTUNIST" and post_h2h_moves:
        opportunist_candidates = [
            m for m in post_h2h_moves
            if (future_head_positions[m]["x"], future_head_positions[m]["y"]) not in hazard_coords
        ]
        if not opportunist_candidates:
            opportunist_candidates = post_h2h_moves

        my_health = game_state.get("you", {}).get("health", 100)
        best_opportunist_move = select_opportunist_mode_move(
            candidate_moves=opportunist_candidates,
            future_head_positions=future_head_positions,
            space_by_move=space_by_move,
            alive_opponents=alive_opponents,
            all_obstacles=all_obstacles,
            board_width=board_width,
            board_height=board_height,
            my_health=my_health,
            target_foods=safe_food_coords if safe_food_coords else all_food_coords,
            hazard_coords=hazard_coords,
            turns_until_shrink=turns_until_shrink,
            find_food_distance_bfs_fn=find_food_distance_bfs,
        )
        print(f"MOVE {game_state['turn']} (OPPORTUNIST MODE): Mid-pack (Length: {my_length}, {len(alive_opponents)} opps) -> Selected {best_opportunist_move} (Avoiding Clusters & Third-Party Contests)", flush=True)
        return {"move": best_opportunist_move}

    # ---------------------------------------------------------
    # BRANCH 4: DEFAULT / NEUTRAL MODE (Minimax + Opponent Modeling)
    # ---------------------------------------------------------
    # 1v1 VORONOI AREA-CONTROL EVALUATION
    # For duels against a single opponent, evaluate territorial control:
    # 1. Shortest distance from our candidate head to each empty tile
    # 2. Shortest distance from opponent head to each empty tile
    # 3. Controlled area = my_tiles - opp_tiles (relative advantage)
    # ---------------------------------------------------------
    is_1v1 = (len(alive_opponents) == 1)
    opp_snake = alive_opponents[0] if is_1v1 else None
    opp_head = opp_snake["body"][0] if is_1v1 else None

    opp_head_coord = (opp_head["x"], opp_head["y"]) if is_1v1 else None
    food_coords_list = [(f["x"], f["y"]) for f in game_state.get("board", {}).get("food", [])]
    opp_is_naive = update_opponent_tracker(game_state, opp_head_coord, food_coords_list) if is_1v1 else False
    if is_1v1 and opp_is_naive:
        print(f"MOVE {game_state['turn']}: OPPONENT MODELING -> Naive food-seeker detected! Aggressive pressure active.", flush=True)

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

    center_coord = {"x": board_width // 2, "y": board_height // 2}
    shrink_interval = get_shrink_interval(game_state)
    turns_until_shrink = get_turns_until_shrink(game_state)

    if turns_until_shrink <= 10:
        urgency = (10 - max(1, turns_until_shrink) + 1) / 10.0
        print(f"MOVE {game_state['turn']}: ROYALE SHRINK COUNTDOWN - {turns_until_shrink} turns until shrink (Interval: {shrink_interval}, Urgency: {urgency:.1f}, Proactive Center Bias Active)", flush=True)

    # Helper scoring key: in 1v1 or 3-snake play, prefer moves maximizing
    # relative controlled area; with 4 snakes, fall back to raw single-snake
    # reachable space (pure survival, no territorial contest). Incorporates
    # a proactive center bias when Royale shrink is approaching (supersedes
    # the old health/distance-based drift heuristic -- this is timing-precise
    # and blended as a soft bonus rather than a hard override, so it can't
    # cause the turn-0 unforced pile-up that heuristic had).
    def move_preference_key(m):
        base_score = voronoi_stats[m]["score"] if (is_1v1 or is_three_snake) and m in voronoi_stats else space_by_move.get(m, 0)
        tie_breaker = voronoi_stats[m]["my_tiles"] if (is_1v1 or is_three_snake) and m in voronoi_stats else 0

        if turns_until_shrink <= 10:
            cand = future_head_positions[m]
            dist_to_center = abs(cand["x"] - center_coord["x"]) + abs(cand["y"] - center_coord["y"])
            max_c_dist = (board_width // 2) + (board_height // 2)
            c_closeness = (max_c_dist - dist_to_center) / max_c_dist if max_c_dist > 0 else 1.0
            urgency = (10 - max(1, turns_until_shrink) + 1) / 10.0
            base_score += c_closeness * 6.0 * urgency

        return (base_score, tie_breaker)

    # ---------------------------------------------------------
    # PHASE 4 & 5: HAZARD AVOIDANCE & INTELLIGENT FOOD SEEKING
    # Food seeking happens normally when safely outside hazard zones.
    # Hazard avoidance is only prioritized when actually near or in a hazard.
    # ---------------------------------------------------------
    hazards = game_state.get("board", {}).get("hazards", [])
    hazard_coords = {(h["x"], h["y"]) for h in hazards}

    def get_coord_distance(a, b):
        return abs(a["x"] - b["x"]) + abs(a["y"] - b["y"])

    my_health = game_state.get("you", {}).get("health", 100)
    food_list = game_state.get("board", {}).get("food", [])
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
    hazard_damage_per_turn = get_hazard_damage_per_turn(game_state)
    turns_survivable = my_health // hazard_damage_per_turn

    # Classify safe moves by hazard status
    non_hazard_moves = [
        m for m in post_h2h_moves
        if (future_head_positions[m]["x"], future_head_positions[m]["y"]) not in hazard_coords
    ]
    hazard_moves = [
        m for m in post_h2h_moves
        if (future_head_positions[m]["x"], future_head_positions[m]["y"]) in hazard_coords
    ]

    # BFS Walkable Path Distance to Food (navigating around bodies/obstacles, dynamic for any board size)
    def find_food_distance_bfs(start_coord, target_food_coords):
        if not target_food_coords:
            return float("inf")
        start = (start_coord["x"], start_coord["y"])
        if start in target_food_coords:
            return 0
        visited = {start}
        queue = deque([(start[0], start[1], 0)])
        max_search_dist = board_width + board_height
        while queue:
            cx, cy, dist = queue.popleft()
            if dist >= max_search_dist:
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
        exit_distance_by_move = {
            m: bfs_distance_to_safe_tile(
                (future_head_positions[m]["x"], future_head_positions[m]["y"]),
                hazard_coords,
                all_obstacles,
                board_width,
                board_height,
            )
            for m in post_h2h_moves
        }
        best_exit_distance = (
            min(exit_distance_by_move.values())
            if exit_distance_by_move
            else float("inf")
        )

        # Life-saver check: Eating food resets health to 100 and buys survival time
        immediate_food = [
            m for m in post_h2h_moves
            if (future_head_positions[m]["x"], future_head_positions[m]["y"]) in all_food_coords
        ]
        if immediate_food and (my_health < 50 or turns_survivable <= best_exit_distance):
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
            finite_exit_moves = [
                m for m in post_h2h_moves
                if exit_distance_by_move.get(m, float("inf")) < float("inf")
            ]
            if finite_exit_moves:
                min_exit_dist = min(exit_distance_by_move[m] for m in finite_exit_moves)
                best_exit_moves = [
                    m for m in finite_exit_moves
                    if exit_distance_by_move[m] == min_exit_dist
                ]
                best_move = max(best_exit_moves, key=move_preference_key)
                print(f"MOVE {game_state['turn']}: DEEP IN STORM - Moving toward safe zone with {best_move} (Exit distance: {min_exit_dist})")
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
        exit_distance_by_hazard_move = {
            m: bfs_distance_to_safe_tile(
                (future_head_positions[m]["x"], future_head_positions[m]["y"]),
                hazard_coords,
                all_obstacles,
                board_width,
                board_height,
            )
            for m in hazard_moves
        }
        min_hazard_exit_distance = (
            min(exit_distance_by_hazard_move.values())
            if exit_distance_by_hazard_move
            else float("inf")
        )

        # Emergency starvation lifeline: If starving to death and food is on an adjacent hazard tile
        if my_health <= 25 or turns_survivable <= min_hazard_exit_distance:
            hazard_food_moves = [
                m for m in hazard_moves
                if (future_head_positions[m]["x"], future_head_positions[m]["y"]) in all_food_coords
            ]
            if hazard_food_moves:
                print(f"MOVE {game_state['turn']}: CRITICAL STARVATION (Health: {my_health}) NEAR STORM - Emergency hazard food lifeline activated!")
                candidate_moves.extend(hazard_food_moves)

        # If all non-hazard moves were blocked, fall back to hazard moves heading to center
        if not candidate_moves:
            if exit_distance_by_hazard_move:
                min_exit = min(exit_distance_by_hazard_move.values())
                candidate_moves = [
                    m for m in hazard_moves
                    if exit_distance_by_hazard_move[m] == min_exit
                ]
            else:
                candidate_moves = post_h2h_moves


        # In 1v1 near storm, if healthy, dominate area control safely inside non-hazard using Iterative Minimax
        if is_1v1 and my_health > 35 and candidate_moves:
            best_move, score, reached_depth, duration_ms, all_scores = select_best_minimax_move(
                candidate_moves, my_body_tuples, opp_body_tuples, all_food_coords,
                board_width, board_height, time_limit=0.140, turns_until_shrink=turns_until_shrink,
                opp_is_naive=opp_is_naive
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

    # NOTE: proactive Royale center-positioning is now handled by the
    # shrink-timing bias built into move_preference_key/open_space_preference
    # above (turns_until_shrink-based, precise, and blended as a soft score
    # bonus). An earlier hard-override version of this lived here, gated on
    # health + raw distance-from-center; it caused a real regression (all 4
    # self-play snakes beelining to center from turn 0 and colliding in an
    # unforced pile-up, confirmed via a real match with 0 hazards on the
    # board the entire game) and has been superseded, not just patched.

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
                board_width, board_height, time_limit=0.140, turns_until_shrink=turns_until_shrink,
                opp_is_naive=opp_is_naive
            )
            print(f"MOVE {game_state['turn']} (1v1 GROWTH ITERATIVE MINIMAX): Eating food with {best_move} (Score: {score:.1f}, Depth: {reached_depth}, Time: {duration_ms:.1f}ms)", flush=True)
            return {"move": best_move}

        # 3. Tactical Domination: Iterative Deepening Minimax with move ordering
        best_move, score, reached_depth, duration_ms, all_scores = select_best_minimax_move(
            candidate_moves, my_body_tuples, opp_body_tuples, all_food_coords,
            board_width, board_height, time_limit=0.140, turns_until_shrink=turns_until_shrink,
            opp_is_naive=opp_is_naive
        )
        print(f"MOVE {game_state['turn']} (1v1 ITERATIVE MINIMAX): Selected {best_move} (Score: {score:.1f}, Reached Depth: {reached_depth}, Time: {duration_ms:.1f}ms, Choices: {all_scores})", flush=True)
        return {"move": best_move}

    # MULTI-SNAKE LOGIC (Standard qualifying round with > 1 opponent)
    if target_foods:
        best_move = pick_food_move(candidate_moves, target_foods)
        print(f"MOVE {game_state['turn']}: SAFELY OUTSIDE HAZARD - Seeking food with {best_move} (Health: {my_health}, Room: {space_by_move[best_move]})")
        return {"move": best_move}

    # If no food on board, wander into maximum open space (with center bias if Royale shrink is approaching)
    def open_space_preference(m):
        score = float(space_by_move.get(m, 0))
        if turns_until_shrink <= 10:
            cand = future_head_positions[m]
            dist_to_center = abs(cand["x"] - center_coord["x"]) + abs(cand["y"] - center_coord["y"])
            max_c_dist = (board_width // 2) + (board_height // 2)
            c_closeness = (max_c_dist - dist_to_center) / max_c_dist if max_c_dist > 0 else 1.0
            urgency = (10 - max(1, turns_until_shrink) + 1) / 10.0
            score += c_closeness * 10.0 * urgency
        return score

    best_move = max(candidate_moves, key=open_space_preference)
    print(f"MOVE {game_state['turn']}: SAFELY OUTSIDE HAZARD - Wandering open space with {best_move}")
    return {"move": best_move}


# Start server when `python main.py` is run
if __name__ == "__main__":
    from server import run_server

    run_server({"info": info, "start": start, "move": move, "end": end})
