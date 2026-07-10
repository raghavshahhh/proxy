"""Round-robin API key rotation across multiple NVIDIA NIM accounts.

Spreads requests across every configured key from the start (so no single
key gets hammered toward its rate limit) and puts a key on cooldown the
moment it gets rate-limited, so the next call - and any in-flight retry -
picks a different key automatically.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

DEFAULT_COOLDOWN_SECONDS = 60.0


@dataclass
class NimKeyRotator:
    """Round-robins a fixed set of NIM API keys with per-key cooldowns."""

    keys: tuple[str, ...]
    cooldown_seconds: float = DEFAULT_COOLDOWN_SECONDS
    _index: int = field(default=0, init=False)
    _cooldown_until: dict[str, float] = field(default_factory=dict, init=False)

    @classmethod
    def from_settings_values(
        cls,
        keys_csv: str | None,
        single_key: str,
        *,
        cooldown_seconds: float = DEFAULT_COOLDOWN_SECONDS,
    ) -> NimKeyRotator:
        """Build a rotator from NVIDIA_NIM_API_KEYS (comma-separated), falling
        back to the single NVIDIA_NIM_API_KEY when the plural setting is unset.
        """
        parsed = tuple(k.strip() for k in (keys_csv or "").split(",") if k.strip())
        if not parsed and single_key.strip():
            parsed = (single_key.strip(),)
        return cls(keys=parsed, cooldown_seconds=cooldown_seconds)

    @property
    def key_count(self) -> int:
        return len(self.keys)

    def current_key(self) -> str:
        """Return the key most recently handed out by :meth:`next_key`."""
        if not self.keys:
            return ""
        return self.keys[(self._index - 1) % len(self.keys)]

    def next_key(self) -> str:
        """Return the next key in round-robin order, skipping cooldowns.

        Falls back to the least-stale key if every key is cooling down, so a
        request never fails outright just because all keys recently hit a
        rate limit.
        """
        if not self.keys:
            return ""
        now = time.monotonic()
        for _ in range(len(self.keys)):
            key = self.keys[self._index % len(self.keys)]
            self._index += 1
            if self._cooldown_until.get(key, 0.0) <= now:
                return key
        return self.keys[self._index % len(self.keys)]

    def mark_rate_limited(self, key: str) -> None:
        """Put a key on cooldown after a 429 so it's skipped until it clears."""
        if key:
            self._cooldown_until[key] = time.monotonic() + self.cooldown_seconds
