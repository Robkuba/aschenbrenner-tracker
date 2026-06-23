# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project does

Monitors Leopold Aschenbrenner's hedge fund (Situational Awareness LP, CIK `0002045724`) via SEC EDGAR 13F filings. When a new quarterly report is detected, it:
1. Sends a WhatsApp alert (via CallMeBot or Twilio) with opened/closed positions.
2. Regenerates a portfolio evolution chart, Instagram carousel slides, and an animated reel video.
3. Posts a JSON payload to a Make.com webhook, which routes content to Buffer/Metricool as drafts for social publishing (X thread, Instagram carousel, LinkedIn post, Reel).

The system is designed to run unattended via GitHub Actions once a day.

## Running the scripts

```bash
# Check for new 13F filing and send WhatsApp alert if found
python aschenbrenner_tracker.py

# Print the current portfolio (no alert sent)
python aschenbrenner_tracker.py --report

# Send a test WhatsApp to verify connectivity
python aschenbrenner_tracker.py --test-wa

# Preview the social media payload without sending (dry-run)
python publish.py

# Generate social content text (X thread, IG carousel, EN hook)
python social_content.py

# Generate portfolio evolution chart → aschenbrenner_evolucion.png
python chart_evolution.py

# Generate Instagram carousel slides → slides/slide_*.png
python carousel_images.py

# Generate animated reel video → reel_aschenbrenner.mp4 (requires ffmpeg)
python reel_video.py
```

Dependencies: `pip install matplotlib pillow` + system `ffmpeg` for video.

## Architecture

### Module dependency graph

```
aschenbrenner_tracker.py   ← core: EDGAR fetch, state machine, WhatsApp
    ↑
social_content.py          ← text content for X/IG/LinkedIn (imports tracker)
    ↑
carousel_images.py         ← PNG slides using Pillow (imports tracker + social_content)
reel_video.py              ← animated MP4 using Pillow + ffmpeg (imports tracker + social_content)
chart_evolution.py         ← matplotlib bar chart (imports tracker only)
publish.py                 ← orchestrates all content, posts to Make.com webhook
fonts_util.py              ← portable Poppins font resolver (used by carousel + reel)
```

`publish.py` is called automatically by `aschenbrenner_tracker.py` at runtime when a new filing is detected (via `import publish; publish.publish_new_filing(...)`).

### State persistence

`state.json` (path configurable via `STATE_FILE` env var) stores:
- `processed`: list of accession numbers already handled (prevents duplicate alerts).
- `last_period`: most recent quarter end date (`YYYY-MM-DD`).
- `assets`: dict keyed by `"cusip|putCall"` with position history including `first_seen`, `last_seen`, `exit_period`, and `status` (`"open"` / `"closed"`).

On first run, it loads the full history as a baseline and optionally sends a "tracker activated" WhatsApp (`ALERT_ON_FIRST_RUN = True`).

### Environment variables / secrets

| Variable | Purpose |
|---|---|
| `SEC_USER_AGENT` | Required by EDGAR (name + email). |
| `CALLMEBOT_PHONE` / `CALLMEBOT_APIKEY` | Free WhatsApp alerts via CallMeBot. |
| `TWILIO_SID` / `TWILIO_TOKEN` / `TWILIO_FROM` / `TWILIO_TO` | Alternative WhatsApp via Twilio. |
| `MAKE_WEBHOOK_URL` | Make.com webhook URL for social scheduling. |
| `IMAGE_BASE_URL` | Public base URL for chart/carousel images in the Make payload. |
| `SCHEDULE_MODE` | `"draft"` (default) or `"auto"` for Make.com scheduling. |
| `SCHEDULE_OFFSET_DAYS` | Days ahead to schedule the post (default: 0). |
| `METRICOOL_USER_TOKEN` / `METRICOOL_BLOG_ID` | Optional direct Metricool API (prefer routing through Make.com). |

### GitHub Actions

`.github/workflows/tracker.yml` runs daily at 12:00 UTC. Sequence:
1. Regenerate chart, carousel, and reel.
2. Run the tracker (alerts + Make.com webhook).
3. Commit `state.json`, generated images, slides, video, and downloaded fonts back to the repo with `[skip ci]`.

Secrets go in **Settings → Secrets → Actions**; `IMAGE_BASE_URL` and `SCHEDULE_MODE` go in **Variables**.

### Font resolution (`fonts_util.py`)

Tries in order: `./fonts/` (local), `/usr/share/fonts/truetype/google-fonts/` (system), download from Google Fonts GitHub raw, fallback to DejaVu (bundled with matplotlib). Results are cached in-process.

### Visual branding

All generated images/video use a dark GitHub-style palette (`#0d1117` background) with green/blue/red for longs/calls/puts. Brand handle is `@robkubanoinvest`. Canvas sizes: carousel 1080×1350 px, reel 1080×1920 px at 30 FPS.
