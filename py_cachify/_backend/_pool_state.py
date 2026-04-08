from dataclasses import dataclass, field


@dataclass
class PoolState:
    """Pool state stored in the cache backend.

    Uses a dict as a set with expiration timestamps to track active slots.
    """

    slots: dict[str, float] = field(default_factory=dict)  # slot_id -> expiration_timestamp

    @property
    def count(self) -> int:
        return len(self.slots)

    def cleanup(self, now: float) -> int:
        """Remove expired slots and return the cleaned count."""
        expired = [sid for sid, exp in self.slots.items() if now > exp]
        for sid in expired:
            del self.slots[sid]
        return len(self.slots)
