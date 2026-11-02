import argparse
import subprocess
import os
import sys
import json
import time
from datetime import datetime


CHECK_TIMEOUT = 90  # seconds per yt-dlp probe


def mask_stream_key(stream_key):
    """Never print the full RTMP key into logs (CI logs are public)."""
    if not stream_key:
        return '***'
    if '/rtmp/' in stream_key:
        base = stream_key.split('/rtmp/')[0]
        return f"{base}/rtmp/***"
    return '***'


def is_channel_url(url):
    """True only for channel paths (/@name, /channel/, /c/, /user/), optionally
    ending in /live. youtube.com/live/<id> is a VIDEO URL, not a channel."""
    markers = ('/@', '/channel/', '/c/', '/user/')
    return any(m in url for m in markers)


def normalize_url(url):
    """Turn a channel URL into its /live alias so yt-dlp resolves the current live video."""
    url = url.rstrip('/')
    if is_channel_url(url) and not url.endswith('/live'):
        url = url + '/live'
    return url


def get_video_info(url):
    """Probe a YouTube URL with yt-dlp.

    Returns (info_dict, error_text): info_dict on success, else error_text.
    """
    print(f"Checking video availability: {url}")
    cmd = [
        'yt-dlp',
        '--js-runtimes', 'node',
        '--dump-json',
        '--no-download',
        '--no-playlist',
        '--extractor-args', 'youtube:player_client=tv_embedded,android,web',
        '--user-agent', 'Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
        '--no-check-certificates',
    ]

    if os.path.exists('cookies.txt'):
        file_size = os.path.getsize('cookies.txt')
        print(f"  Using cookies.txt ({file_size} bytes)")
        cmd.extend(['--cookies', 'cookies.txt'])
    else:
        print("  WARNING: No cookies.txt found — YouTube may block datacenter requests")

    cmd.append(url)

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=CHECK_TIMEOUT)
    except subprocess.TimeoutExpired:
        return None, f"yt-dlp timed out after {CHECK_TIMEOUT}s"
    except Exception as e:
        return None, f"check failed: {e}"

    if result.returncode != 0:
        stderr = result.stderr.strip()
        # yt-dlp *errors* on scheduled streams ("This live event will begin in
        # N minutes" / "Premieres in ...") instead of returning is_upcoming —
        # surface that as an upcoming status so the caller can wait for it.
        if 'will begin in' in stderr or 'Premieres in' in stderr or 'not currently live' in stderr:
            status = 'is_upcoming' if 'not currently live' not in stderr else 'not_live'
            note = stderr.strip().splitlines()[-1]
            return {'live_status': status, 'title': url, '_note': note}, None
        return None, stderr or "yt-dlp failed with no error output"

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        return None, "yt-dlp returned unparseable output"

    return data, None


def describe_video(data):
    live_status = data.get('live_status') or 'not_live'
    print(f"  Title: {data.get('title', 'Unknown')}")
    print(f"  live_status: {live_status}  (is_live={data.get('is_live', False)})")
    if data.get('release_timestamp'):
        print(f"  Scheduled start: {datetime.fromtimestamp(data['release_timestamp'])}")
    if data.get('_note'):
        print(f"  {data['_note']}")
    return live_status


def load_config():
    """Load configuration from config.json with env var overrides"""
    config = {}
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            config = json.load(f)
        print(f"Loaded config from {config_path}")

    # Environment variables override config.json (empty strings fall back to config)
    youtube_url = (os.getenv('YOUTUBE_URL')
                   or os.getenv('YOUTUBE_CHANNEL_URL')
                   or config.get('youtube_url')
                   or config.get('youtube_channel_url', ''))
    stream_key = os.getenv('FB_STREAM_KEY') or config.get('facebook_stream_key', '')

    return youtube_url.strip(), stream_key.strip()


def wait_for_live(youtube_url, wait_minutes, poll_seconds):
    """Probe until the video is live. Returns (data, live_status) or (None, last_error)."""
    deadline = time.time() + wait_minutes * 60
    last_err = None
    while True:
        data, err = get_video_info(youtube_url)
        if data is not None:
            status = describe_video(data)
            if status == 'is_live':
                return data, 'is_live'
            if status in ('is_upcoming', 'not_live'):
                if time.time() >= deadline:
                    return data, status
                print(f"  Not live yet. Poll again in {poll_seconds}s "
                      f"(waiting up to {wait_minutes} min)...")
                time.sleep(poll_seconds)
                continue
            return data, status
        last_err = err
        print(f"  Error: {err}")
        if time.time() >= deadline:
            return None, last_err
        print(f"  Retrying in {poll_seconds}s...")
        time.sleep(poll_seconds)


