import unittest
from main import (
    reset_opponent_tracker,
    update_opponent_tracker,
    evaluate_board_state,
    select_best_minimax_move,
    move,
)


class TestOpponentModelingTracker(unittest.TestCase):
    def setUp(self):
        reset_opponent_tracker("test-game-1")

    def test_insufficient_history_returns_false(self):
        # Turns 0, 1, 2: should return False (pattern unclear / not enough data)
        gs = {"game": {"id": "test-game-1"}, "turn": 0}
        food = [(5, 5)]

        # Turn 0 (Initial observation)
        self.assertFalse(update_opponent_tracker(gs, (1, 5), food))

        # Turn 1: Opponent moves closer to food: (2, 5) from (1, 5) -> dist decreased from 4 to 3
        gs["turn"] = 1
        self.assertFalse(update_opponent_tracker(gs, (2, 5), food))

        # Turn 2: Opponent moves closer to food: (3, 5) from (2, 5) -> dist decreased from 3 to 2
        gs["turn"] = 2
        self.assertFalse(update_opponent_tracker(gs, (3, 5), food))

    def test_naive_food_seeker_detected_after_3_moves(self):
        # 3 consecutive food-seeking moves
        gs = {"game": {"id": "test-game-1"}, "turn": 0}
        food = [(5, 5)]

        update_opponent_tracker(gs, (1, 5), food) # Turn 0 init
        gs["turn"] = 1
        update_opponent_tracker(gs, (2, 5), food) # Move 1: closer
        gs["turn"] = 2
        update_opponent_tracker(gs, (3, 5), food) # Move 2: closer
        gs["turn"] = 3
        is_naive = update_opponent_tracker(gs, (4, 5), food) # Move 3: closer
        self.assertTrue(is_naive)

    def test_sophisticated_or_wandering_opponent_not_classified_naive(self):
        # Opponent moves away from food or takes lateral moves
        gs = {"game": {"id": "test-game-1"}, "turn": 0}
        food = [(5, 5)]

        update_opponent_tracker(gs, (1, 5), food) # Turn 0 init
        gs["turn"] = 1
        update_opponent_tracker(gs, (1, 6), food) # Lateral move: dist from (1,5) was 4, dist from (1,6) is 5 (farther!)
        gs["turn"] = 2
        update_opponent_tracker(gs, (1, 7), food) # Farther away
        gs["turn"] = 3
        is_naive = update_opponent_tracker(gs, (2, 7), food)
        self.assertFalse(is_naive)

    def test_game_reset_on_new_game_id(self):
        gs1 = {"game": {"id": "game-A"}, "turn": 0}
        food = [(5, 5)]
        update_opponent_tracker(gs1, (1, 5), food)
        update_opponent_tracker(gs1, (2, 5), food)
        update_opponent_tracker(gs1, (3, 5), food)
        update_opponent_tracker(gs1, (4, 5), food)

        # Now start new game B: should reset history and return False
        gs2 = {"game": {"id": "game-B"}, "turn": 0}
        self.assertFalse(update_opponent_tracker(gs2, (1, 5), food))

    def test_fail_safe_on_corrupt_data(self):
        # None or invalid game state should never crash and safely return False
        self.assertFalse(update_opponent_tracker({}, None, []))
        self.assertFalse(update_opponent_tracker({"game": None}, (0, 0), None))


class TestOpponentModelingEvaluation(unittest.TestCase):
    def test_aggression_multiplier_applied_when_naive_and_ahead(self):
        # Board where we are ahead
        my_head = (4, 4)
        my_body = [(4, 4), (4, 3), (4, 2)]
        opp_head = (0, 0)
        opp_body = [(0, 0), (0, 1), (0, 2)]

        score_standard = evaluate_board_state(my_head, my_body, opp_head, opp_body, 11, 11, opp_is_naive=False)
        score_aggressive = evaluate_board_state(my_head, my_body, opp_head, opp_body, 11, 11, opp_is_naive=True)

        self.assertGreater(score_standard, 0.0)
        self.assertGreater(score_aggressive, score_standard)

    def test_no_inflation_when_behind_or_tied(self):
        # Board where we are trapped/behind: opponent controls majority of space
        my_head = (0, 0)
        my_body = [(0, 0), (0, 1), (1, 0)]
        opp_head = (2, 2)
        opp_body = [(2, 2), (2, 3), (3, 2)]

        score_standard = evaluate_board_state(my_head, my_body, opp_head, opp_body, 5, 5, opp_is_naive=False)
        score_naive = evaluate_board_state(my_head, my_body, opp_head, opp_body, 5, 5, opp_is_naive=True)

        # When score is negative (behind), aggression multiplier must NOT inflate
        self.assertLess(score_standard, 0.0)
        self.assertAlmostEqual(score_standard, score_naive)


class TestOpponentModelingMinimaxIntegration(unittest.TestCase):
    def test_select_best_minimax_move_with_opp_is_naive(self):
        my_body = [(5, 5), (5, 4), (5, 3)]
        opp_body = [(1, 5), (1, 4), (1, 3)]
        candidate_moves = ["up", "down", "left", "right"]

        best_move, score, depth, duration, scores = select_best_minimax_move(
            candidate_moves, my_body, opp_body, set(), 11, 11,
            time_limit=0.140, opp_is_naive=True
        )
        self.assertIn(best_move, candidate_moves)
        self.assertLess(duration, 150.0)

    def test_full_move_integration(self):
        game_state = {
            "game": {"id": "test-opponent-modeling-game", "ruleset": {"name": "standard"}},
            "turn": 3,
            "board": {
                "height": 11,
                "width": 11,
                "food": [{"x": 5, "y": 5}],
                "hazards": [],
                "snakes": [
                    {
                        "id": "opp",
                        "name": "Rival",
                        "health": 90,
                        "body": [{"x": 1, "y": 5}, {"x": 1, "y": 4}, {"x": 1, "y": 3}],
                        "head": {"x": 1, "y": 5},
                        "length": 3,
                    },
                    {
                        "id": "me",
                        "name": "turbo-69",
                        "health": 90,
                        "body": [{"x": 5, "y": 2}, {"x": 5, "y": 1}, {"x": 5, "y": 0}],
                        "head": {"x": 5, "y": 2},
                        "length": 3,
                    },
                ],
            },
            "you": {
                "id": "me",
                "name": "turbo-69",
                "health": 90,
                "body": [{"x": 5, "y": 2}, {"x": 5, "y": 1}, {"x": 5, "y": 0}],
                "head": {"x": 5, "y": 2},
                "length": 3,
            },
        }
        res = move(game_state)
        self.assertIn(res["move"], ["up", "left", "right"])


if __name__ == "__main__":
    unittest.main()
