import googleapiclient.discovery
import os
import logging
import requests
import google.generativeai as genai
import json
import yt_dlp
from pydub import AudioSegment

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Environment Variables
API_KEY = os.getenv("API_KEY")  # YouTube API Key
CHANNEL_ID = "UCCK3OZi788Ok44K97WAhLKQ"  # Replace with your YouTube channel ID
PLAYLIST_ID = "PLkkCdeu97j3DVg0ZhXg7LY6vFuHqohGEf"  # Replace with your playlist ID
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPOSITORY = os.getenv("GITHUB_REPOSITORY")
VARIABLE_NAME = "PREVIOUS_VIDEO_ID"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
FACEBOOK_PAGE_ID = os.getenv("FACEBOOK_PAGE_ID")
FACEBOOK_ACCESS_TOKEN = os.getenv("FACEBOOK_ACCESS_TOKEN")
GEMINI_MODEL = 'gemini-pro'  # Or gemini-2.0-flash
AUDIO_SAMPLE_RATE = 16000 #Hz

def get_latest_public_video_info(youtube, playlist_id):
    """Fetches the latest public video from a YouTube playlist."""
    try:
        request = youtube.playlistItems().list(
            part="contentDetails",
            playlistId=playlist_id,
            maxResults=10,  # Get the latest 10 videos
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
    """Finds the latest public video from a list of video IDs."""
    try:
        request = youtube.videos().list(
            part="snippet,status",
            id=",".join(video_ids),
            maxResults=10,
        )
        response = request.execute()

        public_videos = [video for video in response.get("items", []) if video["status"]["privacyStatus"] == "public"]
        return max(public_videos, key=lambda x: x["snippet"]["publishedAt"]) if public_videos else None
    except Exception as e:
        logging.error(f"Error retrieving latest video: {e}")
        return None

def get_repo_variable(token, repo, variable_name):
    """Fetches a variable from GitHub Actions."""
    url = f"https://api.github.com/repos/{repo}/actions/variables/{variable_name}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json().get("value")
    else:
        logging.error(f"Failed to get variable '{variable_name}': {response.status_code} - {response.text}")
        return None

def update_repo_variable(token, repo, variable_name, value):
    """Updates a GitHub Actions variable."""
    url = f"https://api.github.com/repos/{repo}/actions/variables/{variable_name}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json",
    }
    data = {"value": value}
    response = requests.patch(url, headers=headers, json=data)
    if response.status_code == 204:
        logging.info(f"Variable '{variable_name}' updated successfully.")
    else:
        logging.error(f"Failed to update variable '{variable_name}': {response.status_code} - {response.text}")

