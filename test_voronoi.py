import unittest
import time
from main import compute_voronoi_control, move


class TestVoronoiCore(unittest.TestCase):
    def test_symmetric_board(self):
        # 11x11 board, my head at (0, 5), opp head at (10, 5)
        # cand_head moves to (1, 5)
        board_width = 11
        board_height = 11
        cand_head = {"x": 1, "y": 5}
        opp_head = {"x": 10, "y": 5}
        obstacles = {(0, 5), (10, 5)}

        my_tiles, opp_tiles, score = compute_voronoi_control(
            cand_head, opp_head, board_width, board_height, obstacles
        )
        print(f"Symmetric test: My={my_tiles}, Opp={opp_tiles}, Score={score}")
        self.assertGreater(my_tiles, 0)
        self.assertGreater(opp_tiles, 0)
        # Moving to (1, 5) puts us 1 step closer to center than opponent at (10, 5)
        self.assertGreaterEqual(score, 0)

    def test_choke_point_cutoff(self):
        # 5x5 board. Wall of body segments from (2, 0) to (2, 3).
        # Choke point is (2, 4).
        board_width = 5
        board_height = 5
        obstacles = {(2, 0), (2, 1), (2, 2), (2, 3), (0, 4), (4, 4)}
        opp_head = {"x": 4, "y": 4}

        # Move A: Seize choke point at (2, 4)
        cand_head_a = {"x": 2, "y": 4}
        my_a, opp_a, score_a = compute_voronoi_control(
            cand_head_a, opp_head, board_width, board_height, obstacles
        )

        # Move B: Retreat away to (0, 3)
        cand_head_b = {"x": 0, "y": 3}
        my_b, opp_b, score_b = compute_voronoi_control(
            cand_head_b, opp_head, board_width, board_height, obstacles
        )

        print(f"Choke point seized: My={my_a}, Opp={opp_a}, Score={score_a}")
        print(f"Retreat: My={my_b}, Opp={opp_b}, Score={score_b}")

        # Seizing the choke point must yield a significantly higher relative score!
        self.assertGreater(score_a, score_b)
        self.assertGreater(score_a, 0)

    def test_performance(self):
        board_width = 19
        board_height = 19
        cand_head = {"x": 9, "y": 10}
        opp_head = {"x": 9, "y": 8}
        obstacles = {(i, 5) for i in range(15)}

        start = time.perf_counter()
        for _ in range(4):  # 4 candidate directions
            compute_voronoi_control(cand_head, opp_head, board_width, board_height, obstacles)
        duration_ms = (time.perf_counter() - start) * 1000
        print(f"4x 19x19 Voronoi evaluations took: {duration_ms:.2f} ms")
        self.assertLess(duration_ms, 30.0)


