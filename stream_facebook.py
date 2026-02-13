import argparse
import subprocess
import sys
import shutil
import static_ffmpeg

def get_video_url(youtube_url):
    # This is kept for compatibility but we prefer piping now
    return youtube_url

def stream_to_facebook(video_url, stream_key):
    """Streams to Facebook using a pipeline: yt-dlp -> ffmpeg."""
    
    # Ensure static-ffmpeg binary paths are set up
    static_ffmpeg.add_paths()
    
    print(f"Starting Pipeline Stream for: {video_url}")
    
    # 1. yt-dlp Command (Producer)
    # Use python -m yt_dlp to ensure we find the installed module
    yt_dlp_cmd = [
        sys.executable, '-m', 'yt_dlp',
        '--js-runtimes', 'node',
        '-o', '-',          # Output to stdout
        '--quiet',          # Suppress excessive logs
        '--no-warnings',
        '--extractor-args', 'youtube:player_client=android,web',
        '--user-agent', 'Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
        '--no-check-certificates',
        '-f', 'best',       # Best quality
    ]
    
    import os
    if os.path.exists('cookies.txt'):
        print("Using cookies.txt for stream pipeline...")
        yt_dlp_cmd.extend(['--cookies', 'cookies.txt'])
        
    yt_dlp_cmd.append(video_url)

    # 2. FFmpeg Command (Consumer)
    # Use 'ffmpeg' directly since static_ffmpeg.add_paths() adds it to os.environ['PATH']
    # If that fails, we can try to find it explicitly, but add_paths usually works for subprocess if shell=False?
    # Actually subprocess doesn't always pick up the path modification in the same process immediately for 'executable' lookup if not shell=True.
    # Let's get the absolute path to be safe.
    try:
        from static_ffmpeg.run import get_or_fetch_platform_executables_else_raise
        ffmpeg_path = get_or_fetch_platform_executables_else_raise()[0]
    except:
        ffmpeg_path = 'ffmpeg'

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
    print("Consumer:", " ".join(ffmpeg_cmd))
    
    try:
        # Create the Pipeline
        # yt-dlp writes to PIPE, FFmpeg reads from PIPE
        p1 = subprocess.Popen(yt_dlp_cmd, stdout=subprocess.PIPE, stderr=sys.stderr)
        p2 = subprocess.Popen(ffmpeg_cmd, stdin=p1.stdout, stdout=sys.stdout, stderr=sys.stderr)
        
        # Allow p1 to receive a SIGPIPE if p2 exits.
        p1.stdout.close()  
        
        # Wait for ffmpeg to finish
        p2.wait()
        
        # Ensure yt-dlp is also done
        p1.wait()
        
    except KeyboardInterrupt:
        print("\nStopping stream...")
        try:
            p2.terminate()
        except: pass
        try:
            p1.terminate()
        except: pass
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Stream YouTube video to Facebook Live via Pipe.")
    parser.add_argument("--url", required=True, help="YouTube video URL")
    parser.add_argument("--key", required=True, help="Facebook Stream Key (RTMP URL)")
    
    args = parser.parse_args()
    
    # We pass the original URL directly to the pipe function
    stream_to_facebook(args.url, args.key)
