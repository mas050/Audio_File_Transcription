import streamlit as st
from moviepy.editor import AudioFileClip
import os
import re
from groq import Groq
from streamlit.components.v1 import html

# Initialize Groq client (Make sure your API key is set correctly)
API_KEY = "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" 
os.environ["GROQ_API_KEY"] = API_KEY
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

# --- Helper Functions ---
def copy_to_clipboard_button(text_to_copy):
    """Displays a "Copy to Clipboard" button and handles the copy functionality."""
    html(f"""
        <button id="copyButton">Copy to Clipboard</button>
        <script>
            const copyButton = document.getElementById('copyButton');
            const textToCopy = `{text_to_copy}`;  
            copyButton.addEventListener('click', () => {{
                navigator.clipboard.writeText(textToCopy).then(() => {{
                    console.log('Text copied to clipboard!');
                    copyButton.innerText = "Copied!";
                }}).catch(err => {{
                    console.error('Could not copy text: ', err);
                    copyButton.innerText = "Copy Failed!";
                }});
            }});
        </script>
    """)


def split_audio_moviepy(input_file, output_dir, segment_length = 180):
    """Splits an audio file into segments using MoviePy.

    Args:
        input_file (str): Path to the input audio file (m4a).
        output_dir (str): Directory to save the output audio files.
        segment_length (int, optional): Length of each segment in seconds (default: 60).
    """
    
    # Load the audio file
    audio = AudioFileClip(input_file)
    total_duration = audio.duration

    # Create the output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # Get the original filename without extension
    base_filename = os.path.splitext(os.path.basename(input_file))[0]

    # Split and save segments
    start_time = 0
    segment_id = 1
    while start_time < total_duration:
        end_time = min(start_time + segment_length, total_duration)  # Ensure end_time within bounds

        # Extract the segment
        subclip = audio.subclip(start_time, end_time)

        # Create the output filename
        output_filename = f"{base_filename}_{segment_id}.m4a"
        output_path = os.path.join(output_dir, output_filename)

        # Export the segment
        subclip.write_audiofile(output_path, codec='aac')  # Ensure AAC codec for m4a
        
        # Update for the next segment
        start_time = end_time 
        segment_id += 1


def transcribe_audio(audio_file):
    """Transcribes an audio file using Groq."""
    with open(audio_file, "rb") as file:
        translation = client.audio.translations.create(
            file=(audio_file, file.read()),
            model="whisper-large-v3",
            prompt="Please provide the transcript of this english conversation.",
            response_format="text",
            temperature=0
        )
    return translation

def main():

    # Initialize session state for messages if it doesn't exist
    if "messages" not in st.session_state:
        st.session_state.messages = []

    st.title("Audio Transcription App")

    uploaded_file = st.file_uploader("Upload an audio file", type=["m4a", "mp3"])

    if uploaded_file is not None:
        # Save the uploaded file temporarily
        with open("temp_audio.m4a", "wb") as f:
            f.write(uploaded_file.read())

        # Split audio if necessary (you might want to adjust this based on your needs)
        output_dir = "temp_audio_splits"
        split_audio_moviepy("temp_audio.m4a", output_dir)

        # Get audio files and sort them
        audio_files = [f for f in os.listdir(output_dir) if f.endswith(".m4a")]
        audio_files.sort(key=lambda f: int(re.search(r'_(\d+)\.m4a$', f).group(1)))

        # Initialize progress bar with a label
        progress_bar = st.progress(0, text="Transcription Progress") 
        progress_text = st.empty()  # To display progress text


        # Transcribe each segment and combine transcripts
        full_transcript = ""
        for i, audio_file in enumerate(audio_files):
            audio_path = os.path.join(output_dir, audio_file)
            segment_transcript = transcribe_audio(audio_path)
            full_transcript += segment_transcript

            # Update progress bar and text
            progress = (i + 1) / len(audio_files)
            progress_bar.progress(progress)
            progress_text.text(f"Transcribing... {int(progress * 100)}%")

        progress_text.empty()  # Clear the progress text after completion

        # Display the transcript in a scrollable container
        #st.header("Transcript")
        #text_container = st.container()  # Create a container for the text
        #with text_container:
        #    st.text_area("", value=full_transcript, height=300)  # Use st.text_area for scrolling


        # Append the transcript to the message history
        st.session_state.messages.append({"role": "assistant", "content": full_transcript})

        # Display messages using st.chat_message
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"], unsafe_allow_html=True)

                if message["role"] == "assistant":
                    copy_to_clipboard_button(message["content"])




        # Clean up temporary files (optional)
        os.remove("temp_audio.m4a")
        for audio_file in audio_files:
            os.remove(os.path.join(output_dir, audio_file))
        os.rmdir(output_dir)

if __name__ == "__main__":
    main()
