import os
import sys
import argparse
import asyncio
import json
import tempfile
import collections
import webrtcvad
import sounddevice as sd
import soundfile as sf
import aiohttp
import numpy as np
import random
from dotenv import load_dotenv
from tts import TTSManager, VOICES

# Load environment variables from .env file
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

# Check for required environment variables
if not os.getenv("GROQ_API_KEY"):
    print("Warning: GROQ_API_KEY is not set in .env file. TTS will not work.", file=sys.stderr)
    print("Get a free API key at https://console.groq.com", file=sys.stderr)

# --- Configuration ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_STT_ENDPOINT = os.getenv("GROQ_STT_ENDPOINT", "https://api.groq.com/openai/v1/audio/transcriptions")
MODEL = "whisper-large-v3"
SAMPLE_RATE = 16000
CHANNELS = 1

async def transcribe(audio_path: str, language: str, args):
    """Sends the audio file to Groq for transcription, specifying the language."""
    if not GROQ_API_KEY:
        print("Error: GROQ_API_KEY is not set.", file=sys.stderr)
        return

    print(f"Transcribing...", file=sys.stderr)
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}"}

    try:
        async with aiohttp.ClientSession() as session:
            with open(audio_path, "rb") as f:
                form_data = aiohttp.FormData()
                form_data.add_field("file", f, filename=os.path.basename(audio_path))
                form_data.add_field("model", MODEL)
                form_data.add_field("language", language)

                async with session.post(GROQ_STT_ENDPOINT, headers=headers, data=form_data) as resp:
                    if resp.status != 200:
                        print(f"Error: API request failed with status {resp.status}", file=sys.stderr)
                        print(f"Response: {await resp.text()}", file=sys.stderr)
                        return

                    response_json = await resp.json()
                    transcript = response_json.get("text")

                    # Handle the case where the API returns an empty string for silence
                    if transcript is not None and transcript.strip():
                        print(f">>> {transcript}")

                        # Generate a response using local function
                        response_text = generate_response(transcript)
                        print(f"<<< {response_text}")

                        # Only attempt TTS if not disabled
                        if not args.disable_tts:
                            try:
                                # Initialize TTS and speak the response
                                tts = TTSManager(voice=args.tts_voice)
                                await tts.speak(response_text)
                            except Exception as tts_error:
                                print(f"TTS error occurred but continuing: {tts_error}", file=sys.stderr)
                    else:
                        # If transcript is empty or just whitespace, do nothing.
                        print("Transcription empty, likely silence.", file=sys.stderr)


    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)

def generate_response(transcript: str) -> str:
    """Generate a natural-sounding response based on the detected intent.

    Args:
        transcript (str): The detected user intent or transcribed text

    Returns:
        str: A natural-sounding response text
    """
    # Map of patterns to friendly responses
    transcript_lower = transcript.lower().strip()

    # Greeting patterns
    if any(greeting in transcript_lower for greeting in ["hello", "hi", "hey", "greetings"]):
        responses = [
            "Hello there! How can I assist you today?",
            "Hi! I'm your AI assistant. What can I do for you?",
            "Hey! It's great to talk with you. How can I help?"
        ]
        return random.choice(responses)

    # Questions about capabilities
    elif any(phrase in transcript_lower for phrase in ["what can you do", "help me with", "your capabilities"]):
        return "I can help with answering questions, providing information, or just having a conversation. What would you like to talk about?"

    # Weather-related
    elif "weather" in transcript_lower:
        responses = [
            "I don't have real-time weather data, but I'd be happy to discuss other topics!",
            "I can't check the weather right now, but I'm here to chat about other things.",
            "While I can't access weather information, I can help with many other questions you might have."
        ]
        return random.choice(responses)

    # Time-related
    elif "time" in transcript_lower:
        responses = [
            "I don't have access to the current time, but I'm still here to help with other questions!",
            "I can't tell you the exact time, but I'm ready to assist with other topics.",
            "While I can't check the time for you, I'd be happy to chat about something else."
        ]
        return random.choice(responses)

    # Feelings/emotions
    elif any(phrase in transcript_lower for phrase in ["how are you", "how do you feel", "are you well"]):
        responses = [
            "I'm doing well, thanks for asking! How about you?",
            "I'm operating normally and ready to help. How are you today?",
            "I'm great! It's nice of you to ask. How can I assist you?"
        ]
        return random.choice(responses)

    # Thanks
    elif any(phrase in transcript_lower for phrase in ["thank you", "thanks", "appreciate it"]):
        responses = [
            "You're welcome! Is there anything else I can help with?",
            "Happy to help! Let me know if you need anything else.",
            "No problem at all! What else would you like to talk about?"
        ]
        return random.choice(responses)

    # Goodbye
    elif any(phrase in transcript_lower for phrase in ["goodbye", "bye", "see you", "talk to you later"]):
        responses = [
            "Goodbye! Feel free to chat again anytime.",
            "See you later! It was nice talking with you.",
            "Take care! I'll be here if you need me again."
        ]
        return random.choice(responses)

    # Default responses for unrecognized inputs
    else:
        responses = [
            f"I heard you say: '{transcript}'. How can I help with that?",
            f"I understood you said: '{transcript}'. What would you like to know about this?",
            f"You mentioned: '{transcript}'. Could you tell me more about what you're looking for?"
        ]
        return random.choice(responses)

