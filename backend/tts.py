import os
import sys
import tempfile
import asyncio
import aiohttp
import random
import re
from pathlib import Path
from dotenv import load_dotenv
import sounddevice as sd
import soundfile as sf

# Load environment variables from .env file
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

# --- Configuration ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_TTS_ENDPOINT = os.getenv("GROQ_TTS_ENDPOINT", "https://api.groq.com/openai/v1/audio/speech")
MODEL = "playai-tts"  # Groq's TTS model
VOICE = "Arista-PlayAI"  # Default voice - warm and conversational

# Available voices for playai-tts model
VOICES = {
    "warm": ["Arista-PlayAI", "Henri-PlayAI"],
    "friendly": ["Fritz-PlayAI", "Nova-PlayAI"],
    "calm": ["Grover-PlayAI", "Quinn-PlayAI"],
    "soothing": ["Sammy-PlayAI", "Ivy-PlayAI"]
}

class TTSManager:
    """Manages text-to-speech operations using Groq's TTS API."""

    # Constructor is now defined above with the speak method

    async def generate_speech(self, text: str) -> str:
        """Generates speech from text using Groq's TTS API.

        Args:
            text (str): The text to convert to speech

        Returns:
            str: Path to the generated audio file or empty string if failed
        """
        if not GROQ_API_KEY:
            print("Error: GROQ_API_KEY is not set.", file=sys.stderr)
            return ""

        if not text or not text.strip():
            print("Error: Empty text provided for TTS.", file=sys.stderr)
            return ""

        print(f"Generating speech for: {text}", file=sys.stderr)
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }

        try:
            # Create a unique filename for this audio
            output_path = Path(self.temp_dir) / f"tts_{hash(text)}.wav"

            async with aiohttp.ClientSession() as session:
                form_data = {
                    "model": self.model,
                    "voice": self.voice,
                    "input": text,
                    "response_format": "wav"
                }

                async with session.post(
                    GROQ_TTS_ENDPOINT,
                    headers=headers,
                    json=form_data
                ) as resp:
                    if resp.status != 200:
                        error_text = await resp.text()
                        print(f"Error: API request failed with status {resp.status}", file=sys.stderr)
                        print(f"Response: {error_text}", file=sys.stderr)

                        # Check for terms acceptance error
                        if "terms acceptance" in error_text and "model_terms_required" in error_text:
                            print("\nIMPORTANT: You need to accept the terms for the TTS model.", file=sys.stderr)
                            print("Please visit https://console.groq.com/playground?model=playai-tts", file=sys.stderr)
                            print("Log in with your Groq account and accept the terms of use.", file=sys.stderr)

                        return ""

                    # Save the audio data to a file
                    audio_data = await resp.read()
                    with open(output_path, "wb") as f:
                        f.write(audio_data)

                    print(f"Speech generated successfully: {output_path}", file=sys.stderr)
                    return str(output_path)

        except aiohttp.ClientError as e:
            print(f"Network error connecting to Groq API: {e}", file=sys.stderr)
            return ""
        except Exception as e:
            print(f"An unexpected error occurred: {e}", file=sys.stderr)
            return ""

    def __init__(self, model=MODEL, voice=VOICE):
        self.model = model
        self.voice = voice
        self.temp_dir = tempfile.mkdtemp(prefix="groq_tts_")
        self.is_playing = False  # Track playback status
        self.interrupted = False  # Track if playback was interrupted

        # Validate environment
        if not GROQ_API_KEY:
            print("Error: GROQ_API_KEY is not set.", file=sys.stderr)

    def stop_playback(self):
        """Stops any currently playing audio."""
        try:
            self.interrupted = True  # Set interrupted flag first
            if self.is_playing:
                sd.stop()
                self.is_playing = False
                print("Audio playback stopped.", file=sys.stderr)
                # Force a small delay to ensure audio is fully stopped
                import time
                time.sleep(0.1)
            return True
        except Exception as e:
            print(f"Error stopping audio: {e}", file=sys.stderr)
            return False

    async def speak(self, text: str) -> bool:
        """Generates speech and plays it with support for interruptions.

        Args:
            text (str): The text to convert to speech and play

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Reset interruption flag
            self.interrupted = False

            # Preprocess text to be shorter for stories
            if len(text) > 300 and any(word in text.lower() for word in ["once upon a time", "story", "tale"]):
                print("Detected story - using shorter format", file=sys.stderr)
                text = " ".join(text.split()[:100]) + "..."

            # Generate speech for the complete text
            print(f"Generating speech for text", file=sys.stderr)
            audio_path = await self.generate_speech(text)
            if not audio_path or audio_path == "":
                print("Could not generate speech audio. See error above.", file=sys.stderr)
                return False

            # Play the audio file with interruption checking
            try:
                data, samplerate = sf.read(audio_path)

                # Calculate duration for logging
                duration = len(data) / samplerate
                print(f"Playing audio (duration: {duration:.2f}s)", file=sys.stderr)

                self.is_playing = True
                sd.play(data, samplerate)

                # Wait for playback with frequent interruption checks
                import time
                start_time = time.time()
                while sd.get_stream().active and time.time() - start_time < duration + 0.5:
                    if self.interrupted:
                        sd.stop()
                        print("TTS interrupted during playback", file=sys.stderr)
                        return False
                    await asyncio.sleep(0.1)  # Small sleep to allow interruption

                self.is_playing = False
                return True

            except Exception as audio_err:
                print(f"Error playing audio: {audio_err}", file=sys.stderr)
                self.is_playing = False
                return False

        except Exception as e:
            print(f"Failed to speak: {e}", file=sys.stderr)
            self.is_playing = False
            return False

    def clean_up(self):
        """Removes temporary audio files."""
        import shutil
        try:
            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
                print(f"Cleaned up temporary TTS files from {self.temp_dir}", file=sys.stderr)
        except Exception as e:
            print(f"Failed to clean up TTS temp files: {e}", file=sys.stderr)

# Helper function for generating natural-sounding responses
def generate_response(intent: str) -> str:
    """Generate a natural-sounding response based on the detected intent.

    Args:
        intent (str): The detected user intent or transcribed text

    Returns:
        str: A natural-sounding response text
    """
    # Map of patterns to friendly responses
    intent_lower = intent.lower().strip()

    # Greeting patterns
    if any(greeting in intent_lower for greeting in ["hello", "hi", "hey", "greetings"]):
        responses = [
            "Hello there! How can I assist you today?",
            "Hi! I'm your AI assistant. What can I do for you?",
            "Hey! It's great to talk with you. How can I help?"
        ]
        return random.choice(responses)

    # Questions about capabilities
    elif any(phrase in intent_lower for phrase in ["what can you do", "help me with", "your capabilities"]):
        return "I can help with answering questions, providing information, or just having a conversation. What would you like to talk about?"

    # Weather-related
    elif "weather" in intent_lower:
        responses = [
            "I don't have real-time weather data, but I'd be happy to discuss other topics!",
            "I can't check the weather right now, but I'm here to chat about other things.",
            "While I can't access weather information, I can help with many other questions you might have."
        ]
        return random.choice(responses)

    # Time-related
    elif "time" in intent_lower:
        responses = [
            "I don't have access to the current time, but I'm still here to help with other questions!",
            "I can't tell you the exact time, but I'm ready to assist with other topics.",
            "While I can't check the time for you, I'd be happy to chat about something else."
        ]
        return random.choice(responses)

    # Feelings/emotions
    elif any(phrase in intent_lower for phrase in ["how are you", "how do you feel", "are you well"]):
        responses = [
            "I'm doing well, thanks for asking! How about you?",
            "I'm operating normally and ready to help. How are you today?",
            "I'm great! It's nice of you to ask. How can I assist you?"
        ]
        return random.choice(responses)

    # Thanks
    elif any(phrase in intent_lower for phrase in ["thank you", "thanks", "appreciate it"]):
        responses = [
            "You're welcome! Is there anything else I can help with?",
            "Happy to help! Let me know if you need anything else.",
            "No problem at all! What else would you like to talk about?"
        ]
        return random.choice(responses)

    # Goodbye
    elif any(phrase in intent_lower for phrase in ["goodbye", "bye", "see you", "talk to you later"]):
        responses = [
            "Goodbye! Feel free to chat again anytime.",
            "See you later! It was nice talking with you.",
            "Take care! I'll be here if you need me again."
        ]
        return random.choice(responses)

    # Default responses for unrecognized inputs
    else:
        responses = [
            f"I heard you say: '{intent}'. How can I help with that?",
            f"I understood you said: '{intent}'. What would you like to know about this?",
            f"You mentioned: '{intent}'. Could you tell me more about what you're looking for?"
        ]
        return random.choice(responses)

async def main():
    """Example usage of the TTS module."""
    import argparse

    parser = argparse.ArgumentParser(description="Groq TTS Client")
    parser.add_argument("-t", "--text", type=str, help="Text to convert to speech")
    parser.add_argument("-v", "--voice", type=str, default=VOICE, help="Voice to use")
    parser.add_argument("-m", "--model", type=str, default=MODEL, help="Model to use")
    args = parser.parse_args()

    if not args.text:
        parser.print_help()
        return

    tts = TTSManager(model=args.model, voice=args.voice)

    try:
        success = await tts.speak(args.text)
        if success:
            print("Speech played successfully.")
        else:
            print("Failed to generate or play speech.")
    finally:
        tts.clean_up()

if __name__ == "__main__":
    asyncio.run(main())
