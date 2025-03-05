import googleapiclient.discovery
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

API_KEY = os.getenv("API_KEY")
CHANNEL_ID = "UCCK3OZi788Ok44K97WAhLKQ"  # Replace with your channel ID
PLAYLIST_ID = "PLkkCdeu97j3DVg0ZhXg7LY6vFuHqohGEf" # Replace with your playlist ID

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
        logging.error(f"Error: {e}")
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
        logging.error(f"Error retrieving latest video: {e}")
        return None

def main():
    youtube = googleapiclient.discovery.build("youtube", "v3", developerKey=API_KEY)
    latest_video_id, latest_video_title = get_latest_public_video_info(youtube, PLAYLIST_ID)

    if not latest_video_id:
        logging.info("Could not retrieve latest public video information.")
        return

    # Print the video ID to standard output
    print(latest_video_id)

    logging.info(f"New public video detected: {latest_video_title} (ID: {latest_video_id})")

if __name__ == "__main__":
    if not API_KEY:
        logging.error("API_KEY is missing. Set it in GitHub Secrets.")
    else:
        main()
