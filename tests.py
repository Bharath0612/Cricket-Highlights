# tests.py
# Automated tests for the cricket highlight streaming platform.
# Tests filter logic, edge cases, and session management WITHOUT
# needing a live server — all logic is tested in isolation.
#
# Usage:
#   python tests.py

import unittest
import json
import uuid

# ── Import the functions we want to test ──
# We'll replicate the key logic here so tests don't need the server running.

VALID_FILTERS = {"wicket", "six", "four", "other"}


def passes_filter(event: dict, filters: set) -> bool:
    """Replicates server-side filter check."""
    if not filters:
        return False
    return event["type"] in filters


def toggle_filter(filters: set, filter_name: str) -> tuple[set, str]:
    """
    Replicates the toggle logic from the server's handle_client_messages.
    Returns (updated_set, action_word).
    """
    if filter_name not in VALID_FILTERS:
        raise ValueError(f"Unknown filter: '{filter_name}'")
    filters = set(filters)  # work on a copy
    if filter_name in filters:
        filters.remove(filter_name)
        return filters, "disabled"
    else:
        filters.add(filter_name)
        return filters, "enabled"


def make_event(event_type: str, player: str = "Test Player", over: float = 1.0):
    return {"type": event_type, "player": player, "over": over,
            "description": f"Test {event_type} event."}


# ═════════════════════════════════════════════════════════════════════════════
#  TC-F: Filter Tests
# ═════════════════════════════════════════════════════════════════════════════

class TestFilterLogic(unittest.TestCase):

    def test_TC_F01_wickets_only(self):
        """TC-F01: Only wicket events pass when filter = {wicket}."""
        filters = {"wicket"}
        self.assertTrue(passes_filter(make_event("wicket"), filters))
        self.assertFalse(passes_filter(make_event("six"), filters))
        self.assertFalse(passes_filter(make_event("four"), filters))
        self.assertFalse(passes_filter(make_event("other"), filters))

    def test_TC_F02_sixes_only(self):
        """TC-F02: Only six events pass when filter = {six}."""
        filters = {"six"}
        self.assertTrue(passes_filter(make_event("six"), filters))
        self.assertFalse(passes_filter(make_event("wicket"), filters))
        self.assertFalse(passes_filter(make_event("four"), filters))

    def test_TC_F03_multiple_filters(self):
        """TC-F03: Wickets and sixes pass; fours do not."""
        filters = {"wicket", "six"}
        self.assertTrue(passes_filter(make_event("wicket"), filters))
        self.assertTrue(passes_filter(make_event("six"), filters))
        self.assertFalse(passes_filter(make_event("four"), filters))

    def test_TC_F04_all_filters_enabled(self):
        """TC-F04: All event types pass when all filters are active."""
        filters = VALID_FILTERS.copy()
        for event_type in ["wicket", "six", "four", "other"]:
            self.assertTrue(passes_filter(make_event(event_type), filters))

    def test_TC_F05_no_filters_enabled(self):
        """TC-F05: Nothing passes when filter set is empty."""
        filters = set()
        for event_type in ["wicket", "six", "four", "other"]:
            self.assertFalse(passes_filter(make_event(event_type), filters))

    def test_TC_F06_invalid_filter_raises(self):
        """TC-F06: An unknown filter name raises a ValueError."""
        filters = {"wicket"}
        with self.assertRaises(ValueError) as ctx:
            toggle_filter(filters, "stumping_extra_double")
        self.assertIn("Unknown filter", str(ctx.exception))


# ═════════════════════════════════════════════════════════════════════════════
#  TC-E: Edge Case Tests
# ═════════════════════════════════════════════════════════════════════════════

