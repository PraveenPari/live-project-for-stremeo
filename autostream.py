import subprocess
import os
import sys
import json
import time
from datetime import datetime


def is_video_available(url):
    """Check if YouTube video is available and playable (live or regular)"""
    print(f"Checking video availability: {url}")
    try:
        cmd = [
            'yt-dlp',
            '--js-runtimes', 'node',
            '--dump-json',
            '--no-download',
            '--extractor-args', 'youtube:player_client=android,web',
            '--user-agent', 'Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
            '--no-check-certificates',
        ]

        # Use cookies if available
        if os.path.exists('cookies.txt'):
            file_size = os.path.getsize('cookies.txt')
            print(f"  Using cookies.txt ({file_size} bytes)")
            cmd.extend(['--cookies', 'cookies.txt'])
        else:
            print("  WARNING: No cookies.txt found!")

        cmd.append(url)
        print(f"  Running: {' '.join(cmd[:5])}...")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

        if result.returncode == 0:
            data = json.loads(result.stdout)
            title = data.get('title', 'Unknown')
            is_live = data.get('is_live', False)
            duration = data.get('duration', 0)
            print(f"  Title: {title}")
            print(f"  Is Live: {is_live}")
            print(f"  Duration: {duration}s")
            print("Video is available and playable!")
            return True
        else:
            print(f"  yt-dlp error (full):\n{result.stderr}")
            return False

    except subprocess.TimeoutExpired:
        print("  Video check timed out after 60s")
        return False
    except Exception as e:
        print(f"  Video check failed: {e}")
        return False


def load_config():
    """Load configuration from config.json with env var overrides"""
    config = {}

    # Load from config.json if it exists
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            config = json.load(f)
        print(f"Loaded config from {config_path}")

    # Environment variables override config.json (empty strings fall back to config)
    youtube_url = os.getenv('YOUTUBE_URL') or config.get('youtube_channel_url', '')
    stream_key = os.getenv('FB_STREAM_KEY') or config.get('facebook_stream_key', '')

    return youtube_url, stream_key


def main():
    print(f"Starting stream check at {datetime.now()}")

    youtube_url, stream_key = load_config()

    if not youtube_url:
        print("ERROR: No YouTube URL configured. Set YOUTUBE_URL env var or update config.json")
        sys.exit(1)

    if not stream_key:
        print("ERROR: No Facebook stream key configured. Set FB_STREAM_KEY env var or update config.json")
        sys.exit(1)

    print(f"YouTube URL: {youtube_url}")
    print(f"Stream Key: {stream_key[:30]}..." if len(stream_key) > 30 else f"Stream Key: {stream_key}")

    # Check if the video is available (with retries for rate limiting)
    max_retries = 3
    retry_delay = 30  # seconds
    video_ok = False

    for attempt in range(1, max_retries + 1):
        print(f"\nAttempt {attempt}/{max_retries}...")
        if is_video_available(youtube_url):
            video_ok = True
            break
        elif attempt < max_retries:
            print(f"Waiting {retry_delay}s before retry...")
            time.sleep(retry_delay)

    if video_ok:
        print("\nStarting stream to Facebook...")

        # Call stream_facebook.py to pipe yt-dlp -> ffmpeg -> Facebook
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
            sys.exit(1)
    else:
        print("Video is not available after all retries. Exiting.")
        sys.exit(1)


if __name__ == '__main__':
    main()