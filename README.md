# sleepAR

A soothing voice-activated AR/AI system designed to help you fall asleep through smart glasses, featuring bedtime stories, calming conversations, and relaxing experiences. sleepAR combines augmented reality with artificial intelligence for an immersive sleep experience.

## Features

- **Voice Interaction**: Hands-free operation through speech recognition
- **Bedtime Stories**: Brief, calming fairy tales to help you drift off
- **Interruption Handling**: Easily interrupt long responses with keywords like "stop" or "wait"
- **Context-Aware Responses**: Response length adapts to the type of request
- **Soothing Voice Options**: Multiple calming voice options to choose from

## Setup

### Requirements

- Python 3.8+
- Groq API key (for speech-to-text and text-to-speech)
- Required Python packages (see `requirements.txt`)

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/HTN-2025.git
   cd HTN-2025
   ```

2. Install dependencies:
   ```bash
   pip install -r backend/requirements.txt
   ```

3. Create a `.env` file in the `backend` directory with your Groq API key:
   ```
   GROQ_API_KEY=your_key_here
   ```

4. Accept the terms for Groq's TTS model (one-time setup):
   - Visit https://console.groq.com/playground?model=playai-tts
   - Log in and accept the terms of use

## Usage

Run the speech recognition system:

```bash
python backend/speech.py --listen
```

### Command Line Options

| Option | Default | Description |
|--------|---------|-------------|
| `--energy-threshold` | 100.0 | Audio energy threshold (higher = less sensitive) |
| `--silence-duration` | 0.7 | Seconds of silence to wait before stopping |
| `--tts-voice` | Indigo | Voice to use for TTS responses |
| `--disable-tts` | False | Use text-only mode without speech |
| `--story-tokens` | 150 | Maximum tokens for stories |
| `--explanation-tokens` | 300 | Maximum tokens for explanations |

## Interrupting Responses

To interrupt the assistant while it's speaking, simply say any of these keywords:
- "sorry"
- "stop"
- "wait"
- "pause"
- "hold"
- "cancel" 
- "nevermind"
- "enough"
- "hey"
- "hi"

## Modes

sleepAR operates across several modes:

- **Conversation Mode**: General sleep-focused chat
- **Story Mode**: Triggered when asking for bedtime stories
- **Explanation Mode**: For explaining sleep-related topics
- **Action Mode**: For simple commands and confirmations

## Available Voices

The system uses Groq's playai-tts voices. Some recommended options include:

| Voice | Style | Description |
|-------|-------|-------------|
| Indigo | Default | A balanced, soothing voice (default) |
| Sammy-PlayAI | Soothing | A calming, gentle voice |
| Ivy-PlayAI | Soothing | A soft, peaceful voice |
| Arista-PlayAI | Warm | A warm, comforting voice |
| Henri-PlayAI | Warm | A deep, relaxing voice |

## Architecture

The sleepAR system consists of three main components:

1. **Speech Recognition**: Uses Groq's whisper-large-v3 model for accurate transcription
2. **Language Model**: Uses Groq's LLM for generating appropriate responses
3. **Text-to-Speech**: Uses Groq's playai-tts model for natural voice responses

## Technical Details

sleepAR is built with:
- Python for the backend
- aiohttp for API calls
- webrtcvad for voice activity detection
- sounddevice/soundfile for audio handling
- Groq API for AI capabilities

## Project Structure

```
HTN-2025/
├── backend/
│   ├── speech.py          # Main speech recognition system
│   ├── tts.py             # Text-to-speech integration
│   ├── requirements.txt   # Python dependencies
│   └── .env               # Environment variables (API keys)
└── README.md              # This file
```

## Acknowledgments

- sleepAR was built for Hack the North 2025
- Uses Groq API for AI capabilities
- Combines AR (Augmented Reality) with AI for an immersive sleep experience