import unittest
from main import (
    get_shrink_interval,
    get_turns_until_shrink,
    evaluate_board_state,
    select_best_minimax_move,
    move,
)


class TestHazardTimingCountdown(unittest.TestCase):
    """
    Tests for tracking Royale hazard shrink interval and turn countdown.
    """
    def test_shrink_interval_default(self):
        # Empty or standard game_state defaults to 25
        self.assertEqual(get_shrink_interval({}), 25)
        self.assertEqual(get_shrink_interval({"game": {}}), 25)
        self.assertEqual(get_shrink_interval({"game": {"ruleset": {"name": "standard"}}}), 25)

    def test_shrink_interval_flat_setting(self):
        game_state = {
            "game": {
                "ruleset": {
                    "name": "royale",
                    "settings": {
                        "royale.shrinkEveryNTurns": 15
                    }
                }
            }
        }
        self.assertEqual(get_shrink_interval(game_state), 15)

    def test_shrink_interval_nested_setting(self):
        game_state = {
            "game": {
                "ruleset": {
                    "name": "royale",
                    "settings": {
                        "royale": {
                            "shrinkEveryNTurns": 30
                        }
                    }
                }
            }
        }
        self.assertEqual(get_shrink_interval(game_state), 30)

    def test_turns_until_shrink_countdown(self):
        # Interval = 25
        gs = {"game": {"ruleset": {"settings": {"royale": {"shrinkEveryNTurns": 25}}}}}

        # Turn 0: game start, 25 turns until first shrink
        gs["turn"] = 0
        self.assertEqual(get_turns_until_shrink(gs), 25)

        # Turn 1: 24 turns until shrink
        gs["turn"] = 1
        self.assertEqual(get_turns_until_shrink(gs), 24)

        # Turn 15: 10 turns until shrink (entering urgency window)
        gs["turn"] = 15
        self.assertEqual(get_turns_until_shrink(gs), 10)

        # Turn 20: 5 turns until shrink
        gs["turn"] = 20
        self.assertEqual(get_turns_until_shrink(gs), 5)

        # Turn 24: 1 turn until shrink
        gs["turn"] = 24
        self.assertEqual(get_turns_until_shrink(gs), 1)

        # Turn 25: shrink event just occurred on turn 25!
        # Next shrink is at turn 50 -> 25 turns remain (plenty of time)
        gs["turn"] = 25
        self.assertEqual(get_turns_until_shrink(gs), 25)

        # Turn 26: 24 turns remain
        gs["turn"] = 26
        self.assertEqual(get_turns_until_shrink(gs), 24)

        # Turn 48: 2 turns remain
        gs["turn"] = 48
        self.assertEqual(get_turns_until_shrink(gs), 2)

        # Turn 49: 1 turn remain
        gs["turn"] = 49
        self.assertEqual(get_turns_until_shrink(gs), 1)

        # Turn 50: shrink just occurred -> resets to 25
        gs["turn"] = 50
        self.assertEqual(get_turns_until_shrink(gs), 25)


