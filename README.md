# Stream Automation

Relays a YouTube live stream to Facebook Live using yt-dlp + FFmpeg, with a daily GitHub Actions check.

## Prerequisites

1. Python 3.x
2. FFmpeg (installed automatically via `static-ffmpeg`, or system `ffmpeg`)
3. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Configuration

Edit `config.json` (or use environment variables — env vars win over the file):

```json
{
  "youtube_url": "https://www.youtube.com/@YourChannel/live",
  "facebook_stream_key": "rtmps://live-api-s.facebook.com:443/rtmp/YOUR-STREAM-KEY"
}
```

**Never commit a real stream key to this file** — the repo is public and the key would be leaked. Put the real key in the `FB_STREAM_KEY` environment variable or GitHub secret instead.

Supported `youtube_url` forms:
- Channel handle — `https://www.youtube.com/@ChannelName` (auto-resolved to `@ChannelName/live`)
- Live alias — `https://www.youtube.com/@ChannelName/live`
- Video — `https://www.youtube.com/watch?v=VIDEO_ID`

## Usage

### Preflight check (recommended before going live)
Validates config, cookies, and that the stream is actually live — without streaming:
```bash
python autostream.py --check-only
```

### Auto Streamer
Checks whether the stream is live. If the configured URL is a scheduled/upcoming live, it polls until it starts (30 min by default), then streams to Facebook:
```bash
python autostream.py [--wait-for-live MINUTES] [--poll-seconds SECONDS]
```

Only an active live stream is relayed by default. To relay any playable video (e.g. a recording):
```bash
python autostream.py --stream-any
```

### Manual Stream
```bash
python stream_facebook.py --url "YOUTUBE_VIDEO_URL" --key "YOUR-FB-STREAM-KEY"
```

## GitHub Actions Automation

The **Daily Stream Check** workflow runs daily at 8:00 AM IST and can also be triggered manually.

### Secrets (Repo Settings → Secrets and variables → Actions)

| Secret | Purpose |
|---|---|
| `YOUTUBE_URL` (or `YOUTUBE_CHANNEL_URL`) | YouTube video/channel URL to watch |
| `FB_STREAM_KEY` | Facebook Live RTMP(S) key |
| `YOUTUBE_COOKIES_BASE64` (or `YOUTUBE_COOKIES`) | Exported YouTube cookies — needed on datacenter runners to pass the "not a bot" check |

### Manual dispatch inputs
- `check_only` — run all preflight checks without streaming.
- `wait_minutes` — if the stream isn't live yet, keep polling this long (default 30).

> GitHub disables scheduled workflows after 60 days of repo inactivity. If runs stop, re-enable the workflow under Actions → Daily Stream Check.

## Notes on Latency
`stream_facebook.py` uses `-fflags nobuffer` and `-tune zerolatency` to minimize delay. Ensure your network connection is stable — zero buffer makes the stream sensitive to jitter.
