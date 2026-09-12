import unittest
from main import (
    check_survival_mode,
    check_dominance_mode,
    determine_behavior_mode,
    move,
)


class TestDominanceModeTriggers(unittest.TestCase):
    def test_dominance_triggers_when_longest_with_margin(self):
        # We have length 8. Opponents have lengths 4, 5, 5 (max=5, avg=4.67, diff=3.33 >= 2.0)
        alive_opponents = [
            {"id": "opp1", "body": [{"x": 1, "y": 1}] * 4},
            {"id": "opp2", "body": [{"x": 2, "y": 2}] * 5},
            {"id": "opp3", "body": [{"x": 3, "y": 3}] * 5},
        ]
        self.assertTrue(check_dominance_mode(8, alive_opponents))
        self.assertEqual(determine_behavior_mode(8, alive_opponents), "DOMINANCE")

    def test_dominance_does_not_trigger_when_barely_longer(self):
        # We have length 6. Opponents have lengths 5, 5, 5 (max=5, avg=5.0, diff=1.0 < 2.0)
        alive_opponents = [
            {"id": "opp1", "body": [{"x": 1, "y": 1}] * 5},
            {"id": "opp2", "body": [{"x": 2, "y": 2}] * 5},
            {"id": "opp3", "body": [{"x": 3, "y": 3}] * 5},
        ]
        self.assertFalse(check_dominance_mode(6, alive_opponents))
        # Should be DEFAULT (neutral) mode
        self.assertEqual(determine_behavior_mode(6, alive_opponents), "DEFAULT")

    def test_dominance_does_not_trigger_when_tied_or_shorter(self):
        # Tied with leader: length 7 vs 7, 5, 4 (diff=7 - 5.33 = 1.67 < 2.0)
        alive_opponents = [
            {"id": "opp1", "body": [{"x": 1, "y": 1}] * 7},
            {"id": "opp2", "body": [{"x": 2, "y": 2}] * 5},
            {"id": "opp3", "body": [{"x": 3, "y": 3}] * 4},
        ]
        self.assertFalse(check_dominance_mode(7, alive_opponents))

        # Strictly shorter than leader: length 6 vs 8, 4, 4
        alive_opponents2 = [
            {"id": "opp1", "body": [{"x": 1, "y": 1}] * 8},
            {"id": "opp2", "body": [{"x": 2, "y": 2}] * 4},
            {"id": "opp3", "body": [{"x": 3, "y": 3}] * 4},
        ]
        self.assertFalse(check_dominance_mode(6, alive_opponents2))

    def test_no_trigger_when_no_opponents(self):
        self.assertFalse(check_dominance_mode(5, []))

    def test_mutual_exclusivity(self):
        # Rigorous cross-test across various length configurations
        test_cases = [
            # (my_len, [opp_lengths])
            (3, [3, 4, 5]),
            (3, [3, 3, 3]),
            (4, [3, 4, 5]),
            (5, [3, 4, 5]),
            (6, [3, 4, 5]),
            (7, [3, 4, 5]),
            (10, [4, 5, 6]),
            (2, [5, 6, 7]),
            (5, [5]),
            (7, [5]),
            (12, [3, 4, 5, 6]),
        ]
        for my_l, opp_lens in test_cases:
            alive = [{"id": f"opp{i}", "body": [{"x": 0, "y": 0}] * l} for i, l in enumerate(opp_lens)]
            is_surv = check_survival_mode(my_l, alive)
            is_dom = check_dominance_mode(my_l, alive)
            mode = determine_behavior_mode(my_l, alive)

            # Rule: Survival and Dominance must NEVER both be True simultaneously
            self.assertFalse(is_surv and is_dom, f"Collision detected for len {my_l} vs {opp_lens}")
            # Mode must match
            if is_surv:
                self.assertEqual(mode, "SURVIVAL")
            elif is_dom:
                self.assertEqual(mode, "DOMINANCE")
            else:
                self.assertEqual(mode, "DEFAULT")


