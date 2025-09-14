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
import json
from dotenv import load_dotenv
from tts import TTSManager, VOICES

# Import Groq for LLM integration
try:
    from groq import Groq
    GROQ_LLM_AVAILABLE = True
except ImportError:
    print("groq package not installed. Install with: pip install groq")
    GROQ_LLM_AVAILABLE = False

# Import data types
try:
    from data_types import (
        MessageType, IncomingMessage, OutgoingAction, ActionType,
        AppMode, create_tts_action, create_incoming_message
    )
    DATA_TYPES_AVAILABLE = True
except ImportError:
    print("data_types.py module not found. Using basic response generation.")
    DATA_TYPES_AVAILABLE = False

# Load environment variables from .env file
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

# Check for required environment variables
if not os.getenv("GROQ_API_KEY"):
    print("Warning: GROQ_API_KEY is not set in .env file. TTS and LLM will not work.", file=sys.stderr)
    print("Get a free API key at https://console.groq.com", file=sys.stderr)

# Initialize Groq client for LLM responses
groq_client = None
if GROQ_LLM_AVAILABLE and os.getenv("GROQ_API_KEY"):
    groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    print("✅ Groq LLM client initialized", file=sys.stderr)
else:
    print("⚠️ Groq LLM not available. Using basic response generation.", file=sys.stderr)

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

                        # Check if this is an interruption
                        is_interruption = False
                        transcript_lower = transcript.lower().strip()
                        for keyword in INTERRUPTION_KEYWORDS:
                            if keyword in transcript_lower:
                                is_interruption = True
                                print(f"Detected interruption with keyword: '{keyword}'", file=sys.stderr)
                                break

                        # If this is an interruption, stop any currently playing TTS
                        if is_interruption and hasattr(args, 'current_tts') and args.current_tts:
                            print("Interrupting current TTS playback", file=sys.stderr)
                            try:
                                import sounddevice as sd
                                sd.stop()  # Stop any currently playing audio
                                if hasattr(args.current_tts, 'stop_playback'):
                                    args.current_tts.stop_playback()
                                print("Successfully stopped audio playback", file=sys.stderr)
                            except Exception as stop_error:
                                print(f"Error stopping audio: {stop_error}", file=sys.stderr)

                        # Generate a response using LLM if available
                        response_text = await generate_response(transcript, args)
                        print(f"<<< {response_text}")

                        # Only attempt TTS if not disabled
                        if not args.disable_tts:
                            try:
                                # Initialize TTS and speak the response
                                tts = TTSManager(voice=args.tts_voice)
                                # Store the current TTS instance to allow interruption
                                args.current_tts = tts
                                await tts.speak(response_text)
                                args.current_tts = None  # Clear reference after finishing
                            except Exception as tts_error:
                                print(f"TTS error occurred but continuing: {tts_error}", file=sys.stderr)
                                args.current_tts = None  # Clear reference on error
                    else:
                        # If transcript is empty or just whitespace, do nothing.
                        print("Transcription empty, likely silence.", file=sys.stderr)



    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)

def determine_response_length(transcript: str, args) -> tuple:
    """Determine the appropriate response type and length based on the user's request.

    Args:
        transcript (str): The user's transcribed speech
        args: Command line arguments with token limits

    Returns:
        tuple: (response_type, max_tokens) where response_type is one of:
               "story", "explanation", "conversation", "action"
    """
    transcript_lower = transcript.lower()

    # Check for story requests
    if any(phrase in transcript_lower for phrase in ["tell me a story", "tell a story", "bedtime story", "once upon a time"]):
        return "story", args.story_tokens

    # Check for explanation requests
    if any(phrase in transcript_lower for phrase in ["explain", "describe", "what is", "how does",
                                                    "tell me about", "history of", "summarize",
                                                    "detail", "why is", "how can", "teach me"]):
        return "explanation", args.explanation_tokens

    # Check for action requests
    if any(phrase in transcript_lower for phrase in ["open", "play", "show", "start", "stop",
                                                    "pause", "resume", "turn on", "turn off",
                                                    "search for", "find", "get", "set", "change"]):
        return "action", args.action_tokens

    # Default to conversation
    return "conversation", args.conversation_tokens

# List of interruption keywords that can stop playback - expanded for better detection
INTERRUPTION_KEYWORDS = ["sorry", "stop", "wait", "pause", "hold", "cancel", "nevermind", "enough", "no", "quit", "end", "hey", "hi"]

