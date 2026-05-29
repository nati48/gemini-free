# Gemini Free 🆓✨

Use Google Gemini's **free web version** (everything you get at [gemini.google.com](https://gemini.google.com)) as if it were a regular API with your own API key — no Google Cloud account, no `GEMINI_API_KEY`, no quota juggling.

> Built on the unofficial [`gemini-webapi`](https://github.com/HanaokaYuzu/Gemini-API) library + Playwright cookie automation.

---

## ⚠️ Heads up

This talks to the Gemini web app the same way your browser does. That means:

- Cookies expire every few days — but the library auto-refreshes them in the background.
- Heavy or obviously automated use **can get your Google account flagged**. Use a throwaway Google account if you care.
- It's against Google's TOS for "production" use. Personal projects, prototypes, learning = your call.

If you need something rock-solid for a real product, use the [official Gemini API](https://ai.google.dev) (also has a free tier).

---

## What you get

- ✅ Access to the same models the free web client has (2.5 Flash, 2.5 Pro, etc.)
- ✅ Your own API key — `Authorization: Bearer <your-key>` like any normal API
- ✅ Cookie auto-grab via a Playwright browser window (sign in once, done)
- ✅ OpenAI-compatible `/v1/chat/completions` endpoint
- ✅ CLI mode too

---

## Quick start

### 1. Install

```bash
git clone https://github.com/YOUR_USER/gemini-free.git
cd gemini-free
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

### 2. Set your own API key

```bash
cp .env.example .env
# edit .env and set GEMINI_FREE_API_KEY to a long random string
```

### 3. Grab Google cookies (one-time login)

```bash
python -m gemini_free.auth
```

A Chromium window pops up → log in to your Google account → wait until Gemini's chat UI shows → the window closes automatically and `cookies.json` is saved.

### 4. Start the server

```bash
uvicorn gemini_free.server:app --host 0.0.0.0 --port 8787
```

### 5. Call it

```bash
curl -X POST http://localhost:8787/v1/chat \
  -H "Authorization: Bearer $GEMINI_FREE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Explain quantum entanglement in one sentence"}'
```

Or OpenAI-style:

```bash
curl -X POST http://localhost:8787/v1/chat/completions \
  -H "Authorization: Bearer $GEMINI_FREE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemini-flash",
    "messages": [{"role": "user", "content": "Hi!"}]
  }'
```

### CLI

```bash
python -m gemini_free.cli "What's the capital of Japan?"
```

---

## Endpoints

| Method | Path | What it does |
|---|---|---|
| GET  | `/health` | Is the client ready? |
| POST | `/v1/chat` | Simple `{prompt, model?, files?}` → `{text, images, ...}` |
| POST | `/v1/chat/completions` | OpenAI-compatible (drop-in for many tools) |

All POST endpoints require `Authorization: Bearer <GEMINI_FREE_API_KEY>`.

---

## Project layout

```
gemini-free/
├── gemini_free/
│   ├── __init__.py
│   ├── auth.py       # Playwright cookie grabber
│   ├── client.py     # Wrapper around gemini-webapi
│   ├── server.py     # FastAPI HTTP server
│   └── cli.py        # Tiny CLI
├── requirements.txt
├── .env.example
└── README.md
```

---

## When cookies expire

`gemini-webapi` auto-refreshes them while the process is running. If the server has been stopped for too long or Google rotated everything, just re-run:

```bash
python -m gemini_free.auth
```

and restart the server.

---

## License

MIT — do what you want, just don't blame me if your Google account gets temp-banned.
