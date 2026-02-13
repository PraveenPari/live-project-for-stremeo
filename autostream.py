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
        cmd = ['yt-dlp', '--js-runtimes', 'node', '--dump-json', '--no-download', url]

        # Use cookies if available
        if os.path.exists('cookies.txt'):
            cmd.insert(1, '--cookies')
            cmd.insert(2, 'cookies.txt')

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
            print(f"  yt-dlp error: {result.stderr[:500]}")
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

    # Check if the video is available
    if is_video_available(youtube_url):
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
        print("Video is not available or not playable. Exiting.")
        sys.exit(1)


if __name__ == '__main__':
    main()