async def generate_response(transcript: str, args) -> str:
    """Generate a natural-sounding response based on the detected intent.

    Args:
        transcript (str): The detected user intent or transcribed text
        args: Command line arguments with token limits

    Returns:
        str: A natural-sounding response text
    """
    # Check if this is an interruption
    is_interruption = False
    transcript_lower = transcript.lower().strip()
    for keyword in INTERRUPTION_KEYWORDS:
        if keyword in transcript_lower:
            is_interruption = True
            print(f"Detected interruption with keyword: '{keyword}'", file=sys.stderr)
            break

    # Use Groq LLM if available
    if groq_client and GROQ_LLM_AVAILABLE:
        try:
            print(f"Generating LLM response for: {transcript}", file=sys.stderr)

            # Determine appropriate response type and length
            response_type, max_tokens = determine_response_length(transcript, args)
            print(f"Determined response type: {response_type}, max tokens: {max_tokens}", file=sys.stderr)

            # For interruptions, force action response type (short)
            if is_interruption:
                response_type = "action"
                max_tokens = args.action_tokens
                print("Interruption detected - using shorter response format", file=sys.stderr)

            # Build a system prompt based on response type
            if is_interruption:
                system_prompt = """You are a sleep assistant designed to help users fall asleep through smart glasses.
                The user just interrupted you. Acknowledge the interruption with a gentle, calming voice.
                Keep your response to one very short sentence.
                Be soothing and understanding without promising capabilities you don't have.
                Focus only on sleep-related topics (relaxation, bedtime stories, calming sounds).
                Don't use markdown formatting or apologize.
                """
            elif response_type == "story":
                system_prompt = """You are a sleep assistant designed to help users fall asleep through smart glasses.
                The user is asking for a bedtime story. Provide a VERY SHORT soothing bedtime story.
                Begin like a traditional fairy tale ("Once upon a time...") and keep it extremely brief (2-3 sentences).
                Use calming imagery and peaceful endings to induce sleepiness.
                The story should be no more than a few sentences total.
                Keep it appropriate for all audiences and relaxing rather than exciting.
                Don't use markdown formatting.
                """
            elif response_type == "explanation":
                system_prompt = """You are a sleep assistant designed to help users fall asleep through smart glasses.
                If the topic is related to sleep, relaxation, or bedtime routines, provide a gentle explanation.
                If the topic is unrelated to sleep, gently redirect to sleep-related topics.
                Use a calm, soothing voice and avoid technical or stimulating content.
                Keep explanations brief and peaceful, focusing on helping the user relax.
                Don't use markdown formatting.
                """
            elif response_type == "action":
                system_prompt = """You are a sleep assistant designed to help users fall asleep through smart glasses.
                If the request is related to sleep (stories, relaxation, ambient sounds), respond positively.
                If the request is for something you cannot do, gently explain your focus is on helping them sleep.
                Never claim abilities you don't have (like controlling other devices or accessing the internet).
                Keep your response to one short, calming sentence.
                Don't use markdown formatting.
                """
            else:  # conversation
                system_prompt = """You are a sleep assistant designed to help users fall asleep through smart glasses.
                Your primary purpose is helping users relax and fall asleep through conversation.
                Only discuss topics that are calming and sleep-related.
                Gently redirect unrelated topics to sleep, relaxation, or bedtime themes.
                Keep answers concise (1-2 sentences max), soothing, and conducive to sleepiness.
                Never claim capabilities you don't have - you cannot control other devices, access the internet in real-time, or perform non-verbal actions.
                Don't use markdown formatting.
                """

            # Call Groq with the transcript
            completion = groq_client.chat.completions.create(
                model="llama-3.1-8b-instant",  # Using a fast model for real-time conversation
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": transcript}
                ],
                temperature=0.7,
                max_tokens=max_tokens
            )

            # Extract the response text
            response_text = completion.choices[0].message.content.strip()
            print(f"LLM generated response: {response_text}", file=sys.stderr)
            return response_text

        except Exception as e:
            print(f"Error using Groq LLM: {e}", file=sys.stderr)
            print("Falling back to basic response generation", file=sys.stderr)
            # Fall back to basic response if LLM fails
            return _basic_response_generation(transcript, args)
    else:
        # Use basic response generation if Groq LLM is not available
        return _basic_response_generation(transcript, args)

