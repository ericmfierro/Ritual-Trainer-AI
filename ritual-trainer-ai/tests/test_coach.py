import json

from ritual_coach import FEW_SHOT, PERSONA_AND_RULES, payload_for_ai


def test_prompt_carries_evidence_and_missing_benchmark():
    text = payload_for_ai(
        {"stats": {"net_worth": 18000}, "economy_windows": [{"start_min": 10, "end_min": 15}]},
        {"available": False}, [], "Support", "Farming", {"net_worth_gain": 1200})
    values = json.loads(text)
    assert values["match_analysis"]["stats"]["net_worth"] == 18000
    assert values["high_rank_cohort"]["available"] is False
    assert values["selected_interval"]["net_worth_gain"] == 1200
    assert "never fabricate" in PERSONA_AND_RULES.lower()
    assert "EXAMPLE 1" in FEW_SHOT and "EXAMPLE 2" in FEW_SHOT
