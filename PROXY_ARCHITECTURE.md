# Proxy Architecture Deep Dive

**Created:** 2026-04-03  
**Session:** Architecture discovery with Claude Code

---

## How It Actually Works

### The Magic Trick
Claude Code CLI thinks it's talking to Anthropic API, but actually it's using **NVIDIA NIM (FREE)** via a translation proxy!

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Claude Code    │────▶│  Render Proxy    │────▶│   NVIDIA NIM    │
│     CLI         │     │  (FastAPI)       │     │   (Mistral)     │
│  v2.1.91        │◄────│  Translator      │◄────│   675B params   │
└─────────────────┘     └──────────────────┘     └─────────────────┘
   Anthropic API              Port 8082            OpenAI API
      (SSE)                   (Local/Render)          (SSE)
```

---

## Step-by-Step Translation

### Step 1: CLI Sends Anthropic Format
```http
POST /v1/messages
Authorization: Bearer freecc

{
  "model": "claude-opus-4-6",
  "messages": [
    {"role": "user", "content": "Hello, how are you?"}
  ],
  "max_tokens": 4096
}
```

### Step 2: Proxy Resolves Model
**Location:** `config/settings.py:192-205`

```python
def resolve_model(self, claude_model_name: str) -> str:
    name_lower = claude_model_name.lower()
    if "opus" in name_lower and self.model_opus:
        return self.model_opus
    if "haiku" in name_lower and self.model_haiku:
        return self.model_haiku
    if "sonnet" in name_lower and self.model_sonnet:
        return self.model_sonnet
    return self.model
```

**Current Mapping:**
- `claude-opus-4-6` → `mistralai/mistral-large-3-675b-instruct-2512`
- `claude-sonnet-4-6` → `mistralai/mistral-large-3-675b-instruct-2512`
- `claude-haiku-4-5` → `mistralai/mistral-large-3-675b-instruct-2512`

### Step 3: Translates to OpenAI Format
**Location:** `providers/nvidia_nim/request.py`

```python
def build_request_body(request, nim_settings):
    return {
        "model": "mistralai/mistral-large-3-675b-instruct-2512",
        "messages": [
            {"role": "user", "content": "Hello, how are you?"}
        ],
        "max_tokens": 4096,
        "stream": True
    }
```

### Step 4: Calls NVIDIA NIM API
```http
POST https://integrate.api.nvidia.com/v1/chat/completions
Authorization: Bearer nvapi-xxx

{
  "model": "mistralai/mistral-large-3-675b-instruct-2512",
  "messages": [...],
  "stream": true
}
```

### Step 5: Receives OpenAI SSE Chunks
```
data: {"choices": [{"delta": {"content": "Hello"}}]}
data: {"choices": [{"delta": {"content": "!"}}]}
data: {"choices": [{"delta": {}, "finish_reason": "stop"}]}
```

### Step 6: Translates Back to Anthropic SSE
**Location:** `providers/openai_compat.py:148-361`

```python
async def _stream_response_impl(self, request, input_tokens, request_id):
    # Convert OpenAI chunks to Anthropic format
    for chunk in stream:
        delta = chunk.choices[0].delta
        if delta.content:
            yield sse.emit_text_delta(delta.content)
```

**Output:**
```
event: message_start
data: {"type": "message", "id": "msg_xxx", "role": "assistant"}

event: content_block_start
data: {"type": "content_block", "index": 0, "content_block": {"type": "text"}}

