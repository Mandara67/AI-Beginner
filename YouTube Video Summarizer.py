import os
import streamlit as st
import pytube as YouTube
import google.generativeai as genai
import sys, re, requests
from bs4 import BeautifulSoup
from google.cloud import speech
from youtube_transcript_api import YouTubeTranscriptApi
from dotenv import load_dotenv

# Set Gemini API key
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY") # insert your GEMINI API Key here

# Load the Gemini model
model = genai.GenerativeModel("models/gemini-1.5-flash")
st.subheader("Enter YouTube URL: ")
st.write("Paste the YouTube link to summarize its content (must have the transcript available)")
url = st.text_input("URL")
language = st.radio("Select language to output: ", ("English", "Spanish", "Korean", "Kannada", "Hindi"))


# Extracts the Video ID from URL
def extract_video_id(url):
    match = re.search(r"v=([a-zA-Z0-9_-]+)", url) # works only with regular youtube URL
    if match:
        return match.group(1)
    else:
        raise ValueError("Invalid Youtube URL.")
if url:
    video_ID = extract_video_id(url)
else:
    video_ID = None  # Handle cases where the URL is empty

# Extracts the Video Metadata from URL
def extract_video_metadata(url):
    r = requests.get(url)
    soup = BeautifulSoup(r.text, features="html.parser")
    title = soup.find("title").text
    channel = soup.find("link", itemprop = "name")['content']
    return title, channel

# Downloads the image of the YouTube for reference
def download_video_thumbnail(url):
    image_url = f"https://img.youtube.com/vi/{video_ID}/hqdefault.jpg"
    image_data = requests.get(image_url).content
    with open('thumbnail.jpg', 'wb') as handler:
        handler.write(image_data)

# Extracts the transcript of the video
def get_video_transcript(url):
    try: # if the video has transcript
        transcript_raw = YouTubeTranscriptApi.get_transcript(video_id=video_ID, languages=['en', 'es', 'ko', 'kn', 'hi'])
        transcript_full = ''.join([i['text'] for i in transcript_raw])
        return transcript_full
    except Exception as e:
        print(f"Transcript not available in this video. Will be downloading the audio file and making the transcript.")
        # Download audio and convert to text
        audio_path = get_video_audio(video_ID)
        if audio_path:
            audio_transcript = transcribe_video_audio(audio_path)
            return audio_transcript
        else:
            return "Failed to process audio"

def get_video_audio(url):
    try:
        yt = YouTube(url)
        audio_stream = yt.streams.filter(only_audio = True).first()
        # Saving the audio file
        save_audio_path = f"{video_ID}.mp3"
        audio_stream.download(filename=save_audio_path)
        return save_audio_path
    except Exception as e:
        print("Error downloading audio.")

def transcribe_video_audio(audio_path):
    try:
        client = speech.SpeechClient()
        with open(audio_path, "rb") as audio_file:
            audio_content = audio_file.read()

        audio = speech.RecognitionAudio(content=audio_content)
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            language_code="en-US"
        )

        response = client.recognize(config=config, audio=audio)
        transcript = " ".join(result.alternatives[0].transcript for result in response.results)
        return transcript
    except Exception as e:
        print(f"Error in transcription: {e}")
        return "Transcription Failed"
    

# Summarizer function
def summarize_video_transcript(text, lang="en"):
    prompt = f"""The following text has the transcript of the Youtube video in its original language. Provide the output in {lang} language.
    Format the output like this:
    Summary: 
    short summary of the video

    Key_Points:
    in bullet points, list the key takeaways

    input_text: {text}
    """

    gemini_response = model.generate_content(prompt)
    return gemini_response.text

def summary():
    if st.button("Summarize"):
        if url:
            title, channel = extract_video_metadata(url)
            st.subheader('Title: ')
            st.write(title)
            st.subheader('Channel: ')
            st.write(channel)

            st.subheader("Video: ")
            st.video(url)
            # download_video_thumbnail(url)
            # st.image(os.path.join(os.getcwd(), "thumbnail.jpg"), caption="Thumbnail", use_container_width=True)

            transcript = get_video_transcript(url)
            summary = summarize_video_transcript(transcript, language)
            st.subheader("Video Summary: ")
            st.write(summary)
        else:
            st.warning("Please enter a YouTube URL.")

if __name__ == "__main__":
    summary()