class TestDominanceModeBehavior(unittest.TestCase):
    def test_dominance_prioritizes_territory_denial_over_food(self):
        # We are length 8 (Dominance Mode vs opponent length 4).
        # We have health 90 (not hungry).
        # Food is to the left at (4, 5).
        # Moving 'right' towards (6, 5) pinches the opponent (at (8, 5)) against the right wall.
        # In Dominance Mode, the snake should pinch the opponent rather than chasing unnecessary food!
        game_state = {
            "game": {"id": "dominance-test", "ruleset": {"name": "standard"}},
            "turn": 20,
            "board": {
                "height": 11,
                "width": 11,
                "food": [{"x": 4, "y": 5}],
                "hazards": [],
                "snakes": [
                    {
                        "id": "opp",
                        "name": "Rival",
                        "health": 90,
                        "body": [{"x": 8, "y": 5}, {"x": 8, "y": 4}, {"x": 8, "y": 3}, {"x": 8, "y": 2}],
                        "head": {"x": 8, "y": 5},
                        "length": 4,
                    },
                    {
                        "id": "me",
                        "name": "turbo-69",
                        "health": 90,
                        "body": [
                            {"x": 5, "y": 5}, {"x": 5, "y": 6}, {"x": 5, "y": 7},
                            {"x": 5, "y": 8}, {"x": 5, "y": 9}, {"x": 5, "y": 10},
                            {"x": 4, "y": 10}, {"x": 3, "y": 10}
                        ],
                        "head": {"x": 5, "y": 5},
                        "length": 8,
                    },
                ],
            },
            "you": {
                "id": "me",
                "name": "turbo-69",
                "health": 90,
                "body": [
                    {"x": 5, "y": 5}, {"x": 5, "y": 6}, {"x": 5, "y": 7},
                    {"x": 5, "y": 8}, {"x": 5, "y": 9}, {"x": 5, "y": 10},
                    {"x": 4, "y": 10}, {"x": 3, "y": 10}
                ],
                "head": {"x": 5, "y": 5},
                "length": 8,
            },
        }
        res = move(game_state)
        # Should squeeze the opponent rightward or down, rather than retreating left into food
        self.assertIn(res["move"], ["right", "down"])

    def test_dominance_respects_all_safety_checks(self):
        # We are in Dominance Mode, cornered at (0, 0) with wall down/left and neck at (1, 0).
        # Only valid move is 'up'. Even in Dominance Mode, it must NEVER hit a wall or neck.
        game_state = {
            "game": {"id": "safety-test", "ruleset": {"name": "standard"}},
            "turn": 10,
            "board": {
                "height": 11,
                "width": 11,
                "food": [{"x": 5, "y": 5}],
                "hazards": [],
                "snakes": [
                    {
                        "id": "opp",
                        "name": "SmallOpp",
                        "health": 90,
                        "body": [{"x": 10, "y": 10}, {"x": 10, "y": 9}],
                        "head": {"x": 10, "y": 10},
                        "length": 2,
                    },
                    {
                        "id": "me",
                        "name": "turbo-69",
                        "health": 90,
                        "body": [
                            {"x": 0, "y": 0}, {"x": 1, "y": 0}, {"x": 2, "y": 0},
                            {"x": 3, "y": 0}, {"x": 4, "y": 0}, {"x": 5, "y": 0}
                        ],
                        "head": {"x": 0, "y": 0},
                        "length": 6,
                    },
                ],
            },
            "you": {
                "id": "me",
                "name": "turbo-69",
                "health": 90,
                "body": [
                    {"x": 0, "y": 0}, {"x": 1, "y": 0}, {"x": 2, "y": 0},
                    {"x": 3, "y": 0}, {"x": 4, "y": 0}, {"x": 5, "y": 0}
                ],
                "head": {"x": 0, "y": 0},
                "length": 6,
            },
        }
        res = move(game_state)
        self.assertEqual(res["move"], "up")


if __name__ == "__main__":
    unittest.main()
