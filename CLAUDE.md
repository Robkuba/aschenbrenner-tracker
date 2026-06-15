# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A Python-based SEC 13F filing tracker for Leopold Aschenbrenner's "Situational Awareness LP" hedge fund. It polls the SEC EDGAR API daily (via GitHub Actions), detects new quarterly portfolio positions, sends WhatsApp alerts, generates multi-format social media content (Instagram carousels, Twitter threads, LinkedIn posts, TikTok/Reels videos), and auto-publishes via Make.com webhooks.

## Running Scripts

There is no build step — scripts run directly with Python 3.12. Required packages: `matplotlib`, `pillow`. System dependency: `ffmpeg` (for video generation).

```bash
# Core tracker (checks for new 13F filings, sends WhatsApp alert)
python aschenbrenner_tracker.py

# Show current portfolio report without sending alerts
python aschenbrenner_tracker.py --report

# Send a test WhatsApp message to verify credentials
python aschenbrenner_tracker.py --test-wa

# Generate social content text (Twitter thread, Instagram script, LinkedIn, video hook)
python social_content.py

# Generate Instagram carousel PNG slides (outputs to ./slides/)
python carousel_images.py

# Generate portfolio evolution bar chart (outputs chart_evolution.png)
python chart_evolution.py

# Generate TikTok/Reels vertical video (outputs reel.mp4)
python reel_video.py

# Test Make.com webhook payload (dry run by default — prints JSON without sending)
python publish.py
```

There are no automated tests or linters configured in this project.

## Architecture

### Data Flow

```
SEC EDGAR API → aschenbrenner_tracker.py → state.json (persistence)
                         ↓
               WhatsApp alert (CallMeBot or Twilio)
                         ↓
               social_content.py → formatted text per platform
                         ↓
               carousel_images.py → PNG slides (Pillow, 1080×1350px)
               chart_evolution.py → bar chart PNG (Matplotlib)
               reel_video.py     → MP4 video (Pillow frames + ffmpeg)
                         ↓
               publish.py → Make.com webhook → Buffer/Metricool
```

### State Management

All state lives in `state.json` (a flat JSON file committed back to the repo by CI). Key structure:

```json
{
  "processed": ["accession-number-1", ...],
  "last_period": "2024-09-30",
  "assets": {
    "CUSIP|PUT": {
      "name": "NVIDIA",
      "cusip": "...",
      "put_call": "PUT",
      "first_seen": "Q3 2024",
      "last_seen": "Q3 2024",
      "exit_period": null,
      "value": 12345678,
      "shares": 100000,
      "status": "open"
    }
  }
}
```

### Module Responsibilities

- **`aschenbrenner_tracker.py`** — The core. Fetches SEC EDGAR filing lists (JSON) and parses 13F XML holding tables. Compares current vs prior quarter to detect opened/closed positions. Writes state.json. Sends WhatsApp alerts.
- **`social_content.py`** — Content factory. Takes two filing dicts (current/prior) and generates platform-specific copy: Spanish Twitter thread (6+ posts), Instagram carousel script, LinkedIn post, English video hook.
- **`carousel_images.py`** — Renders 6 Pillow image slides: cover, "who is" bio, puts list, longs list, moves, CTA. Fixed 1080×1350px IG portrait format.
- **`chart_evolution.py`** — Matplotlib stacked bar chart showing portfolio value by position type across quarters.
- **`reel_video.py`** — Frame-by-frame Pillow rendering with easing animations. Encodes 1080×1920 vertical video at 30 FPS, 16 seconds via ffmpeg subprocess.
- **`publish.py`** — Builds a structured JSON payload and POSTs to the Make.com webhook. Supports `draft` (manual approval) and `auto` (scheduled) modes.
- **`fonts_util.py`** — Resolves Poppins font: local file → system → download from Google Fonts → DejaVu fallback. Caches loaded `ImageFont` objects.

### SEC EDGAR Integration

- CIK for Situational Awareness LP is hardcoded in `aschenbrenner_tracker.py`.
- Filing list: `https://data.sec.gov/submissions/CIK{cik}.json`
- Filing directory: `https://www.sec.gov/Archives/edgar/.../index.json`
- The actual holdings are in an XML file inside the filing directory (13F information table).
- All requests include a `User-Agent` header (required by SEC); set via `SEC_USER_AGENT` env var.
- HTTP calls include retry logic with exponential backoff.

### Quarterly Logic

Dates like `2024-09-30` are converted to `Q3 2024`. Position diff is computed by comparing the current quarter's CUSIP+put_call keys against the prior quarter's. "Opened" = appears in current but not prior; "Closed" = in prior but not current.

## Environment Variables

Set these as GitHub Actions secrets/variables (or locally in a `.env`-style export):

| Variable | Required | Description |
|---|---|---|
| `SEC_USER_AGENT` | Yes | e.g. `"MyName Tracker email@example.com"` |
| `CALLMEBOT_PHONE` | One of | WhatsApp phone number e.g. `"+4915123456789"` |
| `CALLMEBOT_APIKEY` | One of | CallMeBot API key |
| `TWILIO_SID` | Alt | Twilio account SID |
| `TWILIO_TOKEN` | Alt | Twilio auth token |
| `TWILIO_FROM` | Alt | Twilio WhatsApp sender |
| `TWILIO_TO` | Alt | Twilio destination number |
| `MAKE_WEBHOOK_URL` | For publishing | Make.com scenario webhook URL |
| `IMAGE_BASE_URL` | For publishing | Base URL for generated images (e.g. GitHub raw content URL) |
| `SCHEDULE_MODE` | Optional | `"draft"` (default) or `"auto"` |
| `SCHEDULE_OFFSET_DAYS` | Optional | Days ahead to schedule posts (default: `0`) |
| `STATE_FILE` | Optional | Path to state.json (default: `"state.json"` in cwd) |

## CI/CD

`.github/workflows/tracker.yml` runs daily at 12:00 UTC and on manual dispatch (`workflow_dispatch`). It:

1. Installs Python 3.12, matplotlib, pillow, ffmpeg
2. Regenerates chart, carousel PNGs, and reel video
3. Runs the tracker (checks SEC, sends alerts, triggers Make.com)
4. Commits and pushes `state.json` + generated assets back to the repo

Generated assets (`state.json`, `*.png` slides, `chart_evolution.png`, `reel.mp4`) are stored directly in the repo and updated on each CI run.
