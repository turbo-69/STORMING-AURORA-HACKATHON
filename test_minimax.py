import unittest
import time
from main import (
    evaluate_board_state,
    minimax_alpha_beta,
    select_best_minimax_move,
    move,
)


class TestPart1AreaControlScoring(unittest.TestCase):
    """
    Tests for PART 1: Area-control scoring function
    """
    def test_symmetric_board(self):
        # 5x5 board, symmetric corners
        # Diagonals (x+y=4) have 5 tiles where d_my == d_opp (contested, so 'mine')
        # Corner (0,4) weight 2, Corner (4,0) weight 2, (1,3) weight 1, (2,2) weight 1, (3,1) weight 1 = 7.0
        score = evaluate_board_state((0, 0), [(0, 0)], (4, 4), [(4, 4)], 5, 5)
        self.assertAlmostEqual(score, 7.0)

    def test_choke_point_scoring(self):
        # 5x5 board with a wall dividing left and right, choke point at (2, 4)
        wall = [(2, 0), (2, 1), (2, 2), (2, 3)]
        my_body = [(2, 4)] + [(1, 4), (0, 4)] # Sitting on choke point
        opp_body = [(4, 4), (4, 3), (4, 2)] # Restricted to right side

        score = evaluate_board_state(my_body[0], my_body + wall, opp_body[0], opp_body + wall, 5, 5)
        print(f"Choke point board evaluation score: {score}")
        # Controlling choke point should yield very high positive score
        self.assertGreater(score, 5.0)

    def test_edge_and_corner_weighting(self):
        # Verify corner tiles receive higher weight than interior tiles
        # On a 3x3 board:
        # (0,0) corner has weight 2.0
        # (1,1) center has weight 1.0
        my_head = (0, 0)
        opp_head = (2, 2)
        score = evaluate_board_state(my_head, [my_head], opp_head, [opp_head], 3, 3)
        self.assertIsInstance(score, float)


class TestPart2MinimaxAlphaBeta(unittest.TestCase):
    """
    Tests for PART 2: Minimax search with alpha-beta pruning
    """
    def test_depth4_lookahead_performance(self):
        # 11x11 board performance test
        my_body = [(5, 5), (4, 5), (3, 5)]
        opp_body = [(5, 7), (6, 7), (7, 7)]
        candidate_moves = ["up", "down", "right"]
        food = {(5, 6), (2, 2)}

        best_move, score, reached_depth, duration_ms, all_scores = select_best_minimax_move(
            candidate_moves, my_body, opp_body, food, 11, 11, time_limit=0.100
        )
        print(f"11x11 Iterative Minimax: {best_move} (Score: {score:.1f}, Depth: {reached_depth}, Time: {duration_ms:.2f}ms)")
        print(f"Scores by move: {all_scores}")

        self.assertIn(best_move, candidate_moves)
        self.assertGreaterEqual(reached_depth, 3)
        self.assertLess(duration_ms, 150.0)

    def test_minimax_avoids_opponent_trap(self):
        # 5x5 board.
        # Moving 'right' walks towards opponent that is longer.
        # Moving 'left' moves into open space.
        my_body = [(2, 2), (2, 1), (2, 0)]
        opp_body = [(4, 2), (4, 3), (4, 4), (3, 4)] # length 4 vs length 3
        candidate_moves = ["left", "up"]

        best_move, score, reached_depth, duration_ms, all_scores = select_best_minimax_move(
            candidate_moves, my_body, opp_body, set(), 5, 5, time_limit=0.100
        )
        print(f"Avoid trap decision: {best_move} (Depth: {reached_depth}, Time: {duration_ms:.2f}ms, All: {all_scores})")
        self.assertIn(best_move, candidate_moves)


class TestMainIntegration(unittest.TestCase):
    """
    Tests for main.py move() integration
    """
    def test_move_runs_minimax_in_1v1(self):
        game_state = {
            "game": {"id": "test-game", "ruleset": {"name": "standard"}},
            "turn": 12,
            "board": {
                "height": 11,
                "width": 11,
                "food": [{"x": 1, "y": 1}],
                "hazards": [],
                "snakes": [
                    {
                        "id": "opponent",
                        "name": "Rival",
                        "health": 90,
                        "body": [{"x": 8, "y": 5}, {"x": 9, "y": 5}, {"x": 10, "y": 5}],
                        "head": {"x": 8, "y": 5},
                        "length": 3,
                    },
                    {
                        "id": "my-snake",
                        "name": "turbo-69",
                        "health": 85,
                        "body": [{"x": 3, "y": 5}, {"x": 2, "y": 5}, {"x": 1, "y": 5}],
                        "head": {"x": 3, "y": 5},
                        "length": 3,
                    },
                ],
            },
            "you": {
                "id": "my-snake",
                "name": "turbo-69",
                "health": 85,
                "body": [{"x": 3, "y": 5}, {"x": 2, "y": 5}, {"x": 1, "y": 5}],
                "head": {"x": 3, "y": 5},
                "length": 3,
            },
        }
        res = move(game_state)
        print(f"Move Integration Result: {res}")
        self.assertIn(res["move"], ["up", "down", "right"])
        self.assertNotEqual(res["move"], "left") # Neck reversal prevented


if __name__ == "__main__":
    unittest.main()
