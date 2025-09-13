# Smart Glasses Agent Socket System

A modular socket-based backend for smart glasses that routes all inputs through an LLM processor.

## Architecture Overview

```
Glasses → AgentSocket → LLM Processor → Actions → Glasses
```

- **AgentSocket**: Main socket server that handles all communication
- **Data Types**: Strongly typed message structures 
- **LLM Integration**: Single point where all inputs get processed by AI
- **Modular Actions**: Clean separation of different output actions

## Quick Start

### 1. Install Dependencies
```bash
cd HTN-2025/backend
pip install -r requirements.txt
```

### 2. Run the Server
```bash
python app.py
```
Server starts on `http://localhost:5000`

### 3. Test the Connection
```bash
# Interactive testing
python test_client.py

# Automated test sequence  
python test_client.py --auto
```

## Core Components

### 🏗️ **AgentSocket Class**
Main socket server class that:
- Listens for incoming messages from glasses
- Routes all inputs to LLM processor
- Executes actions returned by LLM
- Maintains app state and command history

### 📊 **Data Types** (`data_types.py`)
Strongly typed structures for:
- **Incoming Messages**: `receive_speech`, `done_command`, `done_story`
- **Outgoing Actions**: `tts`, `play_song`, `play_video`, `create_visual`
- **App State**: Current mode, preferences, command history
- **LLM Context**: Complete context sent to AI processor

### 🧪 **Test Client** (`test_client.py`)
- Interactive testing interface
- Automated test sequences
- Simulates glasses sending messages

## Message Flow

### 📥 **Incoming Messages**
```python
# Speech input
{
    "speech": "Play some music",
    "confidence": 0.95,
    "mode": "conversational"
}

# Command completion
{
    "command_id": "cmd_001", 
    "status": "completed",
    "execution_time": 1.5
}

# Story completion
{
    "story_id": "story_001",
    "duration": 30.0,
    "user_engagement": "high"
}
```

### 📤 **Outgoing Actions**
```python
# Text-to-speech
{
    "action": "tts",
    "data": {
        "speech": "Playing your favorite song",
        "voice_type": "default"
    }
}

# Play song
{
    "action": "play_song", 
    "data": {
        "song_title": "Bohemian Rhapsody",
        "artist": "Queen"
    }
}

# Create visual
{
    "action": "create_visual",
    "data": {
        "visual_prompt": "A sunset over mountains",
        "style": "realistic"
    }
}
```

## LLM Integration

### 🤖 **Where to Add Your AI**
In `app.py`, replace the `_process_with_llm()` method:

```python
async def _process_with_llm(self, context: LLMContext) -> LLMResponse:
    """
    THIS IS WHERE YOU INTEGRATE YOUR LLM
    """
    
    # Example with OpenAI
    prompt = f"""
    You are an AI assistant for smart glasses.
    
    Current message: {context.current_message.data}
    App mode: {context.app_state.current_mode}
    Recent history: {context.recent_history[-3:]}
    
    Return actions as JSON array.
    """
    
    response = await openai.ChatCompletion.acreate(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )
    
    # Parse response and return LLMResponse
    return LLMResponse(actions=parsed_actions)
```

### 🎯 **Context Provided to LLM**
- Current incoming message and data
- App state (mode, preferences, session info)
- Recent command history (last 10 commands)
- Available actions and modes
- Session duration and metadata

## App Modes

| Mode | Description | Example Commands |
|------|-------------|------------------|
| `conversational` | General chat | "How are you?", "Tell me a joke" |
| `sheep` | Game/counting mode | "Count sheep", "Jump over fence" |
| `youtube` | Video watching | "Play cat videos", "Search tutorials" |
| `visual_story` | Visual storytelling | "Tell me a story", "Show me adventure" |
| `zzz` | Sleep mode | Minimal responses, "wake up" to exit |

## Available Actions

| Action | Purpose | Data Fields |
|--------|---------|-------------|
| `tts` | Speak text | `speech`, `voice_type`, `speed` |
| `play_song` | Play music | `song_title`, `artist`, `playlist` |
| `play_video` | Show video | `video_url`, `title`, `quality` |
| `create_visual` | Generate image | `visual_prompt`, `style`, `duration` |
| `change_mode` | Switch app mode | `mode` |
| `acknowledge` | Confirm action | `message` |

## HTTP Endpoints

For debugging and monitoring:

- `GET /health` - Server health check
- `GET /state` - Current app state  
- `GET /history?limit=10` - Command history
- `POST /mode` - Change app mode

## Testing Examples

### 🎤 **Speech Testing**
```python
await client.send_speech("Play my favorite song")
await client.send_speech("Tell me a bedtime story", mode="visual_story")
await client.send_speech("Count some sheep", mode="sheep")
```

### ✅ **Command Completion**
```python
await client.send_done_command("cmd_001", "completed")
await client.send_done_command("cmd_002", "failed")
```

### 📖 **Story Completion**
```python
await client.send_done_story("story_001", duration=45.0)
```

## Development Workflow

1. **Start Server**: `python app.py`
2. **Test with Client**: `python test_client.py`
3. **Check Logs**: Server logs all incoming/outgoing messages
4. **Integrate LLM**: Replace `_process_with_llm()` method
5. **Add New Actions**: Extend `ActionFactory` in `data_types.py`

## Key Features

- ✅ **Type Safety**: All messages use typed data structures
- ✅ **Single Handler**: All inputs route through one modular handler  
- ✅ **LLM Ready**: Built-in context building for AI integration
- ✅ **State Management**: Persistent app state and command history
- ✅ **Testing Tools**: Comprehensive test client included
- ✅ **Monitoring**: HTTP endpoints for debugging
- ✅ **Extensible**: Easy to add new message types and actions

## Next Steps

1. **Integrate Your LLM**: Replace the placeholder in `_process_with_llm()`
2. **Add Authentication**: Secure the socket connections
3. **Add Persistence**: Save state to database
4. **Extend Actions**: Add more action types as needed
5. **Add Validation**: Input validation and error handling