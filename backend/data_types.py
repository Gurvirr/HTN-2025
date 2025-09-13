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

@dataclass
class SpeechMessage:
    """Specific data structure for speech input"""
    speech: str
    confidence: Optional[float] = None
    language: Optional[str] = None
    mode: Optional[AppMode] = None

@dataclass
class CommandDoneMessage:
    """Specific data structure for command completion"""
    command_id: str
    status: Literal["completed", "failed", "partial"] = "completed"
    error_message: Optional[str] = None
    execution_time: Optional[float] = None

@dataclass
class StoryDoneMessage:
    """Specific data structure for story completion"""
    story_id: str
    duration: Optional[float] = None
    user_engagement: Optional[str] = None

@dataclass
class OutgoingAction:
    """Standardized outgoing action to glasses"""
    action: ActionType
    data: Dict[str, Any]
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    action_id: Optional[str] = None

@dataclass
class TTSAction:
    """Specific data structure for TTS commands"""
    speech: str
    voice_type: Optional[str] = None
    speed: Optional[float] = None
    volume: Optional[float] = None

@dataclass
class PlaySongAction:
    """Specific data structure for song playback"""
    song_title: str
    artist: Optional[str] = None
    playlist: Optional[str] = None
    volume: Optional[float] = None

@dataclass
class PlayVideoAction:
    """Specific data structure for video playback"""
    video_url: str
    title: Optional[str] = None
    duration: Optional[int] = None
    quality: Optional[str] = None

@dataclass
class CreateVisualAction:
    """Specific data structure for visual creation"""
    visual_prompt: str
    style: Optional[str] = None
    duration: Optional[int] = None
    animation_type: Optional[str] = None

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

# Helper functions for type conversion
class MessageFactory:
    """Factory class for creating typed messages"""

    @staticmethod
    def create_incoming_message(message_type: MessageType, raw_data: Dict[str, Any], session_id: Optional[str] = None) -> IncomingMessage:
        """Create a typed incoming message"""
        return IncomingMessage(
            message_type=message_type,
            data=raw_data,
            session_id=session_id
        )

    @staticmethod
    def create_speech_message(raw_data: Dict[str, Any]) -> SpeechMessage:
        """Create a typed speech message"""
        return SpeechMessage(
            speech=raw_data.get("speech", ""),
            confidence=raw_data.get("confidence"),
            language=raw_data.get("language"),
            mode=raw_data.get("mode")
        )

    @staticmethod
    def create_command_done_message(raw_data: Dict[str, Any]) -> CommandDoneMessage:
        """Create a typed command done message"""
        return CommandDoneMessage(
            command_id=raw_data.get("command_id", ""),
            status=raw_data.get("status", "completed"),
            error_message=raw_data.get("error_message"),
            execution_time=raw_data.get("execution_time")
        )

    @staticmethod
    def create_story_done_message(raw_data: Dict[str, Any]) -> StoryDoneMessage:
        """Create a typed story done message"""
        return StoryDoneMessage(
            story_id=raw_data.get("story_id", ""),
            duration=raw_data.get("duration"),
            user_engagement=raw_data.get("user_engagement")
        )

class ActionFactory:
    """Factory class for creating typed actions"""

    @staticmethod
    def create_tts_action(speech: str, **kwargs) -> OutgoingAction:
        """Create a TTS action"""
        tts_data = TTSAction(speech=speech, **kwargs)
        return OutgoingAction(
            action="tts",
            data=tts_data.__dict__
        )

    @staticmethod
    def create_play_song_action(song_title: str, **kwargs) -> OutgoingAction:
        """Create a play song action"""
        song_data = PlaySongAction(song_title=song_title, **kwargs)
        return OutgoingAction(
            action="play_song",
            data=song_data.__dict__
        )

    @staticmethod
    def create_play_video_action(video_url: str, **kwargs) -> OutgoingAction:
        """Create a play video action"""
        video_data = PlayVideoAction(video_url=video_url, **kwargs)
        return OutgoingAction(
            action="play_video",
            data=video_data.__dict__
        )

    @staticmethod
    def create_visual_action(visual_prompt: str, **kwargs) -> OutgoingAction:
        """Create a visual creation action"""
        visual_data = CreateVisualAction(visual_prompt=visual_prompt, **kwargs)
        return OutgoingAction(
            action="create_visual",
            data=visual_data.__dict__
        )

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
