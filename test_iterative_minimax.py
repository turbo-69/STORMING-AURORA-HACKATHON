import unittest
import time
from collections import deque
import typing

class SearchTimeout(Exception):
    pass

DIRECTIONS = {
    "up": (0, 1),
    "down": (0, -1),
    "left": (-1, 0),
    "right": (1, 0),
}

def evaluate_board_state(
    my_head: typing.Tuple[int, int],
    my_body: typing.List[typing.Tuple[int, int]],
    opp_head: typing.Tuple[int, int],
    opp_body: typing.List[typing.Tuple[int, int]],
    board_width: int,
    board_height: int,
) -> float:
    all_obstacles = set(my_body) | set(opp_body)

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


def get_legal_sim_moves(head, body, other_body, board_width, board_height):
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
    Orders MAX moves: PV move first, then descending by 1-ply evaluation.
    """
    if not moves:
        return []
    if len(moves) == 1:
        return moves

    my_head = my_body[0]
    opp_head = opp_body[0]

    def score_move(m):
        dx, dy = DIRECTIONS[m]
        new_head = (my_head[0] + dx, my_head[1] + dy)
        new_body = [new_head] + (my_body if new_head in food else my_body[:-1])
        return evaluate_board_state(new_head, new_body, opp_head, opp_body, board_width, board_height)

    # Sort descending
    sorted_moves = sorted(moves, key=score_move, reverse=True)

    # If pv_move is given, promote it to the front
    if pv_move and pv_move in sorted_moves:
        sorted_moves.remove(pv_move)
        sorted_moves.insert(0, pv_move)

    return sorted_moves


def order_moves_min(moves, opp_body, my_body, food, board_width, board_height):
    """
    Orders MIN moves: ascending by our board score (best for opponent first).
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

    # Sort ascending (opponent wants lowest score for us)
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
    if time.perf_counter() - start_time > time_limit:
        raise SearchTimeout()

    if depth == 0:
        return evaluate_board_state(
            my_body[0], my_body, opp_body[0], opp_body, board_width, board_height
        )

    my_head = my_body[0]
    opp_head = opp_body[0]

    if is_maximizing:
        legal_moves = get_legal_sim_moves(my_head, my_body, opp_body, board_width, board_height)
        if not legal_moves:
            return -100000.0 + depth

        # Move ordering at MAX
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
                break
        return max_eval

    else:
        legal_moves = get_legal_sim_moves(opp_head, opp_body, my_body, board_width, board_height)
        if not legal_moves:
            return 100000.0 - depth

        # Move ordering at MIN
        ordered_moves = order_moves_min(legal_moves, opp_body, my_body, food, board_width, board_height)

        min_eval = float("inf")
        for m in ordered_moves:
            dx, dy = DIRECTIONS[m]
            new_head = (opp_head[0] + dx, opp_head[1] + dy)

            if new_head == my_head:
                if len(my_body) > len(opp_body):
                    score = 100000.0 - depth
                else:
                    score = -100000.0 + depth
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
                break
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
        # If elapsed exceeds 40% of time limit or >90ms, don't risk starting next depth
        if elapsed > time_limit * 0.40 or elapsed > 0.090:
            break

        try:
            # Move ordering at root: PV move first, then sorted candidate moves
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

            # Successfully completed this depth
            best_overall_move = depth_best_move
            best_overall_score = depth_best_score
            reached_depth = depth
            scores_by_move = current_depth_scores
            pv_move = depth_best_move

            if best_overall_score >= 90000:
                break

        except SearchTimeout:
            break

    duration_ms = (time.perf_counter() - start_time) * 1000
    return best_overall_move, best_overall_score, reached_depth, duration_ms, scores_by_move


class TestIterativeMinimaxSuite(unittest.TestCase):
    def test_iterative_deepening_progression(self):
        my_body = [(5, 5), (4, 5), (3, 5)]
        opp_body = [(5, 7), (6, 7), (7, 7)]
        candidate_moves = ["up", "down", "right"]
        food = {(5, 6)}

        move, score, depth, dur_ms, scores = select_best_minimax_move(
            candidate_moves, my_body, opp_body, food, 11, 11, time_limit=0.350
        )
        print(f"\nIterative Deepening Result: Move={move}, Score={score}, Depth={depth}, Time={dur_ms:.1f}ms")
        print(f"Scores by move at depth {depth}: {scores}")

        self.assertIn(move, candidate_moves)
        self.assertGreaterEqual(depth, 4) # Should easily reach at least depth 4+
        self.assertLess(dur_ms, 360.0) # Within safe 350ms budget

    def test_emergency_timeout_fallback(self):
        # Even with an impossibly tiny time limit (0.001s), it must return a valid move!
        my_body = [(5, 5), (4, 5), (3, 5)]
        opp_body = [(5, 7), (6, 7), (7, 7)]
        candidate_moves = ["up", "down", "right"]

        move, score, depth, dur_ms, scores = select_best_minimax_move(
            candidate_moves, my_body, opp_body, set(), 11, 11, time_limit=0.001
        )
        print(f"Emergency Timeout Fallback: Move={move}, Depth={depth}, Time={dur_ms:.2f}ms")
        self.assertIn(move, candidate_moves)

    def test_move_ordering_efficiency(self):
        my_body = [(2, 2), (2, 1), (2, 0)]
        opp_body = [(4, 2), (4, 3), (4, 4)]
        candidate_moves = ["up", "left", "right"]
        ordered = order_moves_max(candidate_moves, my_body, opp_body, set(), 5, 5, pv_move="up")
        self.assertEqual(ordered[0], "up") # PV move correctly placed first


if __name__ == "__main__":
    unittest.main()