def download_audio(video_id):
    """Downloads the audio from a YouTube video."""
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    ydl_opts = {
        'format': '251',
        'extractaudio': True,
        'audioformat': 'mp3',
        'outtmpl': f'{video_id}.%(ext)s',
        'cookiesfrombrowser': ['chrome']
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(video_url, download=False)
            filename = ydl.prepare_filename(info_dict)
            ydl.download([video_url])
        return filename
    except Exception as e:
        logging.error(f"Error downloading audio: {e}")
        return None

def downsample_audio(input_file, output_file, target_rate=AUDIO_SAMPLE_RATE):
    """Downsamples an audio file."""
    try:
        audio = AudioSegment.from_file(input_file)
        downsampled_audio = audio.set_frame_rate(target_rate)
        downsampled_audio.export(output_file, format="mp3")
        return True
    except Exception as e:
        logging.error(f"Error downsampling audio: {e}")
        return False

def get_news_summary(audio_file_path, gemini_api_key):
    """Uses Gemini AI to generate a news summary in Sinhala from audio."""
    genai.configure(api_key=gemini_api_key)
    model = genai.GenerativeModel(GEMINI_MODEL)
    try:
        with open(audio_file_path, "rb") as audio_file:
            audio_data = audio_file.read()
        prompt = "Summarize the content of this audio in Sinhala as json format, only include title and summary field"
        response = model.generate_content([
            prompt,
            {
                "mime_type": "audio/mpeg",
                "data": audio_data
            }
        ])
        text = response.text
        if "```json" in text:
            start = text.find("{")
            end = text.rfind("}") + 1
            json_str = text[start:end]
        else:
            json_str = text #if gemini returns clean json
        return json_str

    except Exception as e:
        logging.error(f"Error getting news summary: {e}")
        return None

def publish_to_facebook(access_token, page_id, message):
    """Publishes a post on a Facebook Page using the Graph API."""
    url = f"[https://graph.facebook.com/v19.0/](https://graph.facebook.com/v19.0/){page_id}/feed"
    payload = {
        "message": message,
        "access_token": access_token
    }

    try:
        response = requests.post(url, data=payload)
        result = response.json()

        if "id" in result:
            logging.info(f"Post published successfully! Post ID: {result['id']}")
        else:
            logging.error(f"Failed to publish post: {result}")
    except Exception as e:
        logging.error(f"Error posting to Facebook: {e}")

def main():
    """Main function that runs the automation."""
    youtube = googleapiclient.discovery.build("youtube", "v3", developerKey=API_KEY)
    latest_video_id, latest_video_title = get_latest_public_video_info(youtube, PLAYLIST_ID)

    if not latest_video_id:
        logging.info("Could not retrieve latest public video information.")
        return

    logging.info(f"New public video detected: {latest_video_title} (ID: {latest_video_id})")

    previous_video_id = get_repo_variable(GITHUB_TOKEN, REPOSITORY, VARIABLE_NAME)

    if latest_video_id != previous_video_id:
        logging.info("New video detected. Processing...")
        update_repo_variable(GITHUB_TOKEN, REPOSITORY, VARIABLE_NAME, latest_video_id)

        audio_file = download_audio(latest_video_id)
        if audio_file:
            downsampled_file = f"downsampled_{latest_video_id}.mp3"
            if downsample_audio(audio_file, downsampled_file):
                news_summary_json = get_news_summary(downsampled_file, GEMINI_API_KEY)
                if news_summary_json:
                    try:
                        news_data = json.loads(news_summary_json)
                        summary = news_data.get("summary")
                        title = news_data.get("title")
                        if summary and title:
                            facebook_message = f"{title}\n\n{summary}"
                            publish_to_facebook(FACEBOOK_ACCESS_TOKEN, FACEBOOK_PAGE_ID, facebook_message)
                        else:
                            logging.error("Summary or title missing from Gemini response.")
                    except json.JSONDecodeError as e:
                        logging.error(f"Failed to decode JSON from Gemini response: {e}, response: {news_summary_json}")
                else:
                    logging.error("Failed to get news summary.")
                os.remove(downsampled_file)  # Clean up downsampled file
            else:
                logging.error("Downsampling audio failed.")
            os.remove(audio_file) # Clean up original audio file
        else:
            logging.error("Audio download failed.")
    else:
        logging.info("No new video detected. Skipping update.")

if __name__ == "__main__":
    if not API_KEY:
        logging.error("API_KEY is missing. Set it in GitHub Secrets.")
    elif not GITHUB_TOKEN or not REPOSITORY:
        logging.error("GITHUB_TOKEN or GITHUB_REPOSITORY is missing.  Set them in GitHub Secrets.")
    elif not GEMINI_API_KEY:
        logging.error("GEMINI_API_KEY is missing. Set it in GitHub Secrets.")
    elif not FACEBOOK_ACCESS_TOKEN or not FACEBOOK_PAGE_ID:
        logging.warning("FACEBOOK_ACCESS_TOKEN or FACEBOOK_PAGE_ID is missing.  Facebook posting will be skipped.")
        main() # still execute the main function.
    else:
        main()
