import os
import sys
import argparse
import asyncio
import json
import tempfile
import sounddevice as sd
import soundfile as sf
import aiohttp
from dotenv import load_dotenv

# Load environment variables from .env file in the same directory
env_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(dotenv_path=env_path)

# --- Configuration ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_STT_ENDPOINT = os.getenv("GROQ_STT_ENDPOINT", "https://api.groq.com/openai/v1/audio/transcriptions")
MODEL = "whisper-large-v3"
SAMPLE_RATE = 16000  # Use 16kHz for speech, which is standard

def record_audio(duration: int) -> str:
    """
    Records audio from the default microphone for a given duration and saves it
    to a temporary WAV file.

    Args:
        duration: The recording duration in seconds.

    Returns:
        The file path to the temporary WAV file.
    """
    print(f"Recording for {duration} seconds... Speak now!", file=sys.stderr)

    # Record audio data as a NumPy array
    recording = sd.rec(int(duration * SAMPLE_RATE), samplerate=SAMPLE_RATE, channels=1, dtype='float32')
    sd.wait()  # Wait for the recording to complete

    print("Recording finished.", file=sys.stderr)

    # Create a temporary file to store the recording
    # delete=False is important so the file isn't removed before we can send it
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')

    # Write the NumPy array to the WAV file
    sf.write(temp_file.name, recording, SAMPLE_RATE)

    return temp_file.name

async def transcribe(audio_path: str):
    """
    Sends an audio file to the Groq STT API and prints the transcribed text.
    """
    if not GROQ_API_KEY:
        print("Error: GROQ_API_KEY is not set. Please add it to your backend/.env file.", file=sys.stderr)
        return

    if not os.path.exists(audio_path):
        print(f"Error: Audio file not found at '{audio_path}'", file=sys.stderr)
        return

    print(f"Transcribing {os.path.basename(audio_path)} with Groq...", file=sys.stderr)

    headers = {"Authorization": f"Bearer {GROQ_API_KEY}"}

    try:
        async with aiohttp.ClientSession() as session:
            with open(audio_path, "rb") as f:
                form_data = aiohttp.FormData()
                form_data.add_field("file", f, filename=os.path.basename(audio_path))
                form_data.add_field("model", MODEL)

                async with session.post(GROQ_STT_ENDPOINT, headers=headers, data=form_data) as resp:
                    if resp.status != 200:
                        print(f"Error: API request failed with status {resp.status}", file=sys.stderr)
                        print(f"Response: {await resp.text()}", file=sys.stderr)
                        return

                    response_json = await resp.json()
                    transcript = response_json.get("text")

                    if transcript:
                        print(transcript)
                    else:
                        print("Error: Could not find 'text' in API response.", file=sys.stderr)
                        print(f"Full response: {json.dumps(response_json, indent=2)}", file=sys.stderr)

    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)

def main():
    """
    Main function to handle command-line arguments for recording or file-based transcription.
    """
    parser = argparse.ArgumentParser(
        description="A simple STT client for Groq. Either provide a file path or use the --record flag."
    )
    # Use a mutually exclusive group to ensure only one mode is chosen
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "audio_file",
        nargs='?',
        default=None,
        help="Path to an audio file to transcribe."
    )
    group.add_argument(
        "-r", "--record",
        type=int,
        metavar="SECONDS",
        help="Record audio from the microphone for a specified number of seconds."
    )
    args = parser.parse_args()

    temp_audio_path = None
    try:
        if args.record:
            # Record from microphone
            temp_audio_path = record_audio(args.record)
            asyncio.run(transcribe(temp_audio_path))
        elif args.audio_file:
            # Use the provided file
            asyncio.run(transcribe(args.audio_file))
    finally:
        # Clean up the temporary file if one was created
        if temp_audio_path and os.path.exists(temp_audio_path):
            os.remove(temp_audio_path)

if __name__ == "__main__":
    main()
