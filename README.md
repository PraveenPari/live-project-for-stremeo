# Stream Automation

This project contains scripts to stream YouTube videos directly to Facebook Live using FFmpeg locally, with support for automated daily checks.

## Prerequisites

1. Install Python 3.x
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Configuration

1.  Rename `config.json` (or create it) with the following content:
    ```json
    {
      "youtube_channel_url": "https://www.youtube.com/@YourChannel",
      "facebook_stream_key": "rtmps://live-api-s.facebook.com:443/rtmp/YOUR-STREAM-KEY"
    }
    ```

## Usage

### Auto Streamer (Recommended)
Checks if the configured YouTube channel is live. If yes, it starts streaming to Facebook.
```bash
python autostream.py
```

### Manual Stream
To stream a specific video manually:
```bash
python stream_facebook.py --url "YOUTUBE_VIDEO_URL" --key "YOUR-FB-STREAM-KEY"
```

## Deployment to GitHub

To deploy this code to your GitHub repository:

1.  Initialize a Git repository (if not already done):
    ```bash
    git init
    ```

2.  Add files:
    ```bash
    git add .
    ```

3.  Commit changes:
    ```bash
    git commit -m "Initial commit for live-project-for-stremeo"
    ```

4.  Create a new repository named `live-project-for-stremeo` on GitHub.

5.  Add your GitHub remote (replace `YOUR_USERNAME` with your actual GitHub username):
    ```bash
    git remote add origin https://github.com/YOUR_USERNAME/live-project-for-stremeo.git
    ```

6.  Push to GitHub:
    ```bash
    git branch -M main
    git push -u origin main
    ```

## GitHub Actions Automation

This project includes a workflow to automatically check for a live stream daily at 8:00 AM IST.

### Setup

1.  Push this code to a **GitHub** repository (GitHub Actions does not run on Bitbucket).
2.  Go to your GitHub Repository Settings -> Secrets and variables -> Actions.
3.  Add the following Repository Secrets:
    *   `YOUTUBE_CHANNEL_URL`: The full URL of the YouTube channel to check (e.g., `https://www.youtube.com/@ChannelName`).
    *   `FB_STREAM_KEY`: Your Facebook Live Stream Key (RTMP URL + Key).

### Manual Trigger
You can also manually trigger the "Daily Stream Check" workflow from the "Actions" tab in GitHub.

## Notes on Latency
The `stream_facebook.py` script is configured with `-fflags nobuffer` and `-tune zerolatency` to minimize delay. Ensure your network connection is stable, as zero buffer makes the stream sensitive to network jitter.
