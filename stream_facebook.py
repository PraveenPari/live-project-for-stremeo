import argparse
import os
import subprocess
import sys


def mask_stream_key(stream_key):
    """Never print the full RTMP key into logs (CI logs are public)."""
    if not stream_key:
        return '***'
    # Keep only the scheme+server portion visible, e.g. rtmps://live-api-s.facebook.com:443/rtmp/***
    if '/rtmp/' in stream_key:
        base = stream_key.split('/rtmp/')[0]
        return f"{base}/rtmp/***"
    return '***'


def stream_to_facebook(video_url, stream_key):
    """Streams to Facebook using a pipeline: yt-dlp -> ffmpeg.

    Returns the pipeline's exit code (0 on success, non-zero on failure).
    """
    print(f"Starting Pipeline Stream for: {video_url}")

    # Resolve ffmpeg path: prefer static_ffmpeg bundle, fall back to system ffmpeg
    ffmpeg_path = 'ffmpeg'
    try:
        import static_ffmpeg
        from static_ffmpeg.run import get_or_fetch_platform_executables_else_raise
        static_ffmpeg.add_paths()
        ffmpeg_path = get_or_fetch_platform_executables_else_raise()[0]
    except Exception as e:
        print(f"static_ffmpeg unavailable ({e}), using system ffmpeg")

    # 1. yt-dlp Command (Producer)
    yt_dlp_cmd = [
        sys.executable, '-m', 'yt_dlp',
        '--js-runtimes', 'node',
        '-o', '-',          # Output to stdout
        '--quiet',          # Suppress excessive logs
        '--no-warnings',
        '--extractor-args', 'youtube:player_client=android,web',
        '--user-agent', 'Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
        '--no-check-certificates',
        '-f', 'best',       # Best quality single A/V format
    ]

    if os.path.exists('cookies.txt'):
        print("Using cookies.txt for stream pipeline...")
        yt_dlp_cmd.extend(['--cookies', 'cookies.txt'])

    yt_dlp_cmd.append(video_url)

    # 2. FFmpeg Command (Consumer)
    ffmpeg_cmd = [
        ffmpeg_path,
        '-y',               # Overwrite output
        '-re',              # Read input at native frame rate
        '-thread_queue_size', '4096',

        # Input: Read from Pipe
        '-i', 'pipe:0',

        # Facebook Settings (720p Stability Mode)
        '-vf', "scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2",

        '-c:v', 'libx264',
        '-preset', 'veryfast',
        '-tune', 'zerolatency',

        '-max_muxing_queue_size', '1024',
        '-fflags', '+genpts+discardcorrupt+nobuffer',

        # Audio
        '-c:a', 'aac',
        '-b:a', '128k',
        '-ar', '44100',
        '-af', 'aresample=async=1000',

        # Video Bitrate (Lowered for stability)
        '-b:v', '2500k',
        '-maxrate', '2800k',
        '-bufsize', '5000k',

        '-pix_fmt', 'yuv420p',
        '-r', '30',
        '-g', '60',

        '-f', 'flv',
        stream_key
    ]

    print("Initializing Pipe...")
    print("Producer:", " ".join(yt_dlp_cmd))
    # Print consumer command with the stream key masked — never leak it to logs
    print("Consumer:", " ".join(ffmpeg_cmd[:-1]), mask_stream_key(stream_key))

    p1 = None
    p2 = None
    try:
        # Create the Pipeline
        # yt-dlp writes to PIPE, FFmpeg reads from PIPE
        p1 = subprocess.Popen(yt_dlp_cmd, stdout=subprocess.PIPE, stderr=sys.stderr)
        p2 = subprocess.Popen(ffmpeg_cmd, stdin=p1.stdout, stdout=sys.stdout, stderr=sys.stderr)

        # Allow p1 to receive a SIGPIPE if p2 exits.
        p1.stdout.close()

        # Wait for ffmpeg to finish
        ffmpeg_rc = p2.wait()
        print(f"ffmpeg exited with code {ffmpeg_rc}")

        # Ensure yt-dlp is also done
        p1.wait()

        if ffmpeg_rc != 0:
            print("STREAM FAILED: ffmpeg exited with a non-zero code")
            return ffmpeg_rc

        print("Stream pipeline finished cleanly")
        return 0

    except KeyboardInterrupt:
        print("\nStopping stream...")
        for p in (p2, p1):
            if p:
                try:
                    p.terminate()
                except Exception:
                    pass
        return 130
    except Exception as e:
        print(f"An error occurred: {e}")
        for p in (p2, p1):
            if p:
                try:
                    p.terminate()
                except Exception:
                    pass
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Stream YouTube video to Facebook Live via Pipe.")
    parser.add_argument("--url", required=True, help="YouTube video URL")
    parser.add_argument("--key", required=True, help="Facebook Stream Key (RTMP URL)")

    args = parser.parse_args()

    sys.exit(stream_to_facebook(args.url, args.key))
