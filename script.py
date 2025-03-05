import googleapiclient.discovery
import os

# Load API key from environment variables
API_KEY = os.getenv("YOUTUBE_API_KEY")  # Uses GitHub Secrets
CHANNEL_ID = "UCCK3OZi788Ok44K97WAhLKQ"
PLAYLIST_ID = "PLkkCdeu97j3DVg0ZhXg7LY6vFuHqohGEf"
PREVIOUS_VIDEO_ID_FILE = "previous_video_id.txt"

def get_latest_public_video_info(youtube, playlist_id):
    try:
        request = youtube.playlistItems().list(
            part="contentDetails",
            playlistId=playlist_id,
            maxResults=50,
        )
        response = request.execute()

        if "items" in response and response["items"]:
            video_ids = [item["contentDetails"]["videoId"] for item in response["items"]]
            latest_video = get_latest_published_public_video(youtube, video_ids)
            if latest_video:
                return latest_video["id"], latest_video["snippet"]["title"]
        return None, None

    except Exception as e:
        print(f"Error: {e}")
        return None, None

def get_latest_published_public_video(youtube, video_ids):
    try:
        request = youtube.videos().list(
            part="snippet,status",
            id=",".join(video_ids),
            maxResults=50,
        )
        response = request.execute()

        public_videos = [video for video in response.get("items", []) if video["status"]["privacyStatus"] == "public"]
        return max(public_videos, key=lambda x: x["snippet"]["publishedAt"]) if public_videos else None

    except Exception as e:
        print(f"Error retrieving latest video: {e}")
        return None

def main():
    youtube = googleapiclient.discovery.build("youtube", "v3", developerKey=API_KEY)
    latest_video_id, latest_video_title = get_latest_public_video_info(youtube, PLAYLIST_ID)

    if not latest_video_id:
        print("Could not retrieve latest public video information.")
        return

    previous_video_id = None
    if os.path.exists(PREVIOUS_VIDEO_ID_FILE):
        with open(PREVIOUS_VIDEO_ID_FILE, "r") as f:
            previous_video_id = f.read().strip()

    if latest_video_id != previous_video_id:
        print(f"New public video detected: {latest_video_title} (ID: {latest_video_id})")
        with open(PREVIOUS_VIDEO_ID_FILE, "w") as f:
            f.write(latest_video_id)
    else:
        print("No new public videos found.")

if __name__ == "__main__":
    if not API_KEY:
        print("API_KEY is missing. Set it in GitHub Secrets.")
    else:
        main()
