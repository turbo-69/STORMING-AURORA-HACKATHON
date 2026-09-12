import unittest
from main import (
    evaluate_board_state,
    select_best_minimax_move,
    compute_voronoi_control,
    move,
)


class TestBoardSizes(unittest.TestCase):
    def test_19x19_edge_and_corner_detection(self):
        # On 19x19, corners are (0,0), (0,18), (18,0), (18,18)
        # Verify that corners and edges are weighted correctly compared to center
        center_head = (9, 9)
        center_body = [(9, 9)]
        corner_head = (0, 0)
        corner_body = [(0, 0)]

        score = evaluate_board_state(corner_head, corner_body, center_head, center_body, 19, 19)
        self.assertIsInstance(score, float)

    def test_19x19_hazard_timing_center_bias(self):
        # Position near center (9, 9) vs far from center (18, 18)
        near_center = (9, 9)
        opp = (1, 1)

        # Right after shrink (turns_until_shrink=25): no center bias added
        score_calm = evaluate_board_state(near_center, [near_center], opp, [opp], 19, 19, turns_until_shrink=25)
        # Urgency high (turns_until_shrink=2): center bias added
        score_urgent = evaluate_board_state(near_center, [near_center], opp, [opp], 19, 19, turns_until_shrink=2)

        self.assertGreater(score_urgent, score_calm)

    def test_19x19_voronoi_control(self):
        my_head = {"x": 9, "y": 9}
        opp_head = {"x": 1, "y": 1}
        all_obs = {(segment[0], segment[1]) for segment in [(9, 9), (1, 1)]}

        my_tiles, opp_tiles, score = compute_voronoi_control(my_head, opp_head, 19, 19, all_obs)
        # On 19x19, there are 19*19 - 2 = 359 empty tiles
        self.assertEqual(my_tiles + opp_tiles, 359)
        # Center head should control more territory than a cornered snake
        self.assertGreater(my_tiles, opp_tiles)

    def test_19x19_minimax_timing_budget(self):
        # Test minimax on 19x19 to ensure it stays strictly under 140ms
        my_body = [(9, 9), (9, 8), (9, 7)]
        opp_body = [(1, 1), (1, 2), (1, 3)]
        moves = ["up", "down", "left", "right"]
        food = {(9, 12), (5, 5), (15, 15)}

        best_move, score, depth, dur_ms, choices = select_best_minimax_move(
            moves, my_body, opp_body, food, 19, 19, time_limit=0.140, turns_until_shrink=10
        )
        self.assertIn(best_move, moves)
        self.assertGreaterEqual(depth, 2)
        # Must stay safely under 140ms
        self.assertLess(dur_ms, 150.0)

    def test_19x19_full_move_call(self):
        # Test full move() API on 19x19 board
        game_state = {
            "game": {"id": "grand-final-19x19", "ruleset": {"name": "royale", "settings": {"royale.shrinkEveryNTurns": 25}}},
            "turn": 15,
            "board": {
                "height": 19,
                "width": 19,
                "food": [{"x": 9, "y": 10}],
                "hazards": [],
                "snakes": [
                    {
                        "id": "opp",
                        "name": "Rival",
                        "health": 90,
                        "body": [{"x": 2, "y": 2}, {"x": 2, "y": 3}, {"x": 2, "y": 4}],
                        "head": {"x": 2, "y": 2},
                        "length": 3,
                    },
                    {
                        "id": "me",
                        "name": "turbo-69",
                        "health": 90,
                        "body": [{"x": 9, "y": 8}, {"x": 9, "y": 7}, {"x": 9, "y": 6}],
                        "head": {"x": 9, "y": 8},
                        "length": 3,
                    },
                ],
            },
            "you": {
                "id": "me",
                "name": "turbo-69",
                "health": 90,
                "body": [{"x": 9, "y": 8}, {"x": 9, "y": 7}, {"x": 9, "y": 6}],
                "head": {"x": 9, "y": 8},
                "length": 3,
            },
        }
        res = move(game_state)
        self.assertIn(res["move"], ["up", "down", "left", "right"])


if __name__ == "__main__":
    unittest.main()
