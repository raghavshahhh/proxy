# Proxy Status & Configuration

**Last Updated:** 2026-04-03
**Status:** ✅ PRODUCTION READY

---

## Current Setup

| Component | Value |
|-----------|-------|
| **Deployment** | Render Cloud (`https://proxy-jf5d.onrender.com`) |
| **Local Fallback** | `http://localhost:8082` |
| **Auth Token** | `freecc` (no real API key needed) |
| **Provider** | NVIDIA NIM (free tier, 40 req/min) |

---

## Model Routing (Multi-Model Setup)

| Claude Model | Actual Model | Provider | Speed | Capabilities |
|--------------|--------------|----------|-------|--------------|
| **Opus** | `moonshotai/kimi-k2.5` | NVIDIA NIM | ~60s | Text only (best quality) |
| **Sonnet** | `meta/llama-3.2-90b-vision-instruct` | NVIDIA NIM | ~5s | Text + Image ✅ |
| **Haiku** | `stepfun-ai/step-3.5-flash` | NVIDIA NIM | ~1s | Text only (fast) |
| **Default** | `meta/llama-3.2-90b-vision-instruct` | NVIDIA NIM | ~5s | Text + Image ✅ |

---

## Features Working

| Feature | Status | Notes |
|---------|--------|-------|
| **Text Generation** | ✅ Working | All models respond properly |
| **Image Input** | ✅ Working | Sonnet/Default (Llama Vision) supports it |
| **Tool Use** | ✅ Working | Heuristic parser enabled |
| **Thinking Tags** | ✅ Working | `<think>` tags parsed |
| **Streaming** | ✅ Working | SSE streaming active |
| **Rate Limiting** | ✅ Working | 40 req/min enforced |
| **Multi-Model Routing** | ✅ Working | Opus/Sonnet/Haiku route correctly |

---

## Recent Changes (2026-04-03)

### 1. Image Support Added ✅
**File:** `providers/common/message_converter.py`

**Change:** Added image block conversion in `_convert_user_message()` method.

```python
elif block_type == "image":
    flush_text()
    source = get_block_attr(block, "source", {})
    media_type = source.get("media_type", "image/jpeg") if isinstance(source, dict) else "image/jpeg"
    data = source.get("data") or source.get("base64") or "" if isinstance(source, dict) else ""

    if data:
        result.append({
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:{media_type};base64,{data}"}
                }
            ]
        })
```

**Test Result:** Image blocks now properly convert to OpenAI format and vision models respond correctly.

---

### 2. Model Routing Configured ✅
**File:** `.env`

**Configuration:**
```bash
# Opus = Kimi-K2.5 (Best text quality, ~60s, text-only)
MODEL_OPUS=nvidia_nim/moonshotai/kimi-k2.5

# Sonnet = Llama 3.2 90B Vision (Text + Image support, ~5s)
MODEL_SONNET=nvidia_nim/meta/llama-3.2-90b-vision-instruct

# Haiku = Fast model for quick tasks (~1s)
MODEL_HAIKU=nvidia_nim/stepfun-ai/step-3.5-flash

# Default fallback
MODEL=nvidia_nim/meta/llama-3.2-90b-vision-instruct
```

---

## Environment Variables

```bash
# API Key
NVIDIA_NIM_API_KEY=nvapi-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Model Routing
MODEL_OPUS=nvidia_nim/moonshotai/kimi-k2.5
MODEL_SONNET=nvidia_nim/meta/llama-3.2-90b-vision-instruct
MODEL_HAIKU=nvidia_nim/stepfun-ai/step-3.5-flash
MODEL=nvidia_nim/meta/llama-3.2-90b-vision-instruct

# Timeouts
HTTP_READ_TIMEOUT=300
HTTP_CONNECT_TIMEOUT=30
```

---

## How to Use

### Local Testing
```bash
cd ~/free-claude-code
uv run uvicorn server:app --host 0.0.0.0 --port 8082
```

### Claude Code CLI
```bash
# Via .zshrc (permanent)
export ANTHROPIC_BASE_URL="https://proxy-jf5d.onrender.com"
export ANTHROPIC_API_KEY="freecc"

# Or one-time
ANTHROPIC_BASE_URL="https://proxy-jf5d.onrender.com" ANTHROPIC_API_KEY="freecc" claude
```

### Test Image Input
```bash
curl -X POST http://localhost:8082/v1/messages \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer freecc" \
  -d '{
    "model": "claude-sonnet-4-5",
    "messages": [{
      "role": "user",
      "content": [
        {"type": "text", "text": "Describe this image"},
        {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": "BASE64_DATA"}}
      ]
    }],
    "max_tokens": 100
  }'
```

---

## Known Limitations

| Limitation | Impact | Workaround |
|------------|--------|------------|
| Kimi-K2.5 = Text Only | Images don't work with Opus model | Use Sonnet for image tasks |
| Render Sleep | First request after idle = ~30s cold start | Use local proxy for development |
| Rate Limit | 40 requests/minute | Queue requests or use local fallback |

---

## Health Check

```bash
# Render Proxy
curl https://proxy-jf5d.onrender.com/health
# Expected: {"status":"healthy"}

# Local Proxy
curl http://localhost:8082/health
# Expected: {"status":"healthy"}
```

---

## Deployment

### Render Deployment
1. Code changes committed to GitHub
2. Render auto-deploys on push to `main`
3. Health check: https://proxy-jf5d.onrender.com/health

### Local Development
1. Clone: `~/free-claude-code`
2. Install: `uv sync`
3. Run: `uv run uvicorn server:app --host 0.0.0.0 --port 8082`

---

## Architecture

```
┌─────────────────┐         ┌──────────────────┐         ┌─────────────────┐
│  Claude Code    │────────>│  Render Proxy    │────────>│  NVIDIA NIM     │
│  CLI / VSCode   │<────────│  (FastAPI)       │<────────│  (LLM Models)   │
└─────────────────┘         └──────────────────┘         └─────────────────┘
     Anthropic API               Port 8082                  OpenAI-compatible
     Format (SSE)                (Local/Render)             Format (SSE)
```

---

## Version History

| Date | Change | Status |
|------|--------|--------|
| 2026-04-03 | Image support added | ✅ Deployed |
| 2026-04-03 | Multi-model routing (Opus/Sonnet/Haiku) | ✅ Deployed |
| 2026-04-03 | Kimi-K2.5 as Opus model | ✅ Deployed |
| 2026-04-03 | Llama 3.2 90B Vision as Sonnet model | ✅ Deployed |

---

## Quick Reference

**Need best text quality?** → Use `claude-opus-4-5` (routes to Kimi-K2.5)

**Need image support?** → Use `claude-sonnet-4-5` (routes to Llama Vision)

**Need fast response?** → Use `claude-haiku-4-5` (routes to Step-3.5-Flash)

**Not sure?** → Default uses Llama 3.2 90B Vision (balanced)

---

## Contact & Support

- **GitHub:** https://github.com/raghavx03/proxy
- **Render Dashboard:** https://dashboard.render.com
- **NVIDIA NIM:** https://build.nvidia.com
