# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Project Does

Automated financial intelligence system that monitors SEC 13F filings for **Situational Awareness LP** (Leopold Aschenbrenner's hedge fund). When a new quarterly filing is detected, it sends a WhatsApp alert, generates visual assets (Instagram carousel, animated reel, portfolio chart), and publishes social media content via Make.com → Buffer/Metricool.

## Commands

```bash
# Install dependencies
pip install matplotlib pillow
sudo apt-get install ffmpeg

# Run main tracker (detect new 13F, send WhatsApp alert, update state)
python aschenbrenner_tracker.py

# Show text report of current portfolio (no network side-effects)
python aschenbrenner_tracker.py --report

# Test WhatsApp integration
python aschenbrenner_tracker.py --test-wa

# Regenerate visual assets individually
python chart_evolution.py       # portfolio evolution PNG
python carousel_images.py       # 6 Instagram carousel slides
python reel_video.py            # animated MP4 reel (requires ffmpeg)

# Dry-run publishing (prints Make.com JSON payload without sending)
python publish.py

# Generate social media copy (X thread, IG caption, LinkedIn post)
python social_content.py
```

No build step — pure Python, no compilation or transpilation.

## Architecture

### Data Flow

```
SEC EDGAR API → aschenbrenner_tracker.py → state.json (persisted)
                       ↓
               WhatsApp alert (CallMeBot or Twilio)
                       ↓
               publish.py → Make.com webhook → Buffer/Metricool → social platforms

Parallel asset generation (GitHub Actions):
  chart_evolution.py  → aschenbrenner_evolucion.png
  carousel_images.py  → slides/slide_1..6.png
  reel_video.py       → reel_aschenbrenner.mp4
```

### State Machine (`state.json`)

All persistent state lives in `state.json` — this file is committed back to the repo by GitHub Actions after each run. The key fields:

- `processed`: list of accession numbers already handled (prevents duplicates)
- `last_period`: most recently processed quarter-end date (e.g. `"2026-03-31"`)
- `assets`: dict keyed by `"cusip|putCall"` — tracks every position ever seen

Position status transitions: `open` → `closed` (never re-opens under same key). Positions are keyed by `(cusip, put_call)` because a fund can hold both shares and puts on the same CUSIP.

### SEC EDGAR Integration

Rate limiting: 0.25s delay between requests; 1.5s backoff on error. The `SEC_USER_AGENT` env var must identify you to EDGAR (required by their ToS). Filings are fetched as XML (`infotable.xml` inside each 13F accession).

### Asset Generation

- **Fonts**: `fonts_util.py` auto-downloads Poppins from Google Fonts on first run into `./fonts/`. Falls back to system fonts if download fails.
- **Carousel**: Pillow draws 1080×1350 PNG slides; slide content is data-driven from `state.json`.
- **Reel**: Pillow renders frames, then `subprocess` pipes them to FFmpeg for H.264 MP4 encoding (1080×1920).
- **Chart**: Matplotlib with a dark theme, quarterly timeline on x-axis.

### Publishing (`publish.py`)

`publish_new_filing()` is the entry point. It assembles a JSON payload containing image URLs (constructed from `IMAGE_BASE_URL` env var pointing at raw GitHub content), social copy, and scheduling metadata, then POSTs to `MAKE_WEBHOOK_URL`. Make.com routes to Buffer/Metricool. `SCHEDULE_MODE=draft` queues posts for review; `auto` publishes immediately.

## Environment Variables

| Variable | Where set | Purpose |
|---|---|---|
| `SEC_USER_AGENT` | GitHub Secret | Identifies requests to SEC EDGAR |
| `CALLMEBOT_PHONE` | GitHub Secret | WhatsApp recipient phone number |
| `CALLMEBOT_APIKEY` | GitHub Secret | CallMeBot API key |
| `MAKE_WEBHOOK_URL` | GitHub Secret | Make.com scenario webhook |
| `IMAGE_BASE_URL` | GitHub Variable | Base URL for raw GitHub asset URLs |
| `SCHEDULE_MODE` | GitHub Variable | `"draft"` or `"auto"` |

Optional Twilio fallback: `TWILIO_SID`, `TWILIO_TOKEN`, `TWILIO_FROM`, `TWILIO_TO`.

## Deployment

GitHub Actions (`.github/workflows/tracker.yml`) runs daily at 12:00 UTC. Sequence:

1. Install Python 3.12 + pip deps + ffmpeg
2. Run asset generators (`chart_evolution.py`, `carousel_images.py`, `reel_video.py`)
3. Run `aschenbrenner_tracker.py` (detects new 13F, sends alert)
4. Commit updated `state.json` and generated assets back to `main`

The workflow also supports `workflow_dispatch` for manual runs.
