from unittest.mock import patch

import openai
import pytest

from config.nim import NimSettings
from providers.base import ProviderConfig
from providers.nvidia_nim import NvidiaNimProvider
from providers.nvidia_nim.key_rotation import NimKeyRotator


def test_from_settings_values_parses_comma_separated_keys():
    rotator = NimKeyRotator.from_settings_values("key1, key2 ,key3", "fallback")
    assert rotator.keys == ("key1", "key2", "key3")


def test_from_settings_values_falls_back_to_single_key_when_plural_unset():
    rotator = NimKeyRotator.from_settings_values("", "solo-key")
    assert rotator.keys == ("solo-key",)


def test_from_settings_values_falls_back_when_plural_is_blank_entries_only():
    rotator = NimKeyRotator.from_settings_values(" , ,", "solo-key")
    assert rotator.keys == ("solo-key",)


def test_next_key_round_robins_across_all_keys():
    rotator = NimKeyRotator(keys=("a", "b", "c"))
    assert [rotator.next_key() for _ in range(6)] == ["a", "b", "c", "a", "b", "c"]


def test_next_key_skips_keys_on_cooldown():
    rotator = NimKeyRotator(keys=("a", "b"))
    rotator.mark_rate_limited("a")
    assert rotator.next_key() == "b"
    assert rotator.next_key() == "b"


def test_next_key_falls_back_when_every_key_is_cooling_down():
    rotator = NimKeyRotator(keys=("a", "b"))
    rotator.mark_rate_limited("a")
    rotator.mark_rate_limited("b")
    # No exception, no empty string - a key is still returned so a request
    # can be attempted rather than failing outright.
    assert rotator.next_key() in ("a", "b")


def test_current_key_reflects_last_key_handed_out():
    rotator = NimKeyRotator(keys=("a", "b"))
    rotator.next_key()
    assert rotator.current_key() == "a"
    rotator.next_key()
    assert rotator.current_key() == "b"


@pytest.fixture
def multi_key_provider():
    config = ProviderConfig(api_key="key1", base_url="https://test.api.nvidia.com/v1")
    with patch("providers.openai_compat.AsyncOpenAI"):
        return NvidiaNimProvider(
            config, nim_settings=NimSettings(), extra_api_keys="key1,key2,key3"
        )


@pytest.mark.asyncio
async def test_before_create_rotates_client_api_key(multi_key_provider):
    seen_keys = []
    for _ in range(4):
        multi_key_provider._before_create()
        seen_keys.append(multi_key_provider._client.api_key)
    assert seen_keys == ["key1", "key2", "key3", "key1"]


@pytest.mark.asyncio
async def test_before_create_is_a_noop_with_a_single_key():
    config = ProviderConfig(
        api_key="only-key", base_url="https://test.api.nvidia.com/v1"
    )
    with patch("providers.openai_compat.AsyncOpenAI"):
        provider = NvidiaNimProvider(config, nim_settings=NimSettings())
    provider._client.api_key = "only-key"
    provider._before_create()
    assert provider._client.api_key == "only-key"


@pytest.mark.asyncio
async def test_get_retry_request_body_rotates_key_on_rate_limit(multi_key_provider):
    multi_key_provider._before_create()  # picks "key1"
    assert multi_key_provider._client.api_key == "key1"

    error = openai.RateLimitError(
        "rate limited", response=_fake_response(429), body=None
    )
    retry_body = multi_key_provider._get_retry_request_body(error, {"model": "x"})

    assert retry_body == {"model": "x"}
    # The limited key is cooling down, so the next rotation skips it.
    multi_key_provider._before_create()
    assert multi_key_provider._client.api_key == "key2"


@pytest.mark.asyncio
async def test_get_retry_request_body_returns_none_on_rate_limit_with_single_key():
    config = ProviderConfig(
        api_key="only-key", base_url="https://test.api.nvidia.com/v1"
    )
    with patch("providers.openai_compat.AsyncOpenAI"):
        provider = NvidiaNimProvider(config, nim_settings=NimSettings())

    error = openai.RateLimitError(
        "rate limited", response=_fake_response(429), body=None
    )
    assert provider._get_retry_request_body(error, {"model": "x"}) is None


def _fake_response(status_code: int):
    import httpx

    request = httpx.Request("POST", "https://test.api.nvidia.com/v1/chat/completions")
    return httpx.Response(status_code, request=request)