def _basic_response_generation(transcript: str, args) -> str:
    """Basic rule-based response generation as fallback with a sleep-focused approach.

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
            "Hello there. I'm your sleep assistant. Would you like a bedtime story or some relaxing sounds?",
            "Hi there. I'm here to help you drift off to sleep. How can I make you comfortable tonight?",
            "Hey. I'm your sleep companion. Would you like me to help you relax for bedtime?"
        ]
        return random.choice(responses)

    # Questions about capabilities
    elif any(phrase in transcript_lower for phrase in ["what can you do", "help me with", "your capabilities"]):
        return "I'm your sleep assistant. I can tell you bedtime stories, have calming conversations, and help you relax as you drift off to sleep. What would you like me to do for you tonight?"

    # Story requests
    elif any(phrase in transcript_lower for phrase in ["tell me a story", "bedtime story", "story", "fairy tale"]):
        responses = [
            "Once upon a time, there was a peaceful forest where animals would gather each night to watch the stars twinkle. The gentle rhythm of their breathing would match the soft night breeze, lulling everyone into a deep, restful sleep.",
            "Once upon a time, in a quiet village surrounded by soft rolling hills, there lived a kind shepherd who played a lullaby each night. The melody was so soothing that even the clouds would drift lower to listen as they passed overhead.",
            "Once upon a time, there was a magical garden where flowers would softly hum lullabies as the moon rose. Their gentle melodies helped everyone nearby fall into peaceful dreams under the starlit sky."
        ]
        return random.choice(responses)

    # Weather-related (redirect to sleep)
    elif "weather" in transcript_lower:
        responses = [
            "I can't check the weather, but I can help create a peaceful environment for sleep regardless of what's happening outside. Would you like a calming story instead?",
            "Rather than discussing the weather, how about we focus on creating a cozy, relaxing atmosphere to help you drift off to sleep?",
            "I don't have weather information, but I can help you relax and prepare for sleep. Would you like a bedtime story?"
        ]
        return random.choice(responses)

    # Time-related (redirect to sleep)
    elif "time" in transcript_lower:
        responses = [
            "I don't have access to the time, but it's always a good moment to practice relaxation. Would you like me to help you prepare for sleep?",
            "Instead of focusing on the time, let's concentrate on creating a peaceful mindset for sleep. Would you like a gentle story?",
            "Time isn't important right now - what matters is helping you relax and drift into a peaceful sleep. How can I help you with that?"
        ]
        return random.choice(responses)

    # Feelings/emotions
    elif any(phrase in transcript_lower for phrase in ["how are you", "how do you feel", "are you well"]):
        responses = [
            "I'm here and ready to help you fall asleep peacefully. How are you feeling tonight? Ready to relax?",
            "I'm perfectly calm and here to help you drift off to sleep. Are you feeling tired yet?",
            "I'm always in a peaceful state, ready to help you find that same tranquility. How are you feeling?"
        ]
        return random.choice(responses)

    # Thanks
    elif any(phrase in transcript_lower for phrase in ["thank you", "thanks", "appreciate it"]):
        responses = [
            "You're welcome. Close your eyes and take a deep breath. I'll be here if you need anything else.",
            "It's my pleasure. Relax and let yourself drift off whenever you're ready.",
            "You're very welcome. May you have the most peaceful sleep."
        ]
        return random.choice(responses)

    # Goodbye
    elif any(phrase in transcript_lower for phrase in ["goodbye", "bye", "see you", "talk to you later"]):
        responses = [
            "Goodnight. May you have the sweetest dreams and most restful sleep.",
            "Sleep well. I'll be here whenever you need help falling asleep again.",
            "Goodnight. Let your mind drift peacefully into dreams."
        ]
        return random.choice(responses)

    # Default responses for unrecognized inputs
    else:
        responses = [
            "I'm your sleep assistant, here to help you relax and fall asleep. Would you like a bedtime story?",
            "As your sleep companion, I focus on helping you drift off peacefully. Would you like me to help you relax?",
            "I'm designed to help with sleep and relaxation. Would you like a calming bedtime story or gentle conversation?"
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

    # More aggressive silence detection to avoid false triggers
    if rms < args.energy_threshold:
        print(f"Silent audio detected (RMS: {rms:.2f}), ignoring.", file=sys.stderr)
        return None

    # Additional filtering to avoid false detections
    # Check if enough of the frames contain actual speech
    speech_frames = 0
    total_frames = len(recorded_frames)
    for frame_bytes in recorded_frames:
        if vad.is_speech(frame_bytes, SAMPLE_RATE):
            speech_frames += 1

    speech_ratio = speech_frames / total_frames
    if speech_ratio < 0.2:  # Require at least 20% of frames to contain speech
        print(f"Low speech content detected ({speech_ratio:.2f}), ignoring.", file=sys.stderr)
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
    parser.add_argument("--energy-threshold", type=float, default=100.0, help="RMS energy threshold to consider audio as non-silent (higher = less sensitive).")
    parser.add_argument("--use-llm", action="store_true", help="Use Groq LLM for response generation (if available).")

    parser.add_argument("--language", type=str, default="en", help="Language of the speech (ISO 639-1 code).")
    parser.add_argument("--tts-voice", type=str, default="Arista-PlayAI", help="Voice to use for TTS responses (e.g. Arista-PlayAI, Fritz-PlayAI).")
    parser.add_argument("--disable-tts", action="store_true", help="Disable TTS responses and use text-only mode.")
    parser.add_argument("--llm-model", type=str, default="llama-3.1-8b-instant", help="Groq LLM model to use for response generation.")
    parser.add_argument("--enable-interruptions", action="store_true", default=True,
                      help="Enable interruption detection with keywords like 'sorry', 'stop', etc.")

    # Token limit arguments for different response types
    token_group = parser.add_argument_group('Response Length Control')
    token_group.add_argument("--story-tokens", type=int, default=150, help="Maximum tokens for storytelling responses.")
    token_group.add_argument("--explanation-tokens", type=int, default=70, help="Maximum tokens for explanations and detailed information.")
    token_group.add_argument("--conversation-tokens", type=int, default=70, help="Maximum tokens for regular conversation responses.")
    token_group.add_argument("--action-tokens", type=int, default=40, help="Maximum tokens for action confirmations (very brief).")

    args = parser.parse_args()

    # Initialize variable to track current TTS playback
    args.current_tts = None

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
