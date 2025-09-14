# Smart Glasses WebSocket API Documentation

## Overview
This document describes the WebSocket messages used for communication between the smart glasses client and the backend server. The server uses Socket.IO for real-time bidirectional communication and includes AI-powered sleep assistance with automatic music/video search capabilities.

## Connection
- **URL**: `ws://localhost:5000` (or your server URL)
- **Protocol**: Socket.IO
- **CORS**: Enabled for all origins

## Message Types

### 1. Connection Events

#### `connect`
**Direction**: Client → Server (automatic)
**Description**: Fired when client connects to server

**Server Response**: `connection_status`
```json
{
  "status": "connected",
  "mode": "conversational",
  "session_id": "SuUeTQL5ytMr0fY7AAAB"
}
```

#### `disconnect`
**Direction**: Client → Server (automatic)
**Description**: Fired when client disconnects

---

### 2. Incoming Messages (Client → Server)

#### `receive_speech`
**Description**: Send speech input from glasses to server. The server will automatically search for music/videos if needed.
**Required Fields**: `speech`
**Optional Fields**: Any additional context data

```json
{
  "speech": "can you play calm music"
}
```

#### `done_command`
**Description**: Notify server that a command has been completed
**Required Fields**: `command_id`
**Optional Fields**: `status`, `duration`

```json
{
  "command_id": "tts_12345",
  "status": "completed",
  "duration": 3.2
}
```

#### `done_story`
**Description**: Notify server that a story/visual has finished
**Required Fields**: `story_id`
**Optional Fields**: `duration`

```json
{
  "story_id": "visual_67890",
  "duration": 15.5
}
```

#### `config_send`
**Description**: Send configuration updates to server
**Required Fields**: At least one config parameter
**Available Fields**: `config_type`, `voice_type`, `volume`, `closed_captions`

```json
{
  "config_type": "tts",
  "voice_type": "default",
  "volume": 0.8,
  "closed_captions": true
}
```

---

### 3. Outgoing Actions (Server → Client)

All outgoing actions follow this structure:
```json
{
  "action": "action_type",
  "data": { /* action-specific data */ },
  "timestamp": "2025-09-13T23:56:27.685Z",
  "action_id": null
}
```

#### `tts`
**Description**: Text-to-speech command with config-aware parameters
```json
{
  "action": "tts",
  "data": {
    "speech": "Sure, playing some calm, relaxing music for you.",
    "voice_type": "default",
    "speed": 1.0,
    "volume": 1.0,
    "closed_captions": false
  },
  "timestamp": "2025-09-13T23:56:27.685Z",
  "action_id": null
}
```

#### `play_song`
**Description**: Play music command with automatic YouTube search integration
```json
{
  "action": "play_song",
  "data": {
    "song_title": "Beautiful Relaxing Music for Stress Relief ~ Calming Music ~ Meditation, Relaxation, Sleep, Spa",
    "artist": "Meditation Relax Music",
    "video_url": "https://www.youtube.com/watch?v=lFcSrYw-ARY"
  },
  "timestamp": "2025-09-13T23:56:27.685Z",
  "action_id": null
}
```

#### `play_video`
**Description**: Play video command with YouTube URL
```json
{
  "action": "play_video",
  "data": {
    "video_url": "https://youtube.com/watch?v=dQw4w9WgXcQ",
    "title": "Never Gonna Give You Up",
    "duration": "3:32"
  },
  "timestamp": "2025-09-13T23:45:00Z",
  "action_id": null
}
```

#### `create_visual`
**Description**: Create visual/AR content for sleep assistance
```json
{
  "action": "create_visual",
  "data": {
    "visual_prompt": "A peaceful night sky with gentle stars",
    "style": "calming",
    "duration": 30,
    "animation_type": "fade_in"
  },
  "timestamp": "2025-09-13T23:45:00Z",
  "action_id": null
}
```

#### `change_mode`
**Description**: Change application mode
```json
{
  "action": "change_mode",
  "data": {
    "mode": "sheep"
  },
  "timestamp": "2025-09-13T23:45:00Z",
  "action_id": null
}
```

#### `acknowledge`
**Description**: Simple acknowledgment
```json
{
  "action": "acknowledge",
  "data": {
    "message": "Configuration updated successfully"
  },
  "timestamp": "2025-09-13T23:45:00Z",
  "action_id": null
}
```

#### `error`
**Description**: Error notification
```json
{
  "action": "error",
  "data": {
    "error_message": "Sorry, I encountered an error processing that request: [error details]",
    "error_code": "PROCESSING_ERROR"
  },
  "timestamp": "2025-09-13T23:45:00Z",
  "action_id": null
}
```

#### `config_send`
**Description**: Send configuration to glasses
```json
{
  "action": "config_send",
  "data": {
    "config_type": "tts",
    "voice_type": "default",
    "volume": 1.0,
    "closed_captions": false
  },
  "timestamp": "2025-09-13T23:45:00Z",
  "action_id": null
}
```

---

### 4. Status Events (Server → Client)

#### `mode_changed`
**Description**: Notification when app mode changes
```json
{
  "mode": "sheep"
}
```

---

## Application Modes

The system supports the following modes:
- `conversational`: General conversation mode (default)
- `youtube`: Video watching mode
- `sheep`: Sleep/relaxation mode with counting sheep
- `visual_story`: Visual storytelling mode
- `zzz`: Deep sleep mode

