import unittest
import main

class TestHazardSurvivalBudget(unittest.TestCase):
    # ---------------------------------------------------------
    # 1. get_hazard_damage_per_turn tests
    # ---------------------------------------------------------
    def test_default_damage(self):
        # When ruleset is empty or missing damagePerTurn setting, default is 15
        state_empty = {"game": {"ruleset": {}}}
        self.assertEqual(main.get_hazard_damage_per_turn(state_empty), 15)

        state_none = {}
        self.assertEqual(main.get_hazard_damage_per_turn(state_none), 15)

    def test_flat_setting(self):
        # Flat format: settings["damagePerTurn"]
        state = {
            "game": {
                "ruleset": {
                    "settings": {
                        "damagePerTurn": 20
                    }
                }
            }
        }
        self.assertEqual(main.get_hazard_damage_per_turn(state), 20)

    def test_nested_setting(self):
        # Nested format: settings["royale"]["damagePerTurn"]
        state = {
            "game": {
                "ruleset": {
                    "settings": {
                        "royale": {
                            "damagePerTurn": 25
                        }
                    }
                }
            }
        }
        self.assertEqual(main.get_hazard_damage_per_turn(state), 25)

    # ---------------------------------------------------------
    # 2. bfs_distance_to_safe_tile tests
    # ---------------------------------------------------------
    def test_already_safe(self):
        # start_coord not in hazard_coords returns 0
        hazards = {(0, 0), (0, 1)}
        obstacles = set()
        dist = main.bfs_distance_to_safe_tile((5, 5), hazards, obstacles, 11, 11)
        self.assertEqual(dist, 0)

    def test_simple_distance(self):
        # (1, 1) and all its 1-step neighbors are hazards; 2-step neighbors are safe.
        # Shortest distance from (1, 1) to safe tile is 2.
        hazards = {(1, 1), (1, 0), (1, 2), (0, 1), (2, 1)}
        obstacles = set()
        dist = main.bfs_distance_to_safe_tile((1, 1), hazards, obstacles, 5, 5)
        self.assertEqual(dist, 2)

    def test_unreachable_all_hazard(self):
        # Entire 3x3 board is hazard tiles; no safe tile reachable -> float("inf")
        hazards = {(x, y) for x in range(3) for y in range(3)}
        obstacles = set()
        dist = main.bfs_distance_to_safe_tile((1, 1), hazards, obstacles, 3, 3)
        self.assertEqual(dist, float("inf"))

    def test_obstacles_forcing_longer_path(self):
        # On a 3x3 board, only (2, 1) is a safe tile; all other tiles are hazard.
        # Direct path from (0, 1) to (2, 1) through (1, 1) takes 2 steps (Manhattan distance).
        # An obstacle at (1, 1) blocks the direct path, forcing detour through (0, 0)->(1, 0)->(2, 0)->(2, 1) [4 steps].
        hazards = {(x, y) for x in range(3) for y in range(3) if (x, y) != (2, 1)}
        obstacles = {(1, 1)}
        dist = main.bfs_distance_to_safe_tile((0, 1), hazards, obstacles, 3, 3)
        self.assertEqual(dist, 4)

    # ---------------------------------------------------------
    # 3. move() integration tests
    # ---------------------------------------------------------
    def test_move_triggers_food_lifeline_when_budget_insufficient(self):
        # In CASE 1 (in hazard): health is 55 (above the old 50 threshold).
        # Hazard damage is 15 -> turns_survivable = 55 // 15 = 3.
        # Safe tiles are 4 steps away.
        # Immediate food is available at (0, 1).
        # Since turns_survivable (3) <= best_exit_distance (4), time budget triggers food lifeline!
        hazards = [
            {"x": x, "y": y}
            for x in range(11)
            for y in range(11)
            if y < 5  # rows 0-4 are hazard, row 5+ is safe
        ]
        game_state = {
            "game": {
                "id": "budget-test-1",
                "ruleset": {"name": "royale", "settings": {"damagePerTurn": 15}}
            },
            "turn": 10,
            "board": {
                "height": 11,
                "width": 11,
                "food": [{"x": 0, "y": 1}],
                "hazards": hazards,
                "snakes": [
                    {
                        "id": "me",
                        "name": "turbo-69",
                        "health": 55,
                        "body": [{"x": 0, "y": 0}, {"x": 1, "y": 0}, {"x": 2, "y": 0}],
                        "head": {"x": 0, "y": 0},
                        "length": 3
                    }
                ]
            },
            "you": {
                "id": "me",
                "name": "turbo-69",
                "health": 55,
                "body": [{"x": 0, "y": 0}, {"x": 1, "y": 0}, {"x": 2, "y": 0}],
                "head": {"x": 0, "y": 0},
                "length": 3
            }
        }
        res = main.move(game_state)
        # Moving "up" reaches (0, 1) which immediately eats food and resets health to 100
        self.assertEqual(res["move"], "up")

    def test_move_does_not_falsely_trigger_when_budget_sufficient(self):
        # In CASE 1 (in hazard): health is 75 (above 50).
        # Hazard damage is 15 -> turns_survivable = 75 // 15 = 5.
        # Safe tile is only 1 step away at (1, 2) when head is at (1, 1).
        # Food is at (0, 1) in hazard.
        # Since turns_survivable (5) > best_exit_distance (0 for candidate move up to row 2),
        # snake should escape to safe zone ("up" to (1, 2)) rather than eating food in hazard ("left" to (0, 1)).
        hazards = [
            {"x": x, "y": y}
            for x in range(11)
            for y in range(11)
            if y <= 1  # rows 0 and 1 are hazard, row 2+ is safe
        ]
        game_state = {
            "game": {
                "id": "budget-test-2",
                "ruleset": {"name": "royale", "settings": {"damagePerTurn": 15}}
            },
            "turn": 10,
            "board": {
                "height": 11,
                "width": 11,
                "food": [{"x": 0, "y": 1}],
                "hazards": hazards,
                "snakes": [
                    {
                        "id": "me",
                        "name": "turbo-69",
                        "health": 75,
                        "body": [{"x": 1, "y": 1}, {"x": 1, "y": 0}, {"x": 2, "y": 0}],
                        "head": {"x": 1, "y": 1},
                        "length": 3
                    }
                ]
            },
            "you": {
                "id": "me",
                "name": "turbo-69",
                "health": 75,
                "body": [{"x": 1, "y": 1}, {"x": 1, "y": 0}, {"x": 2, "y": 0}],
                "head": {"x": 1, "y": 1},
                "length": 3
            }
        }
        res = main.move(game_state)
        # Should escape directly to safe zone (up to (1, 2))
        self.assertEqual(res["move"], "up")


if __name__ == "__main__":
    unittest.main()