class TestHazardTimingEvaluationBonus(unittest.TestCase):
    """
    Tests for center-bias bonus in evaluate_board_state as countdown gets close.
    """
    def test_zero_effect_when_shrink_is_distant_or_just_happened(self):
        # 11x11 board
        my_head = (5, 5) # Exact center
        my_body = [(5, 5), (5, 4), (5, 3)]
        opp_head = (0, 0) # Corner
        opp_body = [(0, 0), (0, 1), (0, 2)]

        base_score = evaluate_board_state(my_head, my_body, opp_head, opp_body, 11, 11, turns_until_shrink=None)

        # Distant countdown (e.g. 15 turns away) should equal base score
        score_distant = evaluate_board_state(my_head, my_body, opp_head, opp_body, 11, 11, turns_until_shrink=15)
        self.assertEqual(base_score, score_distant)

        # Just shrunk (25 turns away) should have zero bonus
        score_just_shrunk = evaluate_board_state(my_head, my_body, opp_head, opp_body, 11, 11, turns_until_shrink=25)
        self.assertEqual(base_score, score_just_shrunk)

    def test_center_bonus_scales_up_as_shrink_approaches(self):
        # Center snake vs Corner opponent
        my_head = (5, 5) # Center
        my_body = [(5, 5), (5, 4), (5, 3)]
        opp_head = (0, 0) # Corner
        opp_body = [(0, 0), (0, 1), (0, 2)]

        score_10 = evaluate_board_state(my_head, my_body, opp_head, opp_body, 11, 11, turns_until_shrink=10)
        score_8 = evaluate_board_state(my_head, my_body, opp_head, opp_body, 11, 11, turns_until_shrink=8)
        score_5 = evaluate_board_state(my_head, my_body, opp_head, opp_body, 11, 11, turns_until_shrink=5)
        score_2 = evaluate_board_state(my_head, my_body, opp_head, opp_body, 11, 11, turns_until_shrink=2)
        score_1 = evaluate_board_state(my_head, my_body, opp_head, opp_body, 11, 11, turns_until_shrink=1)

        # Score must strictly increase monotonically as the countdown drops
        self.assertGreater(score_8, score_10)
        self.assertGreater(score_5, score_8)
        self.assertGreater(score_2, score_5)
        self.assertGreater(score_1, score_2)

    def test_center_position_preferred_over_edge_as_shrink_nears(self):
        # Board state A: My snake at center (5, 5)
        # Board state B: My snake at edge (0, 5)
        opp_head = (5, 10)
        opp_body = [(5, 10), (5, 9), (5, 8)]

        my_center_head = (5, 5)
        my_center_body = [(5, 5), (4, 5), (3, 5)]

        my_edge_head = (0, 5)
        my_edge_body = [(0, 5), (1, 5), (2, 5)]

        # When shrink is imminent (1 turn away), center position must score significantly higher
        score_center = evaluate_board_state(my_center_head, my_center_body, opp_head, opp_body, 11, 11, turns_until_shrink=1)
        score_edge = evaluate_board_state(my_edge_head, my_edge_body, opp_head, opp_body, 11, 11, turns_until_shrink=1)

        self.assertGreater(score_center - score_edge, 4.0)


class TestHazardTimingMinimaxIntegration(unittest.TestCase):
    """
    Tests that Minimax lookahead actively chooses moves toward the center when shrink is near.
    """
    def test_minimax_prefers_inward_move_when_shrink_imminent(self):
        # Snake is at (1, 5). Moving "right" goes inward to (2, 5) towards center (5, 5).
        # Moving "left" goes to outer wall/edge at (0, 5).
        my_body = [(1, 5), (1, 4), (1, 3)]
        opp_body = [(9, 5), (9, 6), (9, 7)]
        candidate_moves = ["left", "right"]

        # When shrink is 1 turn away, moving inward ("right") should be chosen
        best_move, score, depth, duration, scores = select_best_minimax_move(
            candidate_moves, my_body, opp_body, set(), 11, 11,
            time_limit=0.100, turns_until_shrink=1
        )
        print(f"Hazard Timing Minimax Move: {best_move}, Choices: {scores}")
        self.assertEqual(best_move, "right")
        self.assertGreater(scores["right"], scores["left"])

    def test_move_function_in_royale_mode(self):
        # Test full move() endpoint with a Royale game_state on turn 24 (1 turn before turn 25 shrink)
        game_state = {
            "game": {
                "id": "royale-game-test",
                "ruleset": {
                    "name": "royale",
                    "settings": {
                        "royale": {"shrinkEveryNTurns": 25}
                    }
                }
            },
            "turn": 24, # 1 turn before shrink!
            "board": {
                "height": 11,
                "width": 11,
                "food": [{"x": 5, "y": 5}],
                "hazards": [],
                "snakes": [
                    {
                        "id": "rival",
                        "name": "RivalSnake",
                        "health": 95,
                        "body": [{"x": 9, "y": 5}, {"x": 9, "y": 6}, {"x": 9, "y": 7}],
                        "head": {"x": 9, "y": 5},
                        "length": 3,
                    },
                    {
                        "id": "my-snake",
                        "name": "turbo-69",
                        "health": 90,
                        "body": [{"x": 2, "y": 5}, {"x": 1, "y": 5}, {"x": 0, "y": 5}],
                        "head": {"x": 2, "y": 5},
                        "length": 3,
                    },
                ],
            },
            "you": {
                "id": "my-snake",
                "name": "turbo-69",
                "health": 90,
                "body": [{"x": 2, "y": 5}, {"x": 1, "y": 5}, {"x": 0, "y": 5}],
                "head": {"x": 2, "y": 5},
                "length": 3,
            },
        }

        res = move(game_state)
        print(f"Full Move Royale Result: {res}")
        self.assertIn(res["move"], ["up", "down", "right"])
        # Should not reverse left into neck
        self.assertNotEqual(res["move"], "left")


if __name__ == "__main__":
    unittest.main()
