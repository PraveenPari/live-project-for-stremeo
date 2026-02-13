import subprocess
import os
import time
import requests
from datetime import datetime

def check_streamlink(url):
    """Check if stream is live using Streamlink"""
    try:
        result = subprocess.run(['streamlink', url, '--stream-url'], 
                              capture_output=True, text=True, timeout=30)
        return result.returncode == 0
    except Exception as e:
        print(f"Streamlink check failed: {e}")
        return False

def check_ytdlp(url):
    """Check if stream is live using yt-dlp"""
    try:
        result = subprocess.run(['yt-dlp', '--cookies', 'cookies.txt', '--dump-json', url], 
                              capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            import json
            data = json.loads(result.stdout)
            return data.get('is_live', False)
    except Exception as e:
        print(f"yt-dlp check failed: {e}")
    return False

def is_stream_live(url):
    """Check if YouTube stream is live"""
    print(f"Checking for live stream on: {url}")
    
    # Try Streamlink first
    print("Attempting to fetch with Streamlink first...")
    if check_streamlink(url):
        return True
    print("Streamlink failed or found no stream. Attempting yt-dlp...")
    
    # Fallback to yt-dlp
    return check_ytdlp(url)

def download_stream(url, output_path='stream.mp4'):
    """Download live stream using yt-dlp with cookies"""
    try:
        # Check if cookies.txt exists
        if os.path.exists('cookies.txt'):
            print("Using cookies.txt for authentication...")
        
        # First, get available formats
        result = subprocess.run(['yt-dlp', '--cookies', 'cookies.txt', '-F', url], capture_output=True, text=True, timeout=30)
        
        if result.returncode != 0:
            print(f"Error getting formats: {result.stderr}")
            return False
        
        # Get best format
        best_format = 'best'
        
        # Download the stream
        print(f"Downloading stream from {url}")
        result = subprocess.run(['yt-dlp', '--cookies', 'cookies.txt', '-f', best_format, '-o', output_path, url], capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"Successfully downloaded stream to {output_path}")
            return True
        else:
            print(f"Download failed: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"Error downloading stream: {e}")
        return False

def upload_to_facebook(video_path, page_id, access_token):
    """Upload video to Facebook"""
    try:
        upload_url = f"https://graph.facebook.com/v18.0/{page_id}/videos"
        
        with open(video_path, 'rb') as video_file:
            files = {'file': video_file}
            data = {
                'access_token': access_token,
                'description': f'Live stream recording - {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'
            }
            
            print(f"Uploading to Facebook page {page_id}...")
            response = requests.post(upload_url, files=files, data=data)
            
            if response.status_code == 200:
                print(f"Successfully uploaded to Facebook: {response.json()}")
                return True
            else:
                print(f"Facebook upload failed: {response.text}")
                return False
                
    except Exception as e:
        print(f"Error uploading to Facebook: {e}")
        return False

def upload_to_instagram(video_path, ig_user_id, access_token):
    """Upload video to Instagram"""
    try:
        # Instagram requires a two-step process
        # Step 1: Create media container
        create_url = f"https://graph.facebook.com/v18.0/{ig_user_id}/media"
        create_data = {
            'media_type': 'VIDEO',
            'video_url': video_path,  # This should be a public URL
            'caption': f'Live stream recording - {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
            'access_token': access_token
        }
        
        print(f"Creating Instagram media container...")
        response = requests.post(create_url, data=create_data)
        
        if response.status_code != 200:
            print(f"Failed to create media container: {response.text}")
            return False
            
        container_id = response.json().get('id')
        
        # Step 2: Publish media
        publish_url = f"https://graph.facebook.com/v18.0/{ig_user_id}/media_publish"
        publish_data = {
            'creation_id': container_id,
            'access_token': access_token
        }
        
        print(f"Publishing to Instagram...")
        response = requests.post(publish_url, data=publish_data)
        
        if response.status_code == 200:
            print(f"Successfully uploaded to Instagram: {response.json()}")
            return True
        else:
            print(f"Instagram publish failed: {response.text}")
            return False
            
    except Exception as e:
        print(f"Error uploading to Instagram: {e}")
        return False

def main():
    # Configuration
    youtube_url = os.getenv('YOUTUBE_URL', 'https://www.youtube.com/watch?v=UVZtLRtKKdM')
    platform = os.getenv('INPUT_PLATFORM', 'facebook')
    
    # Facebook credentials
    fb_page_id = os.getenv('FB_PAGE_ID')
    fb_access_token = os.getenv('FB_ACCESS_TOKEN')
    
    # Instagram credentials
    ig_user_id = os.getenv('IG_USER_ID')
    ig_access_token = os.getenv('IG_ACCESS_TOKEN')
    
    print(f"Starting stream check at {datetime.now()}")
    print(f"Target platform: {platform}")
    
    # Check if stream is live
    if is_stream_live(youtube_url):
        print("Live stream detected!")
        
        # Download the stream
        video_path = 'stream.mp4'
        if download_stream(youtube_url, video_path):
            # Upload to selected platform
            if platform == 'facebook' and fb_page_id and fb_access_token:
                upload_to_facebook(video_path, fb_page_id, fb_access_token)
            elif platform == 'instagram' and ig_user_id and ig_access_token:
                upload_to_instagram(video_path, ig_user_id, ig_access_token)
            else:
                print(f"Missing credentials for {platform}")
            
            # Cleanup
            if os.path.exists(video_path):
                os.remove(video_path)
        else:
            print("Failed to download stream")
    else:
        print("No live stream detected. Exiting.")

if __name__ == '__main__':
    main()