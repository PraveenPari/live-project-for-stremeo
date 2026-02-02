import sys
import os
# Force UTF-8 for output to handle emojis
os.environ['PYTHONUTF8'] = '1'
import json
import streamlink
import stream_facebook
from yt_dlp import YoutubeDL

def load_config():
    """Loads configuration from config.json"""
    config_path = 'config.json'
    if not os.path.exists(config_path):
        print(f"Error: {config_path} not found.")
        return None
    
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error reading config.json: {e}")
        return None

def get_channel_live_url(channel_url):
    """
    Checks if a channel is live using yt-dlp (Primary) and Streamlink (Fallback).
    Returns the DIRECT video URL.
    """
    print(f"Checking for live stream on: {channel_url}")
    
    print(f"Checking for live stream on: {channel_url}")
    
    # 1. Try Streamlink FIRST (Often better for simple live checks without blocking)
    print("Attempting to fetch with Streamlink first...")
    
    # Ensure checking /live if it's a channel
    target_url = channel_url
    if 'youtube.com' in channel_url and not channel_url.endswith('/live') and 'watch?v=' not in channel_url:
         if channel_url.endswith('/'):
            target_url = channel_url + 'live'
         else:
            target_url = channel_url + '/live'

    try:
        streams = streamlink.streams(target_url)
        if streams:
            if 'best' in streams:
                print("Live stream found via Streamlink!")
                # For streamlink, we might get a raw hls url. 
                # Returing the original URL might be safer if we want to pipe it, 
                # BUT if we want to confirm it is live, getting the stream url is proof.
                # We return the original target_url or channel_url to indicate "Yes it is live".
                # But wait, the main loop expects a URL to stream. 
                # If we return the HLS URL, yt-dlp might fail to pipe it if it expires.
                # Let's return the channel_url (or target_url) so stream_facebook can handle it.
                return target_url
    except Exception as e:
        print(f"Streamlink error: {e}")

    # 2. Try yt-dlp SECOND (Fallback or for detailed metadata)
    print("Streamlink failed or found no stream. Attempting yt-dlp...")
    ydl_opts = {
    
    # Ensure checking /live if it's a channel
    ydl_opts = {
        'format': 'best',
        'quiet': True,
        'ignoreerrors': True,
        'no_warnings': True,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'referer': 'https://www.youtube.com/',
        'http_headers': {
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7'
        }
    }
    
    if os.path.exists('cookies.txt'):
        print("Using cookies.txt for authentication...")
        ydl_opts['cookiefile'] = 'cookies.txt'
    
    with YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(channel_url, download=False)
            if info:
                 # Check 'is_live' or if it's a direct video (protocol check)
                 if info.get('is_live') or (info.get('was_live') == False and 'live_url' in info):
                      print(f"Live stream detected via yt-dlp: {info.get('title', 'Unknown')}")
                      return info.get('url')
                 elif info.get('protocol') in ['m3u8', 'm3u8_native']:
                      print("Direct HLS stream found via yt-dlp!")
                      return info.get('url')
                 
                 # Logic for specific video IDs that are live
                 if 'watch?v=' in channel_url and info.get('url'):
                     print("Video URL found via yt-dlp.")
                     return info.get('url')
        except Exception as e:
            print(f"yt-dlp error: {e}")

    print("No live stream detected by any method.")
    return None

def main():
    config = load_config()
    if not config:
        sys.exit(1)

    channel_url = config.get('youtube_channel_url')
    fb_key = config.get('facebook_stream_key')

    if not channel_url or not fb_key:
        print("Error: Missing 'youtube_channel_url' or 'facebook_stream_key' in config.json")
        sys.exit(1)
    
    # Check if channel is live
    # We use get_channel_live_url to CONFIRM it is live.
    # But for the actual stream, we pass the original URL to stream_facebook so it can pipe it.
    
    live_status_url = get_channel_live_url(channel_url)
    
    if live_status_url:
        print(f"Live Status Confirmed.")
        print("Starting restream to Facebook...")
        
        # Determine which URL to pass. 
        # If 'live_status_url' is a direct link (m3u8), we COULD pass it, but piping the youtube URL is safer/more robust.
        # However, get_channel_live_url returns the direct link or the watch link.
        # If the user provided a specific watch Link, we use that.
        # IF the user provided a Channel Link, we should ideally use the WATCH Link of the current live.
        
        url_to_stream = channel_url
        
        # If it's a generic channel URL, 'channel_url' might not be the specific video.
        # Ideally, `get_channel_live_url` should return the WATCH URL if it found one via yt-dlp.
        # Let's assume if it returns a 'http' link (m3u8) we might have to use that or fallback to channel url with /live.
        # Actually, piping 'channel_url/live' works with yt-dlp too!
        
        if 'watch?v=' not in channel_url and 'youtube.com' in channel_url:
             # It's a channel URL. yt-dlp -o - "channel/live" usually works.
             if not channel_url.endswith('/live'):
                 if channel_url.endswith('/'):
                    url_to_stream = channel_url + 'live'
                 else:
                    url_to_stream = channel_url + '/live'
        
        # If get_channel_live_url returned a specific watch url (from yt-dlp check), use that
        if 'watch?v=' in live_status_url and 'http' in live_status_url:
             url_to_stream = live_status_url
             
        print(f"Streaming from: {url_to_stream}")
        stream_facebook.stream_to_facebook(url_to_stream, fb_key)
    else:
        print("No live stream detected. Exiting.")
        sys.exit(0)

if __name__ == "__main__":
    main()
