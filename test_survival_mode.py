import unittest
from main import (
    check_survival_mode,
    move,
)


class TestSurvivalModeTriggers(unittest.TestCase):
    def test_trigger_when_shortest_among_multiple_snakes(self):
        # We have length 3, opponents have length 5, 6, 7
        alive_opponents = [
            {"id": "opp1", "body": [{"x": 1, "y": 1}] * 5},
            {"id": "opp2", "body": [{"x": 2, "y": 2}] * 6},
            {"id": "opp3", "body": [{"x": 3, "y": 3}] * 7},
        ]
        self.assertTrue(check_survival_mode(3, alive_opponents))

    def test_trigger_when_tied_shortest(self):
        # We have length 3, opponents have length 3, 5, 6
        alive_opponents = [
            {"id": "opp1", "body": [{"x": 1, "y": 1}] * 3},
            {"id": "opp2", "body": [{"x": 2, "y": 2}] * 5},
            {"id": "opp3", "body": [{"x": 3, "y": 3}] * 6},
        ]
        self.assertTrue(check_survival_mode(3, alive_opponents))

    def test_trigger_when_below_average_length_by_margin(self):
        # Opponents have lengths 7, 7, 7 (avg = 7). We have length 5 (more than 1 below avg)
        alive_opponents = [
            {"id": "opp1", "body": [{"x": 1, "y": 1}] * 7},
            {"id": "opp2", "body": [{"x": 2, "y": 2}] * 7},
            {"id": "opp3", "body": [{"x": 3, "y": 3}] * 7},
        ]
        self.assertTrue(check_survival_mode(5, alive_opponents))

    def test_no_trigger_when_longest(self):
        # We have length 8, opponents have length 4, 5, 6
        alive_opponents = [
            {"id": "opp1", "body": [{"x": 1, "y": 1}] * 4},
            {"id": "opp2", "body": [{"x": 2, "y": 2}] * 5},
            {"id": "opp3", "body": [{"x": 3, "y": 3}] * 6},
        ]
        self.assertFalse(check_survival_mode(8, alive_opponents))

    def test_no_trigger_when_comfortably_longer_than_shortest(self):
        # Opponents have lengths 3, 6, 8 (min=3, avg=5.67). We have length 7.
        # We are strictly longer than min(3) and above average.
        alive_opponents = [
            {"id": "opp1", "body": [{"x": 1, "y": 1}] * 3},
            {"id": "opp2", "body": [{"x": 2, "y": 2}] * 6},
            {"id": "opp3", "body": [{"x": 3, "y": 3}] * 8},
        ]
        self.assertFalse(check_survival_mode(7, alive_opponents))

    def test_no_trigger_when_no_opponents(self):
        self.assertFalse(check_survival_mode(3, []))


class TestSurvivalModeBehavior(unittest.TestCase):
    def test_steer_away_from_opponent_heads(self):
        # We are at (5, 5) with length 3.
        # Opponent is at (5, 7) with length 6 (moving down would get close to them).
        # Food is at (5, 2).
        # Candidate safe moves: 'down' (away from opponent, towards food), 'up' (towards opponent).
        game_state = {
            "game": {"id": "survival-test", "ruleset": {"name": "standard"}},
            "turn": 10,
            "board": {
                "height": 11,
                "width": 11,
                "food": [{"x": 5, "y": 2}],
                "hazards": [],
                "snakes": [
                    {
                        "id": "opp",
                        "name": "BigSnake",
                        "health": 90,
                        "body": [{"x": 5, "y": 7}, {"x": 5, "y": 8}, {"x": 5, "y": 9}, {"x": 5, "y": 10}],
                        "head": {"x": 5, "y": 7},
                        "length": 6,
                    },
                    {
                        "id": "me",
                        "name": "turbo-69",
                        "health": 90,
                        "body": [{"x": 5, "y": 5}, {"x": 4, "y": 5}, {"x": 3, "y": 5}],
                        "head": {"x": 5, "y": 5},
                        "length": 3,
                    },
                ],
            },
            "you": {
                "id": "me",
                "name": "turbo-69",
                "health": 90,
                "body": [{"x": 5, "y": 5}, {"x": 4, "y": 5}, {"x": 3, "y": 5}],
                "head": {"x": 5, "y": 5},
                "length": 3,
            },
        }
        res = move(game_state)
        # Should pick 'down' to gain distance from opponent at (5, 7) and approach food at (5, 2)
        self.assertEqual(res["move"], "down")

    def test_prioritize_distance_over_area_control(self):
        # Position where moving 'up' contests space closer to opponent (5, 7),
        # but moving 'down' keeps maximum distance buffer (steering away from threat).
        game_state = {
            "game": {"id": "buffer-over-area", "ruleset": {"name": "standard"}},
            "turn": 8,
            "board": {
                "height": 11,
                "width": 11,
                "food": [],  # No food so purely testing distance buffer & retreat
                "hazards": [],
                "snakes": [
                    {
                        "id": "opp",
                        "name": "Giant",
                        "health": 90,
                        "body": [{"x": 5, "y": 7}, {"x": 5, "y": 8}, {"x": 5, "y": 9}, {"x": 5, "y": 10}, {"x": 6, "y": 10}],
                        "head": {"x": 5, "y": 7},
                        "length": 5,
                    },
                    {
                        "id": "me",
                        "name": "turbo-69",
                        "health": 90,
                        "body": [{"x": 5, "y": 4}, {"x": 4, "y": 4}, {"x": 3, "y": 4}],
                        "head": {"x": 5, "y": 4},
                        "length": 3,
                    },
                ],
            },
            "you": {
                "id": "me",
                "name": "turbo-69",
                "health": 90,
                "body": [{"x": 5, "y": 4}, {"x": 4, "y": 4}, {"x": 3, "y": 4}],
                "head": {"x": 5, "y": 4},
                "length": 3,
            },
        }
        res = move(game_state)
        # In survival mode, moving 'down' keeps distance 4 from opponent (5, 7),
        # whereas moving 'up' to (5, 5) reduces distance to 2.
        self.assertEqual(res["move"], "down")

    def test_survival_mode_never_produces_unsafe_move(self):
        # We are at corner (0, 0), facing right (neck at (1, 0)).
        # Valid physical move is only 'up' (0, 1).
        # Even with an opponent nearby, it must strictly obey physical safety.
        game_state = {
            "game": {"id": "safety-test", "ruleset": {"name": "standard"}},
            "turn": 4,
            "board": {
                "height": 11,
                "width": 11,
                "food": [{"x": 5, "y": 5}],
                "hazards": [],
                "snakes": [
                    {
                        "id": "opp",
                        "name": "BigSnake",
                        "health": 90,
                        "body": [{"x": 0, "y": 3}, {"x": 0, "y": 4}, {"x": 0, "y": 5}, {"x": 0, "y": 6}],
                        "head": {"x": 0, "y": 3},
                        "length": 5,
                    },
                    {
                        "id": "me",
                        "name": "turbo-69",
                        "health": 90,
                        "body": [{"x": 0, "y": 0}, {"x": 1, "y": 0}, {"x": 2, "y": 0}],
                        "head": {"x": 0, "y": 0},
                        "length": 3,
                    },
                ],
            },
            "you": {
                "id": "me",
                "name": "turbo-69",
                "health": 90,
                "body": [{"x": 0, "y": 0}, {"x": 1, "y": 0}, {"x": 2, "y": 0}],
                "head": {"x": 0, "y": 0},
                "length": 3,
            },
        }
        res = move(game_state)
        self.assertEqual(res["move"], "up")


if __name__ == "__main__":
    unittest.main()
