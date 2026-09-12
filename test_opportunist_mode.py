import unittest
from main import (
    check_survival_mode,
    check_dominance_mode,
    check_opportunist_mode,
    determine_behavior_mode,
    select_opportunist_mode_move,
    move,
)

def make_dummy_snake(snake_id: str, length: int, head_x: int = 5, head_y: int = 5):
    body = [{"x": head_x, "y": head_y + i} for i in range(length)]
    return {
        "id": snake_id,
        "name": snake_id,
        "health": 100,
        "body": body,
        "head": body[0],
        "length": length,
    }

class TestOpportunistModeTriggers(unittest.TestCase):
    """
    Test suite for Opportunist Mode trigger conditions and dynamic transitions.
    """

    def test_opportunist_mode_triggers_with_3_snakes_midpack(self):
        """
        (a) Opportunist Mode triggers correctly with 3+ snakes and no clear length advantage.
        My snake: 6
        Opponents: 8, 5
        Neither shortest (opp2 is 5) nor longest with margin (opp1 is 8).
        """
        opponents = [
            make_dummy_snake("opp1", 8, head_x=1, head_y=1),
            make_dummy_snake("opp2", 5, head_x=9, head_y=9),
        ]
        my_len = 6
        self.assertFalse(check_survival_mode(my_len, opponents))
        self.assertFalse(check_dominance_mode(my_len, opponents))
        self.assertTrue(check_opportunist_mode(my_len, opponents))
        self.assertEqual(determine_behavior_mode(my_len, opponents), "OPPORTUNIST")

    def test_opportunist_mode_triggers_with_4_snakes(self):
        """
        Opportunist Mode triggers with 4 alive snakes when mid-pack.
        My snake: 6
        Opponents: 7, 6, 5
        """
        opponents = [
            make_dummy_snake("opp1", 7),
            make_dummy_snake("opp2", 6),
            make_dummy_snake("opp3", 5),
        ]
        my_len = 6
        self.assertFalse(check_survival_mode(my_len, opponents))
        self.assertFalse(check_dominance_mode(my_len, opponents))
        self.assertTrue(check_opportunist_mode(my_len, opponents))
        self.assertEqual(determine_behavior_mode(my_len, opponents), "OPPORTUNIST")

    def test_does_not_trigger_with_only_2_snakes_alive(self):
        """
        (b) Does NOT trigger with only 2 snakes alive (1v1 duel), even if mid-pack/close.
        """
        # 1v1 where my length is 6 and opponent is 5 (Dominance needs margin >= 2.0, so margin 1.0 is DEFAULT)
        opponents_1v1 = [make_dummy_snake("opp1", 5)]
        my_len = 6
        self.assertFalse(check_survival_mode(my_len, opponents_1v1))
        self.assertFalse(check_dominance_mode(my_len, opponents_1v1))
        self.assertFalse(check_opportunist_mode(my_len, opponents_1v1))
        self.assertEqual(determine_behavior_mode(my_len, opponents_1v1), "DEFAULT")

    def test_does_not_trigger_when_survival_mode_active_in_3_snakes(self):
        """
        In 3+ snakes, if my snake is shortest, SURVIVAL mode must trigger instead of Opportunist.
        """
        opponents = [
            make_dummy_snake("opp1", 8),
            make_dummy_snake("opp2", 7),
        ]
        my_len = 4  # Strictly shortest
        self.assertTrue(check_survival_mode(my_len, opponents))
        self.assertFalse(check_opportunist_mode(my_len, opponents))
        self.assertEqual(determine_behavior_mode(my_len, opponents), "SURVIVAL")

    def test_does_not_trigger_when_dominance_mode_active_in_3_snakes(self):
        """
        In 3+ snakes, if my snake is longest with margin >= 2.0, DOMINANCE must trigger instead.
        """
        opponents = [
            make_dummy_snake("opp1", 5),
            make_dummy_snake("opp2", 4),
        ]
        my_len = 8  # Average is 4.5, margin is 3.5 >= 2.0
        self.assertTrue(check_dominance_mode(my_len, opponents))
        self.assertFalse(check_opportunist_mode(my_len, opponents))
        self.assertEqual(determine_behavior_mode(my_len, opponents), "DOMINANCE")

    def test_dynamic_exit_when_snake_count_drops_to_2(self):
        """
        (c) Correctly exits Opportunist Mode when snake count drops to 2 (1 opponent remaining).
        """
        my_len = 6
        # Start with 3 snakes: Opp1 (8), Opp2 (4) -> Mid-pack -> OPPORTUNIST
        opps_3 = [
            make_dummy_snake("opp1", 8),
            make_dummy_snake("opp2", 4),
        ]
        self.assertEqual(determine_behavior_mode(my_len, opps_3), "OPPORTUNIST")

        # Scenario A: Opp2 dies, leaving only Opp1 (8)
        # My length 6 vs Opp1 8 -> Shortest in 1v1 -> Exits to SURVIVAL
        opps_survival = [make_dummy_snake("opp1", 8)]
        self.assertEqual(determine_behavior_mode(my_len, opps_survival), "SURVIVAL")

        # Scenario B: Opp1 dies, leaving only Opp2 (4)
        # My length 6 vs Opp2 4 -> Longest with margin 2.0 in 1v1 -> Exits to DOMINANCE
        opps_dominance = [make_dummy_snake("opp2", 4)]
        self.assertEqual(determine_behavior_mode(my_len, opps_dominance), "DOMINANCE")

        # Scenario C: Opponent is length 5 (margin 1.0)
        # Exits to DEFAULT
        opps_default = [make_dummy_snake("opp_close", 5)]
        self.assertEqual(determine_behavior_mode(my_len, opps_default), "DEFAULT")