event: content_block_delta
data: {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": "Hello"}}

event: content_block_stop
data: {"type": "content_block_stop", "index": 0}

event: message_stop
data: {"type": "message_stop"}
```

### Step 7: CLI Receives Anthropic Format
CLI displays the response thinking it came from Claude API!

---

## Key Translation Points

| Component | File | Function |
|-----------|------|----------|
| **Entry Point** | `api/routes.py:26` | `/v1/messages` endpoint receives Anthropic requests |
| **Model Resolver** | `config/settings.py:192` | `resolve_model()` - maps Claude model names → NVIDIA models |
| **Provider Factory** | `api/dependencies.py` | Returns `NvidiaNimProvider` instance |
| **Request Builder** | `providers/nvidia_nim/request.py` | Converts Anthropic format → OpenAI format |
| **Stream Handler** | `providers/openai_compat.py:148` | Converts OpenAI SSE → Anthropic SSE |
| **Tool Converter** | `providers/common/message_converter.py` | Tool format translation |
| **Error Mapping** | `providers/common/error_mapping.py` | Maps NVIDIA errors → Anthropic errors |

---

## Current Configuration (2026-04-03)

### Environment Variables (from `.env`)
```bash
NVIDIA_NIM_API_KEY=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

# All models currently point to Mistral Large 3
MODEL_OPUS=nvidia_nim/mistralai/mistral-large-3-675b-instruct-2512
MODEL_SONNET=nvidia_nim/mistralai/mistral-large-3-675b-instruct-2512
MODEL_HAIKU=nvidia_nim/mistralai/mistral-large-3-675b-instruct-2512
MODEL=nvidia_nim/meta/llama-3.2-90b-vision-instruct
```

### Client Configuration (from `.zshrc`)
```bash
export ANTHROPIC_BASE_URL="https://proxy-jf5d.onrender.com"
export ANTHROPIC_API_KEY="freecc"
```

---

## Issues Discovered

| Issue | Status | Impact |
|-------|--------|--------|
| **Local Proxy DOWN** | ❌ | Python 3.14 crash, can't run locally |
| **All Models Same** | ⚠️ | Opus/Sonnet/Haiku all → Mistral, no quality/speed choice |
| **No Telegram Config** | ⚠️ | Messaging only on Discord, Telegram not set up |
| **Render Working** | ✅ | Cloud proxy at `proxy-jf5d.onrender.com` functional |

---

## Cost Comparison

| Service | Actual Cost | Notes |
|---------|-------------|-------|
| **Real Claude Opus** | $15-75/month | Anthropic API pricing |
| **Your Setup** | **₹0 (FREE)** | NVIDIA NIM free tier (5000 RPM) |
| **Proxy Hosting** | ₹0 | Render free tier |
| **Total Savings** | **100%** | Using Mistral 675B for free! |

---

## Files Involved in Request Flow

```
1. api/routes.py:26
   └─ create_message() - Entry point

2. api/dependencies.py
   └─ get_provider_for_type() - Returns NvidiaNimProvider

3. config/settings.py:192
   └─ resolve_model() - Maps claude-* to nvidia_nim/*

4. providers/nvidia_nim/client.py
   └─ _build_request_body() - Builds OpenAI request

5. providers/openai_compat.py:148
   └─ _stream_response_impl() - Streams + translates response

6. providers/common/sse_builder.py
   └─ Anthropic SSE format construction
```

---

## How to Verify

### Test Proxy Health
```bash
curl https://proxy-jf5d.onrender.com/health
# Expected: {"status":"healthy","provider":"nvidia_nim","model":"nvidia_nim/meta/llama-3.2-90b-vision-instruct"}
```

### Test Model Resolution
```bash
curl -X POST https://proxy-jf5d.onrender.com/v1/messages \
  -H "Authorization: Bearer freecc" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "claude-opus-4-6",
    "messages": [{"role": "user", "content": "Say hello"}],
    "max_tokens": 100
  }'
```

---

## Summary

**The Setup:**
- Claude Code CLI thinks it's using Anthropic API
- Actually using NVIDIA NIM Mistral Large 3 (675B params) for FREE
- Proxy translates Anthropic ↔ OpenAI format seamlessly
- Render hosts the proxy (always on)
- Local proxy broken (Python 3.14 issue)

**Current State:**
- ✅ Working: Render proxy, NVIDIA NIM, all features
- ❌ Broken: Local proxy server
- ⚠️ Needs fix: Multi-model routing, Telegram setup

**Next Steps:**
1. Fix local proxy (Python 3.12 downgrade)
2. Configure different models for Opus/Sonnet/Haiku
3. Add Telegram bot token for messaging
4. Test image support with Llama Vision

---

*Document created during architecture discovery session with Claude Code v2.1.91*
