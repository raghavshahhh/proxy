"""NVIDIA NIM provider implementation with multi-key load balancing."""

import itertools
from typing import Any

from config.nim import NimSettings
from providers.base import ProviderConfig
from providers.openai_compat import OpenAICompatibleProvider

from .request import build_request_body

NVIDIA_NIM_BASE_URL = "https://integrate.api.nvidia.com/v1"


class NvidiaNimProvider(OpenAICompatibleProvider):
    """NVIDIA NIM provider with multi-key round-robin load balancing."""

    def __init__(self, config: ProviderConfig, *, nim_settings: NimSettings):
        # Parse multiple API keys (comma-separated) for load balancing
        api_keys = [k.strip() for k in config.api_key.split(",") if k.strip()]
        self._api_key_iterator = itertools.cycle(api_keys) if len(api_keys) > 1 else None
        self._api_keys = api_keys
        self._key_count = len(api_keys)
        self._current_key_index = 0

        # Use first key for initial client
        super().__init__(
            config,
            provider_name="NIM",
            base_url=config.base_url or NVIDIA_NIM_BASE_URL,
            api_key=api_keys[0] if api_keys else config.api_key,
        )
        self._nim_settings = nim_settings

    def _get_next_api_key(self) -> str:
        """Get next API key in round-robin fashion."""
        if self._api_key_iterator:
            key = next(self._api_key_iterator)
            self._current_key_index = (self._current_key_index + 1) % self._key_count
            return key
        return self._api_keys[0] if self._api_keys else ""

    def _build_request_body(self, request: Any) -> dict:
        """Internal helper for tests and shared building."""
        return build_request_body(request, self._nim_settings)
