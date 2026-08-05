"""Narrative memory — pure Python, no LLM (spec §13 constraint 4).

Tracks actors across the simulation timeline so a competitor introduced in
Month 4 behaves consistently in Month 8. JSON-serializable for persistence.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ActorState:
    name: str
    kind: str
    first_seen_month: int
    last_seen_month: int
    notes: list[str] = field(default_factory=list)


@dataclass
class ChronicleEntry:
    month: int
    event_id: str
    title: str
    actors: list[str]
    summary: str
    chosen_option_id: str | None = None


class Chronicle:
    """Ordered event log + actor roster for narrative continuity."""

    def __init__(
        self,
        actors: dict[str, ActorState] | None = None,
        entries: list[ChronicleEntry] | None = None,
    ) -> None:
        self.actors: dict[str, ActorState] = actors or {}
        self.entries: list[ChronicleEntry] = entries or []

    def add_entry(self, entry: ChronicleEntry) -> None:
        """Record an entry, auto-creating/updating actor rows for every actor."""
        self.entries.append(entry)
        for name in entry.actors:
            actor = self.actors.get(name)
            if actor is None:
                self.actors[name] = ActorState(
                    name=name,
                    kind="unknown",
                    first_seen_month=entry.month,
                    last_seen_month=entry.month,
                )
            else:
                actor.last_seen_month = entry.month

    def get_actor(self, name: str) -> ActorState | None:
        return self.actors.get(name)

    def to_prompt_summary(self, max_chars: int = 2000) -> str:
        """Compact newest-first bullet list + one-line actor roster."""
        lines = ["PAST EVENTS (newest first):"]
        for entry in reversed(self.entries):
            option = f" [chose {entry.chosen_option_id}]" if entry.chosen_option_id else ""
            lines.append(
                f"- Month {entry.month} ({entry.event_id}): {entry.title} — {entry.summary}{option}"
            )
        roster = ", ".join(
            f"{name} ({a.kind}, last seen M{a.last_seen_month})"
            for name, a in self.actors.items()
        )
        if roster:
            lines.append(f"ACTORS: {roster}")
        text = "\n".join(lines)
        if len(text) <= max_chars:
            return text
        return text[:max_chars].rsplit("\n", 1)[0] + "\n…(truncated)"

    def to_dict(self) -> dict[str, Any]:
        return {
            "actors": {
                name: {
                    "name": a.name,
                    "kind": a.kind,
                    "first_seen_month": a.first_seen_month,
                    "last_seen_month": a.last_seen_month,
                    "notes": list(a.notes),
                }
                for name, a in self.actors.items()
            },
            "entries": [
                {
                    "month": e.month,
                    "event_id": e.event_id,
                    "title": e.title,
                    "actors": list(e.actors),
                    "summary": e.summary,
                    "chosen_option_id": e.chosen_option_id,
                }
                for e in self.entries
            ],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Chronicle:
        actors = {
            name: ActorState(
                name=row["name"],
                kind=row["kind"],
                first_seen_month=row["first_seen_month"],
                last_seen_month=row["last_seen_month"],
                notes=list(row.get("notes", [])),
            )
            for name, row in data.get("actors", {}).items()
        }
        entries = [
            ChronicleEntry(
                month=e["month"],
                event_id=e["event_id"],
                title=e["title"],
                actors=list(e["actors"]),
                summary=e["summary"],
                chosen_option_id=e.get("chosen_option_id"),
            )
            for e in data.get("entries", [])
        ]
        return cls(actors=actors, entries=entries)