class TestFourWayMutualExclusivity(unittest.TestCase):
    """
    (d) 4-way mutual exclusivity across all modes confirmed with no overlaps.
    """

    def test_four_way_mutual_exclusivity_matrix(self):
        cases = [
            # (my_len, opp_lengths, expected_mode)
            (3, [3, 3], "SURVIVAL"),        # 3 snakes, tied shortest -> SURVIVAL
            (3, [5, 6], "SURVIVAL"),        # 3 snakes, strictly shortest -> SURVIVAL
            (6, [8, 4], "OPPORTUNIST"),     # 3 snakes, mid-pack -> OPPORTUNIST
            (6, [6, 5], "OPPORTUNIST"),     # 3 snakes, tied longest without margin (avg 5.5, margin 0.5 < 2.0) -> OPPORTUNIST
            (9, [5, 4], "DOMINANCE"),       # 3 snakes, longest with margin (margin 4.5 >= 2.0) -> DOMINANCE
            (3, [3], "SURVIVAL"),           # 2 snakes (1v1), tied shortest -> SURVIVAL
            (3, [5], "SURVIVAL"),           # 2 snakes (1v1), shortest -> SURVIVAL
            (5, [4], "DEFAULT"),            # 2 snakes (1v1), margin 1.0 (< 2.0) -> DEFAULT
            (7, [4], "DOMINANCE"),          # 2 snakes (1v1), margin 3.0 (>= 2.0) -> DOMINANCE
        ]

        valid_modes = {"SURVIVAL", "DOMINANCE", "OPPORTUNIST", "DEFAULT"}
        for my_len, opp_lens, expected in cases:
            opponents = [make_dummy_snake(f"opp_{i}", l) for i, l in enumerate(opp_lens)]
            mode = determine_behavior_mode(my_len, opponents)
            self.assertIn(mode, valid_modes)
            self.assertEqual(
                mode, expected,
                f"Failed for my_len={my_len}, opp_lens={opp_lens}: expected {expected}, got {mode}"
            )


