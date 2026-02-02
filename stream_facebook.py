import argparse
import subprocess
import sys
import shutil
from yt_dlp import YoutubeDL
import static_ffmpeg

def get_video_url(youtube_url):
    """Extracts the best video stream URL using yt-dlp."""
    ydl_opts = {
        'format': 'best',
        'quiet': True,
    }
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(youtube_url, download=False)
        return info['url']

def stream_to_facebook(video_url, stream_key):
    """Streams the video to Facebook using FFmpeg with low latency settings."""
    
    # Ensure static-ffmpeg binary paths are set up if system ffmpeg is missing
    static_ffmpeg.add_paths()
    
    # Facebook Live recommended settings:
    # 720p (1280x720) or 1080p (1920x1080)
    # Keyframe interval: 2 seconds (GOP 60 for 30fps)
    # Bitrate: 4000k max standard, but we'll use variable for low latency
    
    ffmpeg_cmd = [
        'ffmpeg',
        # Input Options: Reconnect to source if it drops
        '-reconnect', '1',
        '-reconnect_at_eof', '1',
        '-reconnect_streamed', '1',
        '-reconnect_delay_max', '5',
        
        '-i', video_url,
        
        # Scale to 1080p (Full High Resolution)
        '-vf', "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2",
        
        '-c:v', 'libx264',
        '-preset', 'ultrafast',
        '-tune', 'zerolatency',
        
        # Latency flags
        '-fflags', 'nobuffer',
        '-flags', 'low_delay',
        '-strict', 'experimental',
        
        # Bitrate Control: High Quality CBR for 1080p
        '-b:v', '4500k',
        '-minrate', '4500k',
        '-maxrate', '4500k',
        '-bufsize', '4500k', # 1-second buffer
        
        '-pix_fmt', 'yuv420p',
        '-r', '30', # Force 30 fps
        '-g', '60', # 2 second GOP (Standard for FB at 30fps)
        
        '-c:a', 'aac',
        '-b:a', '128k',
        '-ar', '44100',
        
        '-f', 'flv',
        stream_key
    ]

    print("Starting stream to Facebook...")
    print("Command:", " ".join(ffmpeg_cmd))
    
    try:
        process = subprocess.Popen(ffmpeg_cmd)
        process.wait()
    except KeyboardInterrupt:
        print("\nStopping stream...")
        process.terminate()
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Stream YouTube video to Facebook Live.")
    parser.add_argument("--url", required=True, help="YouTube video URL or Direct Stream URL")
    parser.add_argument("--key", required=True, help="Facebook Stream Key (RTMP URL)")
    
    args = parser.parse_args()
    
    print(f"Processing URL: {args.url}")
    
    # Simple check if it's already a direct link (m3u8/mp4)
    if "m3u8" in args.url or ".mp4" in args.url or "googlevideo.com" in args.url:
        print("Detected direct stream URL.")
        direct_url = args.url
    else:
        # Use yt-dlp as fallback if run standalone (or switch to streamlink here too)
        # Using streamlink for consistency
        import streamlink
        try:
            streams = streamlink.streams(args.url)
            if 'best' in streams:
                direct_url = streams['best'].url
            else:
                 # Fallback to get_video_url (yt-dlp) if streamlink fails or for VODs
                 direct_url = get_video_url(args.url)
        except:
             direct_url = get_video_url(args.url)

    if direct_url:
        print(f"Got direct stream URL. Initializing FFmpeg...")
        stream_to_facebook(direct_url, args.key)
    else:
        print("Failed to retrieve video URL.")
