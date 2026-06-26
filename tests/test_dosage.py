"""dosage.py: the edit-budget tiers and the tells that drive them."""
import dosage


def test_manufactured_persuasion_forces_rewrite():
    draft = ("Hi Dana, there's a real, time-limited window here and I'd hate for you to "
             "miss the better pricing. Evidence beats another nudge.")
    tells = dosage.scan(draft, "Customers / external")
    assert any("MANUFACTURED" in name for name, _ in tells)
    tier, _ = dosage.tier(tells, draft)
    assert tier == "REWRITE"


def test_three_asterisk_labels_force_rewrite():
    draft = "*Round:* four million *Board:* one seat *Timeline:* this week"
    tells = dosage.scan(draft, "Investors / board")
    tier, _ = dosage.tier(tells, draft)
    assert tier == "REWRITE"


def test_near_clean_team_draft_is_surgical():
    draft = "before standup - auth bug's in the token refresh path, not login. lmk"
    tells = dosage.scan(draft, "Team")
    tier, _ = dosage.tier(tells, draft)
    assert tier == "SURGICAL"


def test_greeting_is_flagged():
    tells = dosage.scan("Hi Sam, here's the number.", "Investors / board")
    assert any(name == "greeting" for name, _ in tells)


def test_em_dash_native_in_team_not_flagged():
    draft = "we ship friday — no blockers"
    assert not any("em-dash" in name for name, _ in dosage.scan(draft, "Team"))
    assert any("em-dash" in name for name, _ in dosage.scan(draft, "Customers / external"))