def record_with_vad(args):
    """Records from the microphone using VAD and returns a filepath or None if silent."""
    vad = webrtcvad.Vad(args.aggressiveness)
    frame_size = int(SAMPLE_RATE * args.frame_duration / 1000)

    pre_buffer_frames = int(args.pre_buffer * SAMPLE_RATE / frame_size)
    ring_buffer = collections.deque(maxlen=pre_buffer_frames)

    recorded_frames = []
    is_recording = False
    silent_frames_after_speech = 0
    max_silent_frames = int(args.silence_duration * SAMPLE_RATE / frame_size)

    print("Listening... (speak to start recording)", file=sys.stderr)

    with sd.InputStream(samplerate=SAMPLE_RATE, channels=CHANNELS, blocksize=frame_size, dtype='int16') as stream:
        while True:
            frame, _ = stream.read(frame_size)
            frame_bytes = frame.tobytes()
            is_speech = vad.is_speech(frame_bytes, SAMPLE_RATE)

            if not is_recording:
                ring_buffer.append(frame_bytes)
                if is_speech:
                    is_recording = True
                    print("Speech detected, recording...", file=sys.stderr)
                    recorded_frames.extend(list(ring_buffer))
                    ring_buffer.clear()
            else:
                recorded_frames.append(frame_bytes)
                if not is_speech:
                    silent_frames_after_speech += 1
                    if silent_frames_after_speech > max_silent_frames:
                        print("End of speech detected.", file=sys.stderr)
                        break
                else:
                    silent_frames_after_speech = 0

    if not recorded_frames:
        return None

    recording_bytes = b''.join(recorded_frames)
    recording_array = np.frombuffer(recording_bytes, dtype=np.int16)

    # --- Silence Check ---
    # Calculate the Root Mean Square (RMS) energy of the audio
    rms = np.sqrt(np.mean(recording_array.astype(np.float32)**2))
    if rms < args.energy_threshold:
        print(f"Silent audio detected (RMS: {rms:.2f}), ignoring.", file=sys.stderr)
        return None

    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
        sf.write(tmp_file.name, recording_array, SAMPLE_RATE)
        return tmp_file.name

async def main():
    parser = argparse.ArgumentParser(description="A continuous STT client for Groq using VAD.")

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-l", "--listen", action="store_true", help="Listen continuously and transcribe speech automatically.")
    group.add_argument("-f", "--file", type=str, help="Path to an audio file to transcribe (one-shot).")

    vad_group = parser.add_argument_group('VAD & Audio Tuning')
    vad_group.add_argument("--aggressiveness", type=int, default=3, choices=range(4), help="VAD aggressiveness (0-3).")
    vad_group.add_argument("--silence-duration", type=float, default=0.7, help="Seconds of silence to wait before stopping.")
    vad_group.add_argument("--frame-duration", type=int, default=30, choices=[10, 20, 30], help="Duration of each audio frame in ms.")
    vad_group.add_argument("--pre-buffer", type=float, default=0.3, help="Seconds of audio to keep before speech starts.")
    vad_group.add_argument("--energy-threshold", type=float, default=50.0, help="RMS energy threshold to consider audio as non-silent.")

    parser.add_argument("--language", type=str, default="en", help="Language of the speech (ISO 639-1 code).")
    parser.add_argument("--tts-voice", type=str, default="Arista-PlayAI", help="Voice to use for TTS responses (e.g. Arista-PlayAI, Fritz-PlayAI).")
    parser.add_argument("--disable-tts", action="store_true", help="Disable TTS responses and use text-only mode.")

    args = parser.parse_args()

    if args.listen:
        print("Starting continuous listening mode. Press Ctrl+C to stop.", file=sys.stderr)
        try:
            while True:
                temp_audio_path = None
                try:
                    temp_audio_path = record_with_vad(args)
                    if temp_audio_path:
                        await transcribe(temp_audio_path, args.language, args)
                finally:
                    if temp_audio_path and os.path.exists(temp_audio_path):
                        os.remove(temp_audio_path)
                print("\nListening for next utterance...", file=sys.stderr)
        except KeyboardInterrupt:
            print("\nStopping listener.", file=sys.stderr)

    elif args.file:
        if not os.path.exists(args.file):
            print(f"Error: Audio file not found at '{args.file}'", file=sys.stderr)
            return
        await transcribe(args.file, args.language, args)

if __name__ == "__main__":
    asyncio.run(main())
