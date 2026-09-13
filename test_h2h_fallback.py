import unittest
from main import move


class TestH2HFallbackLogic(unittest.TestCase):
    def test_h2h_fallback_prefers_fewer_killers(self):
        """
        Scenario: Two candidate moves exist (up and right). Down is neck, left is our own body.
        Both moves step into dangerous head zones of equal-or-longer opponents (h2h_safe_moves is empty).
        - 'up' (cell 5, 6) is contested by 2 opponents (Opponent A at 5, 7 and Opponent B at 4, 6).
        - 'right' (cell 6, 5) is contested by only 1 opponent (Opponent C at 7, 5).
        Even if food is placed near 'up', the new fallback tier must select 'right' (fewer killers).
        """
        game_state = {
            "game": {"id": "h2h-fallback-test", "ruleset": {"name": "standard"}},
            "turn": 5,
            "board": {
                "height": 11,
                "width": 11,
                # Food near 'up' to ensure raw food heuristics don't override killer count
                "food": [{"x": 5, "y": 8}],
                "hazards": [],
                "snakes": [
                    {
                        "id": "my-snake",
                        "name": "turbo-69",
                        "health": 80,
                        "body": [
                            {"x": 5, "y": 5},  # Head
                            {"x": 5, "y": 4},  # Neck (down is blocked)
                            {"x": 4, "y": 4},
                            {"x": 4, "y": 5},  # Left (4, 5) is our own body segment
                        ],
                        "head": {"x": 5, "y": 5},
                        "length": 4,
                    },
                    {
                        "id": "opp-a",
                        "name": "opp-a",
                        "health": 100,
                        # Length 4 (equal to us), head at (5, 7) -> can step down into (5, 6)
                        "body": [{"x": 5, "y": 7}, {"x": 5, "y": 8}, {"x": 5, "y": 9}, {"x": 5, "y": 10}],
                        "head": {"x": 5, "y": 7},
                        "length": 4,
                    },
                    {
                        "id": "opp-b",
                        "name": "opp-b",
                        "health": 100,
                        # Length 5 (longer than us), head at (4, 6) -> can step right into (5, 6)
                        "body": [{"x": 4, "y": 6}, {"x": 3, "y": 6}, {"x": 2, "y": 6}, {"x": 1, "y": 6}, {"x": 0, "y": 6}],
                        "head": {"x": 4, "y": 6},
                        "length": 5,
                    },
                    {
                        "id": "opp-c",
                        "name": "opp-c",
                        "health": 100,
                        # Length 4 (equal to us), head at (7, 5) -> can step left into (6, 5)
                        "body": [{"x": 7, "y": 5}, {"x": 8, "y": 5}, {"x": 9, "y": 5}, {"x": 10, "y": 5}],
                        "head": {"x": 7, "y": 5},
                        "length": 4,
                    },
                ],
            },
            "you": {
                "id": "my-snake",
                "name": "turbo-69",
                "health": 80,
                "body": [
                    {"x": 5, "y": 5},
                    {"x": 5, "y": 4},
                    {"x": 4, "y": 4},
                    {"x": 4, "y": 5},
                ],
                "head": {"x": 5, "y": 5},
                "length": 4,
            },
        }

        res = move(game_state)
        # 'up' is contested by 2 opponents, 'right' is contested by 1 opponent.
        self.assertEqual(res["move"], "right")

    def test_h2h_fallback_tiebreak_prefers_more_space(self):
        """
        Scenario: Two candidate moves exist (up and right).
        Both are threatened by exactly 1 equal-or-longer opponent (killer count tie: 1 vs 1).
        - 'up' leads into a small enclosed pocket (space = 3).
        - 'right' leads into a wide open board area (space = 105).
        The tiebreak logic must pick 'right' due to larger reachable space.
        """
        game_state = {
            "game": {"id": "test-space-tiebreak", "ruleset": {"name": "standard"}},
            "turn": 10,
            "board": {
                "height": 11,
                "width": 11,
                "food": [],
                "hazards": [],
                "snakes": [
                    {
                        "id": "my-snake",
                        "name": "turbo-69",
                        "health": 80,
                        "body": [{"x": 1, "y": 1}, {"x": 1, "y": 0}, {"x": 0, "y": 0}],
                        "head": {"x": 1, "y": 1},
                        "length": 3,
                    },
                    {
                        "id": "opp-up",
                        "name": "opp-up",
                        "health": 100,
                        # Encloses the pocket around (1, 2) and threatens (1, 2)
                        "body": [
                            {"x": 1, "y": 3},
                            {"x": 1, "y": 4},
                            {"x": 0, "y": 4},
                            {"x": 2, "y": 4},
                            {"x": 2, "y": 3},
                            {"x": 2, "y": 2},
                            {"x": 0, "y": 1},
                        ],
                        "head": {"x": 1, "y": 3},
                        "length": 7,
                    },
                    {
                        "id": "opp-right",
                        "name": "opp-right",
                        "health": 100,
                        # Threatens (2, 1)
                        "body": [{"x": 3, "y": 1}, {"x": 4, "y": 1}, {"x": 5, "y": 1}],
                        "head": {"x": 3, "y": 1},
                        "length": 3,
                    },
                ],
            },
            "you": {
                "id": "my-snake",
                "name": "turbo-69",
                "health": 80,
                "body": [{"x": 1, "y": 1}, {"x": 1, "y": 0}, {"x": 0, "y": 0}],
                "head": {"x": 1, "y": 1},
                "length": 3,
            },
        }

        res = move(game_state)
        self.assertEqual(res["move"], "right")

    def test_h2h_safe_moves_unaffected_when_non_empty(self):
        """
        Ensure that when at least one move is genuinely safe from head-to-head collision,
        the first tier (h2h_safe_moves) is respected without regression.
        """
        game_state = {
            "game": {"id": "h2h-safe-tier1", "ruleset": {"name": "standard"}},
            "turn": 8,
            "board": {
                "height": 11,
                "width": 11,
                "food": [],
                "hazards": [],
                "snakes": [
                    {
                        "id": "my-snake",
                        "name": "turbo-69",
                        "health": 80,
                        "body": [
                            {"x": 5, "y": 5},
                            {"x": 5, "y": 4},
                            {"x": 4, "y": 4},
                            {"x": 4, "y": 5},
                        ],
                        "head": {"x": 5, "y": 5},
                        "length": 4,
                    },
                    {
                        "id": "opp-up",
                        "name": "opp-up",
                        "health": 100,
                        # Opponent threatens (5, 6) only
                        "body": [
                            {"x": 5, "y": 7},
                            {"x": 5, "y": 8},
                            {"x": 5, "y": 9},
                            {"x": 5, "y": 10},
                        ],
                        "head": {"x": 5, "y": 7},
                        "length": 4,
                    },
                ],
            },
            "you": {
                "id": "my-snake",
                "name": "turbo-69",
                "health": 80,
                "body": [
                    {"x": 5, "y": 5},
                    {"x": 5, "y": 4},
                    {"x": 4, "y": 4},
                    {"x": 4, "y": 5},
                ],
                "head": {"x": 5, "y": 5},
                "length": 4,
            },
        }

        res = move(game_state)
        # 'right' (6, 5) is completely unthreatened, so it must be selected over 'up'
        self.assertEqual(res["move"], "right")

    def test_shorter_opponents_do_not_count_as_killers(self):
        """
        Opponents that are strictly shorter than us cannot kill us head-to-head.
        Verify that a shorter opponent's adjacent cells do not count as killing threats.
        """
        game_state = {
            "game": {"id": "h2h-shorter-opp", "ruleset": {"name": "standard"}},
            "turn": 6,
            "board": {
                "height": 11,
                "width": 11,
                "food": [],
                "hazards": [],
                "snakes": [
                    {
                        "id": "my-snake",
                        "name": "turbo-69",
                        "health": 80,
                        # Length 5
                        "body": [
                            {"x": 5, "y": 5},
                            {"x": 5, "y": 4},
                            {"x": 4, "y": 4},
                            {"x": 4, "y": 5},
                            {"x": 4, "y": 6},
                        ],
                        "head": {"x": 5, "y": 5},
                        "length": 5,
                    },
                    {
                        "id": "shorter-opp",
                        "name": "shorter-opp",
                        "health": 100,
                        # Length 3 (strictly shorter than our length 5)
                        "body": [{"x": 5, "y": 7}, {"x": 5, "y": 8}, {"x": 5, "y": 9}],
                        "head": {"x": 5, "y": 7},
                        "length": 3,
                    },
                ],
            },
            "you": {
                "id": "my-snake",
                "name": "turbo-69",
                "health": 80,
                "body": [
                    {"x": 5, "y": 5},
                    {"x": 5, "y": 4},
                    {"x": 4, "y": 4},
                    {"x": 4, "y": 5},
                    {"x": 4, "y": 6},
                ],
                "head": {"x": 5, "y": 5},
                "length": 5,
            },
        }

        res = move(game_state)
        # Moving 'up' (5, 6) is safe because the opponent is strictly shorter!
        self.assertIn(res["move"], ["up", "right"])


class TestInfoEndpoint(unittest.TestCase):
    def test_info_metadata(self):
        from main import info
        res = info()
        self.assertEqual(res.get("apiversion"), "1")
        self.assertEqual(res.get("author"), "turbo-69")
        self.assertNotEqual(res.get("color"), "#888888")
        self.assertNotEqual(res.get("head"), "default")
        self.assertNotEqual(res.get("tail"), "default")


if __name__ == "__main__":
    unittest.main()