class TestVoronoiMoveIntegration(unittest.TestCase):
    def test_1v1_voronoi_prefers_area_control(self):
        """
        Verify that 1v1 move logic prefers the move that cuts off the opponent
        over a move that retreats into a dead end, even if food is nearby.
        """
        game_state = {
            "game": {"id": "test-game", "ruleset": {"name": "standard"}},
            "turn": 10,
            "board": {
                "height": 11,
                "width": 11,
                "food": [{"x": 0, "y": 0}],
                "hazards": [],
                "snakes": [
                    {
                        "id": "opponent",
                        "name": "Rival",
                        "health": 90,
                        "body": [{"x": 7, "y": 5}, {"x": 8, "y": 5}, {"x": 9, "y": 5}],
                        "head": {"x": 7, "y": 5},
                        "length": 3,
                    },
                    {
                        "id": "my-snake",
                        "name": "turbo-69",
                        "health": 85,
                        "body": [{"x": 5, "y": 5}, {"x": 4, "y": 5}, {"x": 3, "y": 5}],
                        "head": {"x": 5, "y": 5},
                        "length": 3,
                    },
                ],
            },
            "you": {
                "id": "my-snake",
                "name": "turbo-69",
                "health": 85,
                "body": [{"x": 5, "y": 5}, {"x": 4, "y": 5}, {"x": 3, "y": 5}],
                "head": {"x": 5, "y": 5},
                "length": 3,
            },
        }
        res = move(game_state)
        print(f"1v1 Duel Move Result: {res}")
        self.assertIn(res["move"], ["up", "down", "right"])
        # Should not retreat left into neck (4, 5)
        self.assertNotEqual(res["move"], "left")

    def test_1v1_hunger_seeks_food(self):
        """
        When health is low (<= 35), the snake must prioritize food seeking.
        """
        game_state = {
            "game": {"id": "test-game", "ruleset": {"name": "standard"}},
            "turn": 25,
            "board": {
                "height": 11,
                "width": 11,
                "food": [{"x": 5, "y": 6}],  # 1 step up
                "hazards": [],
                "snakes": [
                    {
                        "id": "opponent",
                        "name": "Rival",
                        "health": 80,
                        "body": [{"x": 9, "y": 9}, {"x": 9, "y": 8}, {"x": 9, "y": 7}],
                        "head": {"x": 9, "y": 9},
                        "length": 3,
                    },
                    {
                        "id": "my-snake",
                        "name": "turbo-69",
                        "health": 20,  # Starving!
                        "body": [{"x": 5, "y": 5}, {"x": 5, "y": 4}, {"x": 5, "y": 3}],
                        "head": {"x": 5, "y": 5},
                        "length": 3,
                    },
                ],
            },
            "you": {
                "id": "my-snake",
                "name": "turbo-69",
                "health": 20,
                "body": [{"x": 5, "y": 5}, {"x": 5, "y": 4}, {"x": 5, "y": 3}],
                "head": {"x": 5, "y": 5},
                "length": 3,
            },
        }
        res = move(game_state)
        print(f"Hunger Move Result: {res}")
        self.assertEqual(res["move"], "up")  # Eats food directly above

    def test_h2h_safety_overrides_voronoi(self):
        """
        If opponent is longer, head-to-head collision tile must be avoided
        even if it would have high Voronoi territory.
        """
        game_state = {
            "game": {"id": "test-game", "ruleset": {"name": "standard"}},
            "turn": 30,
            "board": {
                "height": 11,
                "width": 11,
                "food": [],
                "hazards": [],
                "snakes": [
                    {
                        "id": "opponent",
                        "name": "GiantRival",
                        "health": 90,
                        "body": [{"x": 5, "y": 7}, {"x": 5, "y": 8}, {"x": 5, "y": 9}, {"x": 5, "y": 10}],
                        "head": {"x": 5, "y": 7},
                        "length": 4,  # Longer than us (length 4 vs 3)
                    },
                    {
                        "id": "my-snake",
                        "name": "turbo-69",
                        "health": 80,
                        "body": [{"x": 5, "y": 5}, {"x": 4, "y": 5}, {"x": 3, "y": 5}],
                        "head": {"x": 5, "y": 5},
                        "length": 3,
                    },
                ],
            },
            "you": {
                "id": "my-snake",
                "name": "turbo-69",
                "health": 80,
                "body": [{"x": 5, "y": 5}, {"x": 4, "y": 5}, {"x": 3, "y": 5}],
                "head": {"x": 5, "y": 5},
                "length": 3,
            },
        }
        res = move(game_state)
        print(f"H2H Safety Result: {res}")
        # Moving 'up' would step onto (5, 6), directly adjacent to longer opponent at (5, 7)!
        self.assertNotEqual(res["move"], "up")

    def test_multiplayer_fallback(self):
        """
        With 3 opponents (>1 opponent), verify standard multi-snake logic executes cleanly.
        """
        game_state = {
            "game": {"id": "test-game", "ruleset": {"name": "standard"}},
            "turn": 1,
            "board": {
                "height": 11,
                "width": 11,
                "food": [{"x": 5, "y": 5}],
                "hazards": [],
                "snakes": [
                    {"id": "opp1", "health": 100, "body": [{"x": 1, "y": 1}, {"x": 1, "y": 0}], "head": {"x": 1, "y": 1}},
                    {"id": "opp2", "health": 100, "body": [{"x": 9, "y": 1}, {"x": 9, "y": 0}], "head": {"x": 9, "y": 1}},
                    {"id": "opp3", "health": 100, "body": [{"x": 1, "y": 9}, {"x": 1, "y": 10}], "head": {"x": 1, "y": 9}},
                    {"id": "my-snake", "health": 100, "body": [{"x": 9, "y": 9}, {"x": 9, "y": 10}], "head": {"x": 9, "y": 9}},
                ],
            },
            "you": {
                "id": "my-snake",
                "name": "turbo-69",
                "health": 100,
                "body": [{"x": 9, "y": 9}, {"x": 9, "y": 10}],
                "head": {"x": 9, "y": 9},
            },
        }
        res = move(game_state)
        print(f"Multiplayer Move Result: {res}")
        self.assertIn(res["move"], ["down", "left"])


if __name__ == "__main__":
    unittest.main()
