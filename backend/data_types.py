from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Literal, Union
from datetime import datetime


# Message Types
MessageType = Literal[
    "receive_speech",
    "done_command",
    "done_story"
]

# Action Types that can be sent to glasses
ActionType = Literal[
    "tts",
    "play_song",
    "play_video",
    "create_visual",
    "change_mode",
    "acknowledge",
    "error"
]

# App Modes
AppMode = Literal[
    "sheep",
    "youtube",
    "conversational",
    "visual_story",
    "zzz"
]

@dataclass
class IncomingMessage:
    """Standardized incoming message from glasses"""
    message_type: MessageType
    data: Dict[str, Any]
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    session_id: Optional[str] = None

# Note: Specific message parsing can be done directly from raw_data dict when needed

@dataclass
class OutgoingAction:
    """Standardized outgoing action to glasses"""
    action: ActionType
    data: Dict[str, Any]
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    action_id: Optional[str] = None

@dataclass
class CommandHistory:
    """Represents a command that was executed"""
    timestamp: str
    command_type: str
    data: Dict[str, Any]
    mode: AppMode
    success: bool = True
    response_time: Optional[float] = None

@dataclass
class UserPreferences:
    """User preferences and settings"""
    voice_type: str = "default"
    background: str = "space"
    timer_enabled: bool = True
    volume: float = 1.0
    language: str = "en"
    visual_style: str = "default"

@dataclass
class AppState:
    """Maintains the application state"""
    current_mode: AppMode = "conversational"
    command_history: List[CommandHistory] = field(default_factory=list)
    user_preferences: UserPreferences = field(default_factory=UserPreferences)
    active_session_id: Optional[str] = None
    last_activity: str = field(default_factory=lambda: datetime.now().isoformat())
    context_memory: Dict[str, Any] = field(default_factory=dict)

@dataclass
class LLMContext:
    """Complete context sent to LLM for processing"""
    current_message: IncomingMessage
    app_state: AppState
    recent_history: List[CommandHistory]
    available_actions: List[ActionType]
    available_modes: List[AppMode]
    session_info: Dict[str, Any] = field(default_factory=dict)

@dataclass
class LLMResponse:
    """Response from LLM processor"""
    actions: List[OutgoingAction]
    new_mode: Optional[AppMode] = None
    context_updates: Dict[str, Any] = field(default_factory=dict)
    confidence: Optional[float] = None
    reasoning: Optional[str] = None

@dataclass
class ErrorInfo:
    """Error information structure"""
    error_code: str
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

# Simple helper functions for creating actions and messages
def create_incoming_message(message_type: MessageType, raw_data: Dict[str, Any], session_id: Optional[str] = None) -> IncomingMessage:
    """Create a typed incoming message"""
    return IncomingMessage(
        message_type=message_type,
        data=raw_data,
        session_id=session_id
    )

def create_action(action_type: ActionType, **data) -> OutgoingAction:
    """Create an outgoing action with the given type and data"""
    return OutgoingAction(
        action=action_type,
        data=data
    )

# Convenience functions for common actions
def create_tts_action(speech: str, voice_type: Optional[str] = None, speed: Optional[float] = None, volume: Optional[float] = None) -> OutgoingAction:
    """Create a TTS action"""
    return create_action("tts", speech=speech, voice_type=voice_type, speed=speed, volume=volume)

def create_play_song_action(song_title: str, artist: Optional[str] = None, playlist: Optional[str] = None, volume: Optional[float] = None) -> OutgoingAction:
    """Create a play song action"""
    return create_action("play_song", song_title=song_title, artist=artist, playlist=playlist, volume=volume)

def create_play_video_action(video_url: str, title: Optional[str] = None, duration: Optional[int] = None, quality: Optional[str] = None) -> OutgoingAction:
    """Create a play video action"""
    return create_action("play_video", video_url=video_url, title=title, duration=duration, quality=quality)

def create_visual_action(visual_prompt: str, style: Optional[str] = None, duration: Optional[int] = None, animation_type: Optional[str] = None) -> OutgoingAction:
    """Create a visual creation action"""
    return create_action("create_visual", visual_prompt=visual_prompt, style=style, duration=duration, animation_type=animation_type)

def create_error_action(error_message: str, error_code: Optional[str] = None) -> OutgoingAction:
    """Create an error action"""
    return create_action("error", error_message=error_message, error_code=error_code)

# Utility functions
def serialize_dataclass(obj) -> Union[Dict[str, Any], List[Any], Any]:
    """Serialize a dataclass to dictionary"""
    if hasattr(obj, '__dict__'):
        return {k: serialize_dataclass(v) if hasattr(v, '__dict__') else v
                for k, v in obj.__dict__.items()}
    elif isinstance(obj, list):
        return [serialize_dataclass(item) for item in obj]
    elif isinstance(obj, dict):
        return {k: serialize_dataclass(v) for k, v in obj.items()}
    else:
        return obj

def validate_message_type(message_type: str) -> bool:
    """Validate if message type is supported"""
    return message_type in ["receive_speech", "done_command", "done_story"]

def validate_action_type(action_type: str) -> bool:
    """Validate if action type is supported"""
    return action_type in ["tts", "play_song", "play_video", "create_visual", "change_mode", "acknowledge", "error"]

def validate_app_mode(mode: str) -> bool:
    """Validate if app mode is supported"""
    return mode in ["sheep", "youtube", "conversational", "visual_story", "zzz"]