class TestOpportunistModeBehavior(unittest.TestCase):
    """
    Behavior tests for Opportunist Mode:
    - Avoids congested clusters of opponents
    - Refuses voluntary head-to-head contests against shorter snakes
    - Respects boundaries and body collisions
    """

    def test_opportunist_avoids_cluster_and_prefers_peripheral_space(self):
        """
        Opponents are clustered at (2, 2) and (3, 2).
        Candidate moves:
        - 'left' moves closer to (1, 5) towards the cluster
        - 'right' moves away towards open perimeter (7, 5)
        Snake must prefer 'right' away from the cluster centroid.
        """
        future_head_positions = {
            "left": {"x": 3, "y": 5},
            "right": {"x": 5, "y": 5},
        }
        space_by_move = {"left": 40, "right": 40}
        alive_opponents = [
            make_dummy_snake("opp1", 7, head_x=1, head_y=5),
            make_dummy_snake("opp2", 5, head_x=2, head_y=6),
        ]
        all_obstacles = set()
        hazard_coords = set()
        target_foods = set()

        chosen_move = select_opportunist_mode_move(
            candidate_moves=["left", "right"],
            future_head_positions=future_head_positions,
            space_by_move=space_by_move,
            alive_opponents=alive_opponents,
            all_obstacles=all_obstacles,
            board_width=11,
            board_height=11,
            my_health=90,
            target_foods=target_foods,
            hazard_coords=hazard_coords,
            turns_until_shrink=25,
            find_food_distance_bfs_fn=lambda c, f: float("inf"),
        )
        self.assertEqual(chosen_move, "right")

    def test_opportunist_avoids_initiating_head_contest_against_shorter_snake(self):
        """
        In Opportunist mode, even if an opponent is shorter, our snake refuses to step
        into its adjacent strike zone unless forced, letting others fight.
        """
        future_head_positions = {
            "up": {"x": 5, "y": 6},     # Steps adjacent to opp head at (5, 7)
            "right": {"x": 6, "y": 5},  # Safe open tile away from any head
        }
        space_by_move = {"up": 50, "right": 50}
        # Opponent is shorter (length 4 vs our length 6), but we refuse to contest
        alive_opponents = [
            make_dummy_snake("opp1", 4, head_x=5, head_y=7),
            make_dummy_snake("opp2", 7, head_x=9, head_y=9),
        ]
        all_obstacles = set()
        hazard_coords = set()
        target_foods = set()

        chosen_move = select_opportunist_mode_move(
            candidate_moves=["up", "right"],
            future_head_positions=future_head_positions,
            space_by_move=space_by_move,
            alive_opponents=alive_opponents,
            all_obstacles=all_obstacles,
            board_width=11,
            board_height=11,
            my_health=90,
            target_foods=target_foods,
            hazard_coords=hazard_coords,
            turns_until_shrink=25,
            find_food_distance_bfs_fn=lambda c, f: float("inf"),
        )
        self.assertEqual(chosen_move, "right")

    def test_opportunist_mode_respects_all_safety_checks_in_move(self):
        """
        Full move() integration check: walls and bodies are strictly filtered out.
        """
        game_state = {
            "game": {"id": "test-game", "ruleset": {"name": "standard"}},
            "turn": 10,
            "board": {
                "height": 11,
                "width": 11,
                "food": [{"x": 5, "y": 5}],
                "hazards": [],
                "snakes": [
                    {
                        "id": "you",
                        "name": "turbo-69",
                        "health": 90,
                        "body": [{"x": 0, "y": 5}, {"x": 0, "y": 4}, {"x": 0, "y": 3}, {"x": 0, "y": 2}, {"x": 0, "y": 1}, {"x": 1, "y": 1}],
                        "head": {"x": 0, "y": 5},
                        "length": 6,
                    },
                    {
                        "id": "opp1",
                        "name": "BigOpp",
                        "health": 90,
                        "body": [{"x": 3, "y": 5}, {"x": 3, "y": 4}, {"x": 3, "y": 3}, {"x": 3, "y": 2}, {"x": 3, "y": 1}, {"x": 3, "y": 0}, {"x": 4, "y": 0}],
                        "head": {"x": 3, "y": 5},
                        "length": 7,
                    },
                    {
                        "id": "opp2",
                        "name": "SmallOpp",
                        "health": 90,
                        "body": [{"x": 8, "y": 8}, {"x": 8, "y": 7}, {"x": 8, "y": 6}, {"x": 8, "y": 5}],
                        "head": {"x": 8, "y": 8},
                        "length": 4,
                    },
                ],
            },
            "you": {
                "id": "you",
                "name": "turbo-69",
                "health": 90,
                "body": [{"x": 0, "y": 5}, {"x": 0, "y": 4}, {"x": 0, "y": 3}, {"x": 0, "y": 2}, {"x": 0, "y": 1}, {"x": 1, "y": 1}],
                "head": {"x": 0, "y": 5},
                "length": 6,
            },
        }

        # Head is at (0, 5), neck is at (0, 4) -> 'down' is neck, 'left' is wall (x=0)
        # Safe moves are only 'up' or 'right'
        result = move(game_state)
        self.assertIn(result["move"], ["up", "right"])

if __name__ == "__main__":
    unittest.main()