def main():
    parser = argparse.ArgumentParser(
        description="Check a YouTube live stream and relay it to Facebook Live.")
    parser.add_argument('--url', help='YouTube video/channel URL (overrides env/config)')
    parser.add_argument('--key', help='Facebook stream key (overrides env/config)')
    parser.add_argument('--check-only', action='store_true',
                        help='Run all preflight checks and exit without streaming')
    parser.add_argument('--wait-for-live', type=int, default=30, metavar='MINUTES',
                        help='If the stream is upcoming/not yet live, keep polling '
                             'this many minutes for it to start (default: 30)')
    parser.add_argument('--poll-seconds', type=int, default=60,
                        help='Seconds between live checks while waiting (default: 60)')
    parser.add_argument('--stream-any', action='store_true',
                        help='Stream any playable video, not only an active live stream')
    args = parser.parse_args()

    print(f"Starting stream check at {datetime.now()}")

    youtube_url, stream_key = load_config()
    youtube_url = (args.url or youtube_url).strip()
    stream_key = (args.key or stream_key).strip()

    if not youtube_url:
        print("ERROR: No YouTube URL configured. Set YOUTUBE_URL env var or update config.json")
        sys.exit(1)

    if not stream_key:
        print("ERROR: No Facebook stream key configured. Set FB_STREAM_KEY env var or update config.json")
        sys.exit(1)

    youtube_url = normalize_url(youtube_url)

    print(f"YouTube URL: {youtube_url}")
    print(f"Stream Key: {mask_stream_key(stream_key)}")

    # Probe with retries for rate limiting / transient errors
    max_retries = 3
    retry_delay = 30
    data = None
    status = None

    for attempt in range(1, max_retries + 1):
        print(f"\nAttempt {attempt}/{max_retries}...")
        data, err = get_video_info(youtube_url)
        if data is not None:
            status = describe_video(data)
            break
        print(f"  Error: {err}")
        # Longer backoff when YouTube rate-limits us
        delay = retry_delay * 3 if '429' in err or 'Too Many Requests' in err else retry_delay
        if attempt < max_retries:
            print(f"Waiting {delay}s before retry...")
            time.sleep(delay)

    if data is None:
        print("\nVideo is not available after all retries. Exiting.")
        sys.exit(1)

    # A scheduled/upcoming stream found: for check-only that IS a pass —
    # config, cookies and URL are all valid; it just isn't live yet.
    if args.check_only and status == 'is_upcoming':
        print("\nCHECK-ONLY: preflight passed — stream is scheduled and upcoming. "
              "When run without --check-only it will be picked up when it goes live.")
        sys.exit(0)

    if status == 'is_upcoming' or (status == 'not_live' and is_channel_url(youtube_url)):
        if args.wait_for_live > 0:
            print(f"\nNot live yet — polling for up to {args.wait_for_live} minutes...")
            data, status = wait_for_live(youtube_url, args.wait_for_live, args.poll_seconds)
        else:
            print("\nStream is not live yet and --wait-for-live is 0. Exiting.")

    if status == 'is_live':
        print("\nVideo is LIVE!")
    elif args.stream_any:
        print(f"\nWARNING: video is '{status}' — streaming anyway (--stream-any)")
    else:
        print(f"\nNot streaming: live_status='{status}' "
              f"(use --stream-any to relay non-live videos).")
        sys.exit(1)

    if args.check_only:
        print("\nCHECK-ONLY: all preflight checks passed. Stream NOT started.")
        sys.exit(0)

    print("\nStarting stream to Facebook...")

    script_dir = os.path.dirname(os.path.abspath(__file__))
    stream_script = os.path.join(script_dir, 'stream_facebook.py')

    result = subprocess.run(
        [sys.executable, stream_script, '--url', youtube_url, '--key', stream_key],
        cwd=script_dir
    )

    if result.returncode == 0:
        print("Stream completed successfully!")
    else:
        print(f"Stream failed with exit code: {result.returncode}")
        sys.exit(result.returncode)


if __name__ == '__main__':
    main()
