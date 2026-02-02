import json
import sys
import os
import streamlink
import stream_facebook

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
    Checks if a channel is live using Streamlink and returns the DIRECT video URL.
    Returns None if the channel is not live.
    Using Streamlink is usually faster than yt-dlp for live checks.
    """
    print(f"Checking for live stream on: {channel_url}")
    
    # Ensure we are checking the /live endpoint if generic channel URL is provided
    # Streamlink handles channel URLs well, but explicit /live is safer for "is live now" logic on some platforms
    target_url = channel_url
    # Only append /live if it's a channel URL (not a specific video)
    if 'youtube.com' in channel_url and not channel_url.endswith('/live') and 'watch?v=' not in channel_url:
         if channel_url.endswith('/'):
            target_url = channel_url + 'live'
         else:
            target_url = channel_url + '/live'

    # First attempt: Check the specific /live endpoint (most reliable for "current" stream)
    try:
        streams = streamlink.streams(target_url)
    except streamlink.PluginError as e:
        print(f"Plugin error on /live url: {e}")
        streams = None
    except Exception as e:
        print(f"Error checking /live url: {e}")
        streams = None

    # Second attempt: If /live failed, try the raw channel URL
    if not streams and target_url != channel_url:
        print(f"Retrying with raw channel URL: {channel_url}")
        try:
             streams = streamlink.streams(channel_url)
        except Exception as e:
             print(f"Error checking raw url: {e}")
             streams = None

    if not streams:
        print("Channel is not currently live (No streams found).")
        return None
    
    # Get the 'best' quality stream (usually 1080p or 720p)
    if 'best' in streams:
        print("Live stream found!")
        return streams['best'].url
    elif 'mobile_worst' in streams: # Fallback
            return streams['mobile_worst'].url
    else:
        # Return first available if 'best' missing
        return list(streams.values())[0].url

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
    # This now returns the DIRECT HLS URL (m3u8), not the YouTube Page URL
    direct_stream_url = get_channel_live_url(channel_url)
    
    if direct_stream_url:
        print(f"Direct Stream URL obtained.")
        print("Starting restream to Facebook...")
        
        # We pass the direct URL. We need to tell stream_facebook it's a direct URL.
        # But stream_facebook currently expects a YouTube URL to extract. 
        # We will update stream_facebook to detect if it's already a direct link or simple call the stream function.
        
        stream_facebook.stream_to_facebook(direct_stream_url, fb_key)
    else:
        print("No live stream detected. Exiting.")
        sys.exit(0)

if __name__ == "__main__":
    main()
