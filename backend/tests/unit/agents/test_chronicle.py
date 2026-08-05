"""Chronicle narrative-memory tests (T23)."""

from app.agents.chronicle import ActorState, Chronicle, ChronicleEntry


def _entry(month: int, event_id: str, actors: list[str], title: str = "T") -> ChronicleEntry:
    return ChronicleEntry(
        month=month, event_id=event_id, title=title, actors=actors, summary="summary"
    )


def test_add_entry_creates_actor_rows() -> None:
    chronicle = Chronicle()
    chronicle.add_entry(_entry(4, "evt_1", ["Competitor X"]))
    actor = chronicle.get_actor("Competitor X")
    assert actor is not None
    assert actor.first_seen_month == 4
    assert actor.last_seen_month == 4


def test_actor_last_seen_updates() -> None:
    chronicle = Chronicle()
    chronicle.add_entry(_entry(4, "evt_1", ["Competitor X"]))
    chronicle.add_entry(_entry(8, "evt_2", ["Competitor X"]))
    actor = chronicle.get_actor("Competitor X")
    assert actor is not None
    assert actor.first_seen_month == 4
    assert actor.last_seen_month == 8


def test_entries_newest_first_in_summary() -> None:
    chronicle = Chronicle()
    chronicle.add_entry(_entry(4, "evt_1", ["A"], title="First"))
    chronicle.add_entry(_entry(8, "evt_2", ["A"], title="Second"))
    summary = chronicle.to_prompt_summary()
    assert summary.index("Second") < summary.index("First")
    assert "ACTORS" in summary


def test_summary_truncation() -> None:
    chronicle = Chronicle()
    for i in range(50):
        chronicle.add_entry(_entry(i, f"evt_{i}", ["A"], title=f"Event {i}"))
    summary = chronicle.to_prompt_summary(max_chars=500)
    assert len(summary) <= 500
    assert "(truncated)" in summary


def test_round_trip_lossless() -> None:
    chronicle = Chronicle()
    chronicle.add_entry(_entry(4, "evt_1", ["Competitor X"], title="Launch"))
    chronicle.add_entry(
        ChronicleEntry(
            month=6,
            event_id="evt_2",
            title="Churn",
            actors=["Competitor X", "Founder"],
            summary="s",
            chosen_option_id="B",
        )
    )
    restored = Chronicle.from_dict(chronicle.to_dict())
    assert restored.to_dict() == chronicle.to_dict()
    assert restored.get_actor("Founder") is not None


def test_actor_kind_preserved() -> None:
    chronicle = Chronicle(actors={"X": ActorState("X", "competitor", 1, 1)})
    restored = Chronicle.from_dict(chronicle.to_dict())
    assert restored.get_actor("X") is not None
    assert restored.get_actor("X").kind == "competitor"
