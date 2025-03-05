import googleapiclient.discovery
import time
import os

# Load API key from environment variables
API_KEY = os.getenv("API_KEY")  # Uses GitHub Secrets
CHANNEL_ID = "UCCK3OZi788Ok44K97WAhLKQ"
PLAYLIST_ID = "PLkkCdeu97j3DVg0ZhXg7LY6vFuHqohGEf"
CHECK_INTERVAL = 1800  # 30 minutes

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

    if latest_video_id:
        print(f"Latest public video: {latest_video_title} (ID: {latest_video_id})")
    else:
        print("No new videos found.")

if __name__ == "__main__":
    if not API_KEY:
        print("API_KEY is missing. Set it in GitHub Secrets.")
    else:
        main()
