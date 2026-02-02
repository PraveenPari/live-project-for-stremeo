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
        '-o', '-',          # Output to stdout
        '--quiet',          # Suppress excessive logs
        '--no-warnings',
        '--user-agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
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
        '-re',              # Read input at native frame rate (CRITICAL for piping live content correctly if not handled by source)
                            # However, for live piping, -re is sometimes risky. 
                            # But since we are piping FROM a downloader that downloads as fast as possible, 
                            # we usually want ffmpeg to pace itself or the downloader to pace.
                            # yt-dlp downloads live streams in real-time usually.
                            # Let's try WITHOUT -re first because input is a stream.
                            # Actually, with piping, '-re' is safer if the source is a file, but for live source it might be redundant.
                            # Let's keep input options simple.
        
        # Input: Read from Pipe
        '-i', 'pipe:0',
        
        # Facebook Settings (1080p, 30fps, CBR 4500k)
        '-vf', "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2",
        
        '-c:v', 'libx264',
        '-preset', 'ultrafast',
        '-tune', 'zerolatency',
        
        # Latency & Stability
        '-fflags', 'nobuffer',
        '-flags', 'low_delay',
        '-strict', 'experimental',
        
        # Audio
        '-c:a', 'aac',
        '-b:a', '128k',
        '-ar', '44100',
        
        # Video Bitrate (CBR)
        '-b:v', '4500k',
        '-minrate', '4500k',
        '-maxrate', '4500k',
        '-bufsize', '4500k',
        
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