## Configuration System

### Config Structure
The server maintains a `Config` object with these parameters:

```json
{
  "config_type": "tts",
  "voice_type": "default",
  "volume": 1.0,
  "closed_captions": false
}
```

### Configuration Behavior
- Config changes are applied immediately to all subsequent TTS actions
- The server automatically uses current config settings for TTS
- Config can be updated via `config_send` message from client
- Server can send config updates to client via `config_send` action

## AI-Powered Features

### Automatic Content Search
The server includes intelligent content enhancement:

1. **Music Search**: When users request music, the system automatically searches YouTube for relevant tracks
2. **Video Search**: Video requests trigger YouTube search for appropriate content
3. **Sleep Focus**: All content is optimized for sleep assistance and relaxation

### Context Enhancement Process
1. User sends speech via `receive_speech`
2. AI analyzes if content search is needed
3. If needed, searches YouTube for relevant content
4. Enhances response with found URLs and metadata
5. Sends appropriate actions (`play_song`, `play_video`, etc.)

## Client Implementation Guidelines

### 1. Connection Setup
```javascript
import io from 'socket.io-client';

const socket = io('http://localhost:5000');

socket.on('connect', () => {
  console.log('Connected to server');
});

socket.on('connection_status', (data) => {
  console.log('Connection status:', data);
  // data: {status: "connected", mode: "conversational", session_id: "..."}
});
```

### 2. Sending Speech
```javascript
function sendSpeech(speechText) {
  socket.emit('receive_speech', {
    speech: speechText
  });
}

// Example usage
sendSpeech("can you play calm music");
```

### 3. Handling Actions
```javascript
// Handle TTS with config-aware parameters
socket.on('tts', (action) => {
  const { speech, voice_type, volume, closed_captions } = action.data;
  console.log(`TTS: "${speech}" (voice: ${voice_type}, volume: ${volume})`);
  
  // Implement TTS playback with config
  playTTS(speech, { voice_type, volume, closed_captions });
  
  // Send completion notification (optional)
  socket.emit('done_command', {
    command_id: action.action_id || 'tts_completed',
    status: 'completed',
    duration: 2.5
  });
});

// Handle music with YouTube URLs
socket.on('play_song', (action) => {
  const { song_title, artist, video_url } = action.data;
  console.log(`Playing: "${song_title}" by ${artist}`);
  console.log(`URL: ${video_url}`);
  
  // Use video_url for actual playback
  playMusic(video_url);
});

// Handle video playback
socket.on('play_video', (action) => {
  const { video_url, title, duration } = action.data;
  console.log(`Playing video: "${title}" (${duration})`);
  
  // Implement video player
  playVideo(video_url);
});

// Handle visual content
socket.on('create_visual', (action) => {
  const { visual_prompt, style, duration } = action.data;
  console.log(`Creating visual: "${visual_prompt}" (${style}, ${duration}s)`);
  
  // Implement AR/visual rendering
  createVisual(visual_prompt, style, duration);
});

// Handle mode changes
socket.on('change_mode', (action) => {
  const { mode } = action.data;
  console.log(`Changing to mode: ${mode}`);
  
  // Update UI/behavior for new mode
  setMode(mode);
});
```

### 4. Configuration Management
```javascript
// Send config updates to server
function updateConfig(configUpdates) {
  socket.emit('config_send', configUpdates);
}

// Handle config updates from server
socket.on('config_send', (action) => {
  const config = action.data;
  console.log('Config updated:', config);
  
  // Apply config to local TTS/audio systems
  applyConfig(config);
});

// Example usage
updateConfig({
  voice_type: 'female_voice_1',
  volume: 0.7,
  closed_captions: true
});
```

### 5. Error Handling
```javascript
socket.on('error', (action) => {
  console.error('Server error:', action.data.error_message);
  // Handle error appropriately in UI
});

socket.on('disconnect', () => {
  console.log('Disconnected from server');
  // Implement reconnection logic
  setTimeout(() => socket.connect(), 1000);
});
```

## HTTP Endpoints (Debugging)

The server provides HTTP endpoints for debugging and monitoring:

- `GET /health` - Health check and server status
- `GET /state` - Current application state and config
- `GET /history?limit=10` - Recent command history
- `POST /mode` - Directly set application mode

## Implementation Notes
z
1. **Timestamps**: All timestamps are in ISO 8601 format
2. **Action IDs**: Currently set to `null` but structure supports future tracking
3. **Config Integration**: TTS actions automatically use current config settings
4. **Search Integration**: Music/video requests trigger automatic YouTube search
5. **Sleep Focus**: System is optimized for sleep assistance and relaxation content
6. **Error Handling**: Server provides detailed error messages for debugging
7. **Session Management**: Server maintains session state and command history
8. **Reconnection**: Client should implement graceful reconnection logic

## Example Flow

1. **Client connects** → Server sends `connection_status`
2. **User says "play calm music"** → Client sends `receive_speech`
3. **Server searches YouTube** → Finds relaxing music
4. **Server responds** → Sends `tts` (announcement) + `play_song` (with YouTube URL)
5. **Client plays content** → Uses provided YouTube URL for playback
6. **Client notifies completion** → Sends `done_command` (optional)