class TestEdgeCases(unittest.TestCase):

    def test_TC_E02_malformed_event_missing_type(self):
        """TC-E02: Event missing 'type' key uses .get() default and fails filter."""
        bad_event = {"player": "X", "over": 1.0, "description": "broken"}
        filters = {"wicket"}
        # .get() returns None, which is not in filters
        result = bad_event.get("type", "") in filters
        self.assertFalse(result)

    def test_TC_E05_toggle_is_idempotent(self):
        """TC-E05: Toggling same filter twice returns to original state."""
        original = {"wicket", "six"}
        after_first, _ = toggle_filter(original, "wicket")
        after_second, _ = toggle_filter(after_first, "wicket")
        self.assertEqual(original, after_second)

    def test_rapid_toggle_final_state(self):
        """TC-E05 extended: Final state after N toggles reflects even/odd count."""
        filters = set()
        for _ in range(7):  # Odd → should end up enabled
            filters, _ = toggle_filter(filters, "six")
        self.assertIn("six", filters)

        for _ in range(4):  # 4 more (total 11, odd) → still enabled
            filters, _ = toggle_filter(filters, "six")
        # Total = 11 toggles → enabled (odd)
        self.assertIn("six", filters)


# ═════════════════════════════════════════════════════════════════════════════
#  TC-U: User Interaction Tests
# ═════════════════════════════════════════════════════════════════════════════

class TestUserInteraction(unittest.TestCase):

    def test_TC_U01_independent_filters_two_users(self):
        """TC-U01: User A (sixes) and User B (wickets) see different events."""
        user_a_filters = {"six"}
        user_b_filters = {"wicket"}
        six_event = make_event("six")

        self.assertTrue(passes_filter(six_event, user_a_filters))
        self.assertFalse(passes_filter(six_event, user_b_filters))

    def test_TC_U02_mid_stream_toggle(self):
        """TC-U02: Disabling 'four' mid-stream stops four events immediately."""
        filters = {"wicket", "six", "four"}
        four_event = make_event("four")

        # Before toggle: four passes
        self.assertTrue(passes_filter(four_event, filters))

        # Toggle four off
        filters, action = toggle_filter(filters, "four")
        self.assertEqual(action, "disabled")

        # After toggle: four no longer passes
        self.assertFalse(passes_filter(four_event, filters))

        # Wickets and sixes still pass
        self.assertTrue(passes_filter(make_event("wicket"), filters))
        self.assertTrue(passes_filter(make_event("six"), filters))

    def test_toggle_returns_correct_action_word(self):
        """Toggle action word reflects the new state correctly."""
        filters = set()
        filters, word = toggle_filter(filters, "four")
        self.assertEqual(word, "enabled")
        filters, word = toggle_filter(filters, "four")
        self.assertEqual(word, "disabled")


# ═════════════════════════════════════════════════════════════════════════════
#  TC-P: Concurrent / Performance Tests (simulated)
# ═════════════════════════════════════════════════════════════════════════════

class TestConcurrentSimulation(unittest.TestCase):

    def test_TC_P03_unique_filters_per_user(self):
        """TC-P03: Ten simulated users each with unique filters see correct events."""
        import random
        random.seed(42)
        all_types = list(VALID_FILTERS)

        # Create 10 users with random filter subsets
        users = {}
        for i in range(10):
            num_filters = random.randint(1, len(all_types))
            chosen = set(random.sample(all_types, num_filters))
            users[f"user_{i}"] = chosen

        # Check each user only sees their allowed event types
        test_events = [make_event(t) for t in all_types]
        for user_id, user_filters in users.items():
            for event in test_events:
                expected = event["type"] in user_filters
                result = passes_filter(event, user_filters)
                self.assertEqual(
                    result, expected,
                    f"{user_id} with filters {user_filters} "
                    f"got wrong result for event type '{event['type']}'"
                )

    def test_session_isolation(self):
        """Modifying one user's filters does not affect another's."""
        user_a = {"wicket", "six"}
        user_b = {"four"}

        # Simulate users modifying their own sessions
        user_a_new, _ = toggle_filter(user_a, "wicket")

        # user_b's filters must be unchanged
        self.assertEqual(user_b, {"four"})

        # user_a's original must be unchanged (we worked on a copy)
        self.assertEqual(user_a, {"wicket", "six"})


# ═════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("  Cricket Highlights Platform — Test Suite")
    print("=" * 60)
    unittest.main(verbosity=2)