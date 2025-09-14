# Speech Recognition with Groq Integration

A powerful speech-to-text and text-to-speech system using Groq's API for natural, conversational interactions.

## Features

- 🎤 **Speech-to-Text**: Accurate transcription with Groq's whisper-large-v3 model
- 🔊 **Text-to-Speech**: Natural voice responses using Groq's playai-tts model
- 🧠 **LLM Integration**: Smart responses powered by Groq's LLM models
- ⏱️ **Voice Activity Detection**: Automatically detect when you start and stop speaking
- 🛑 **Interruption Handling**: Stop long responses with interruption keywords
- 📏 **Context-aware Responses**: Response length adjusts based on query type

## Interruption Handling

The system now supports interruptions during longer responses (like stories or explanations) using trigger keywords:

- **Interruption Keywords**: "sorry", "stop", "wait", "pause", "hold on", "cancel", "nevermind", "enough"
- **How it Works**:
  1. Start speaking any of the interruption keywords
  2. The system will immediately stop the current TTS playback
  3. Your new request will be processed with a short acknowledgment

Example:
```
AI: "Once upon a time in a land far away, there lived a..."
You: "Sorry, I'd like to watch a video instead"
AI: "Sure, what would you like to watch?"
```

## Usage

### Basic Usage

```bash
# Run with default settings
python speech.py --listen

# Adjust speech detection sensitivity
python speech.py --listen --energy-threshold 100.0

# Use a specific voice
python speech.py --listen --tts-voice Fritz-PlayAI
```

### Response Length Control

The system automatically adjusts response length based on the type of request:

| Request Type | Default Token Limit | Example Triggers |
|--------------|---------------------|------------------|
| Stories      | 500 tokens          | "tell me a story", "once upon a time" |
| Explanations | 300 tokens          | "explain", "what is", "how does", "tell me about" |
| Conversation | 150 tokens          | Regular conversation, questions |
| Actions      | 50 tokens           | "open", "play", "show", commands |

You can customize these limits:

```bash
# For longer stories
python speech.py --listen --story-tokens 700

# For shorter explanations
python speech.py --listen --explanation-tokens 200
```

## Command Line Options

### Speech Detection

| Option | Default | Description |
|--------|---------|-------------|
| `--energy-threshold` | 100.0 | Audio energy threshold (higher = less sensitive) |
| `--aggressiveness` | 3 | VAD aggressiveness (0-3) |
| `--silence-duration` | 0.7 | Seconds of silence to wait before stopping |
| `--pre-buffer` | 0.3 | Seconds of audio to keep before speech starts |

### TTS Options

| Option | Default | Description |
|--------|---------|-------------|
| `--tts-voice` | Arista-PlayAI | Voice to use for TTS |
| `--disable-tts` | False | Use text-only mode without speech |

### LLM Options

| Option | Default | Description |
|--------|---------|-------------|
| `--llm-model` | llama-3.1-8b-instant | Groq LLM model to use |
| `--story-tokens` | 500 | Max tokens for stories |
| `--explanation-tokens` | 300 | Max tokens for explanations |
| `--conversation-tokens` | 150 | Max tokens for conversations |
| `--action-tokens` | 50 | Max tokens for action commands |

## Available Voices

### PlayAI Voices

| Category | Voices |
|----------|--------|
| Warm | Arista-PlayAI, Henri-PlayAI |
| Friendly | Fritz-PlayAI, Nova-PlayAI |
| Calm | Grover-PlayAI, Quinn-PlayAI |
| Soothing | Sammy-PlayAI, Ivy-PlayAI |

## Requirements

- Python 3.8+
- Groq API key (set in `.env` file)
- Required packages (see `requirements.txt`)

## Setup

1. Install required packages:
```bash
pip install -r requirements.txt
```

2. Create `.env` file with your Groq API key:
```
GROQ_API_KEY=your_key_here
```

3. Accept terms for the TTS model (one-time setup):
   - Visit https://console.groq.com/playground?model=playai-tts
   - Log in and accept the terms of use

## Troubleshooting

### False Speech Detection
- Increase `--energy-threshold` (try 150-200)
- Decrease VAD `--aggressiveness` (try 2 or 1)

### TTS Issues
- Ensure you've accepted the TTS model terms
- Check your Groq API key is valid
- Use `--disable-tts` to verify transcription works

### Interruption Not Working
- Speak louder when interrupting
- Start with an interruption keyword ("sorry", "stop", etc.)
- Try increasing microphone sensitivity