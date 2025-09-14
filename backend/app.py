import logging
import os
import json
import asyncio
import websockets
from datetime import datetime
from typing import Dict, List, Any, Optional, Set
from dotenv import load_dotenv
from data_types import (
        MessageType, IncomingMessage, OutgoingAction, ActionType, AppMode,
        AppState, CommandHistory, LLMContext, LLMResponse, Config,
        create_incoming_message, create_tts_action, create_tts_with_config,
        create_play_song_action, create_play_video_action, create_visual_action, 
        create_error_action, create_config_action, update_config,
        serialize_dataclass, convert_structured_to_actions
)
from dotenv import load_dotenv

try:
    import websockets
except ImportError:
    print("websockets is required. Install with: pip install websockets")
    exit(1)

# Import Pydantic models if available
try:
    from data_types import LLMResponse_Structured, ContextEnhancementDecision
    PYDANTIC_AVAILABLE = LLMResponse_Structured is not None and ContextEnhancementDecision is not None
except ImportError:
    PYDANTIC_AVAILABLE = False
    LLMResponse_Structured = None
    ContextEnhancementDecision = None

# Import Groq
try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    print("groq is required. Install with: pip install groq")
    GROQ_AVAILABLE = False
    Groq = None

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AgentWebSocket:
    """Main WebSocket class for handling all smart glasses communication"""
    
    # Define available actions and modes using our types
    AVAILABLE_ACTIONS: list[ActionType] = ["tts", "play_song", "play_video", "create_visual", "change_mode", "acknowledge", "config_send"]
    AVAILABLE_MODES: list[AppMode] = ["sheep", "youtube", "conversational", "visual_story", "zzz"]

    def __init__(self, host: str = "0.0.0.0", port: int = 5000) -> None:
        self.host = host
        self.port = port
        self.app_state = AppState()
        self.connected_clients: Set[websockets.WebSocketServerProtocol] = set()
        
        # Initialize Groq client if available
        self.groq_client = None
        if GROQ_AVAILABLE:
            load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))
            api_key = os.environ.get("GROQ_API_KEY")
            if api_key:
                self.groq_client = Groq(api_key=api_key)
                logger.info("✅ Groq client initialized")
            else:
                logger.warning("⚠️  GROQ_API_KEY environment variable not set. Using placeholder LLM.")
        else:
            logger.warning("⚠️  Groq not available. Using placeholder LLM.")

    async def handle_client(self, websocket, path=None):
        """Handle a new WebSocket client connection"""
        self.connected_clients.add(websocket)
        client_id = id(websocket)
        logger.info(f"Client {client_id} connected")
        self.app_state.active_session_id = str(client_id)
        
        # Send connection acknowledgment
        connection_data = {
            'type': 'connection',
            'status': 'connected',
            'mode': self.app_state.current_mode,
            'session_id': str(client_id)
        }
        await websocket.send(json.dumps(connection_data))
        logger.info(f"📤 WEBSOCKET SEND → {client_id}: connection_status | Data: {connection_data}")
        
        try:
            async for message in websocket:
                await self.handle_message(websocket, message)
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Client {client_id} disconnected")
        finally:
            self.connected_clients.discard(websocket)
            if self.app_state.active_session_id == str(client_id):
                self.app_state.active_session_id = None

    async def handle_message(self, websocket, raw_message):
        """Handle incoming WebSocket message"""
        client_id = id(websocket)
        try:
            data = json.loads(raw_message)
            message_type = data.get('type')
            
            logger.info(f"📥 WEBSOCKET RECV ← {client_id}: {message_type} | Data: {data}")
            
            if message_type == "receive_speech":
                await self._handle_incoming_message(str(client_id), "receive_speech", data)
            elif message_type == "done_command":
                await self._handle_incoming_message(str(client_id), "done_command", data)
            elif message_type == "button_press":
                await self._handle_incoming_message(str(client_id), "button_press", data)
            elif message_type == "config_update":
                await self._handle_incoming_message(str(client_id), "config_update", data)
            elif message_type == "mode_change":
                await self._handle_incoming_message(str(client_id), "mode_change", data)
            else:
                logger.warning(f"Unknown message type: {message_type}")
                
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON received from client {client_id}: {raw_message}")
        except Exception as e:
            logger.error(f"Error handling message from client {client_id}: {e}")

    async def send_to_client(self, client_id: str, data: Dict[str, Any]) -> None:
        """Send data to a specific client"""
        message = json.dumps(data)
        for websocket in self.connected_clients:
            if str(id(websocket)) == client_id:
                try:
                    await websocket.send(message)
                    return
                except websockets.exceptions.ConnectionClosed:
                    self.connected_clients.discard(websocket)
                    break
        logger.warning(f"Client {client_id} not found or disconnected")

    async def broadcast_to_all(self, data: Dict[str, Any]) -> None:
        """Broadcast data to all connected clients"""
        if not self.connected_clients:
            return
        
        message = json.dumps(data)
        disconnected = set()
        
        for websocket in self.connected_clients:
            try:
                await websocket.send(message)
            except websockets.exceptions.ConnectionClosed:
                disconnected.add(websocket)
        
        # Remove disconnected clients
        self.connected_clients -= disconnected

    async def _handle_incoming_message(self, sid: str, message_type: MessageType, raw_data: Dict[str, Any]) -> None:
        """
        Single handler for all incoming messages
        Creates typed message and routes to LLM processor
        """
        try:
            logger.info(f"Received {message_type}: {raw_data}")

            # Print last 3 messages from history to show it's working
            self._print_recent_history(3)

            # Create typed incoming message
            incoming_message = create_incoming_message(
                message_type=message_type,
                raw_data=raw_data,
                session_id=sid
            )

            # Handle config updates
            if message_type == "config_send":
                await self._handle_config_update(raw_data)

            # Add to command history
            command = CommandHistory(
                timestamp=datetime.now().isoformat(),
                command_type=message_type,
                data=raw_data,
                mode=self.app_state.current_mode
            )
            self.app_state.command_history.append(command)

            # Update last activity
            self.app_state.last_activity = datetime.now().isoformat()

            # Build context for LLM
            llm_context = self._build_llm_context(incoming_message)

            # Process with LLM (this is where you'll integrate your AI)
            llm_response = await self._process_with_llm(llm_context)

            # Execute the actions from LLM
            await self._execute_llm_actions(sid, llm_response)

        except Exception as e:
            logger.error(f"Error handling {message_type}: {e}")
            error_action = create_error_action(
                f"Sorry, I encountered an error processing that request: {str(e)}"
            )
            await self._send_action(sid, error_action)

    async def _handle_config_update(self, raw_data: Dict[str, Any]) -> None:
        """Handle incoming config updates"""
        try:
            # Update the config with new values
            if "config_type" in raw_data:
                self.app_state.config.config_type = raw_data["config_type"]
            if "voice_type" in raw_data:
                self.app_state.config.voice_type = raw_data["voice_type"]
            if "volume" in raw_data:
                self.app_state.config.volume = float(raw_data["volume"])
            if "closed_captions" in raw_data:
                self.app_state.config.closed_captions = bool(raw_data["closed_captions"])
            
            logger.info(f"✅ Config updated: {self.app_state.config}")
        except Exception as e:
            logger.error(f"❌ Error updating config: {e}")

    def _create_tts_with_config(self, speech: str) -> OutgoingAction:
        """Create a TTS action using current config settings"""
        return create_tts_with_config(speech, self.app_state.config)

    async def send_config(self, sid: str, config: Optional[Config] = None) -> None:
        """Send config action to glasses"""
        if config is None:
            config = self.app_state.config
        action = create_config_action(config)
        await self._send_action(sid, action)

    def _build_llm_context(self, incoming_message: IncomingMessage) -> LLMContext:
        """Build comprehensive context for LLM processing"""

        # Get recent command history (last 10 commands)
        recent_history = self.app_state.command_history[-10:]

        context = LLMContext(
            current_message=incoming_message,
            app_state=self.app_state,
            recent_history=recent_history,
            available_actions=self.AVAILABLE_ACTIONS,
            available_modes=self.AVAILABLE_MODES,
            session_info={
                'session_duration': self._calculate_session_duration(),
                'total_commands': len(self.app_state.command_history)
            }
        )

        return context

    def _calculate_session_duration(self) -> float:
        """Calculate how long the current session has been active"""
        if not self.app_state.command_history:
            return 0.0

        first_command = self.app_state.command_history[0]
        start_time = datetime.fromisoformat(first_command.timestamp)
        current_time = datetime.now()
        return (current_time - start_time).total_seconds()

    async def _search_youtube_video(self, search_query: str, limit: int = 1) -> Optional[Dict[str, Any]]:
        """Search for YouTube videos and return the first result"""
        try:
            import yt_dlp
        except ImportError:
            logger.warning("⚠️  yt-dlp not available. Install with: pip install yt-dlp")
            return None
            
        try:
            logger.info(f"🔍 Searching YouTube for: {search_query}")
            
            # Configure yt-dlp for search
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,  # Get full video info
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Search for videos using ytsearch: prefix
                search_results = ydl.extract_info(f'ytsearch1:{search_query}', download=False)
                
                if search_results and 'entries' in search_results and len(search_results['entries']) > 0:
                    video = search_results['entries'][0]
                    
                    if video and video.get('id'):
                        video_data = {
                            'video_url': video.get('webpage_url') or f"https://youtube.com/watch?v={video.get('id')}",
                            'title': video.get('title'),
                            'duration': video.get('duration_string') or str(video.get('duration', 'Unknown')),
                            'channel': video.get('uploader') or video.get('channel'),
                            'thumbnail': video.get('thumbnail')
                        }
                        logger.info(f"✅ Found video: {video_data['title']}")
                        return video_data
                
                logger.warning(f"❌ No YouTube videos found for: {search_query}")
                return None
                    
        except Exception as e:
            logger.error(f"❌ Error searching YouTube: {e}")
            return None

    async def _search_music(self, search_query: str, limit: int = 1) -> Optional[Dict[str, Any]]:
        """Search for music on YouTube and return the first result"""
        try:
            import yt_dlp
        except ImportError:
            logger.warning("⚠️  yt-dlp not available. Install with: pip install yt-dlp")
            return None
            
        try:
            logger.info(f"🎵 Searching for music: {search_query}")
            
            # Add music-specific terms to improve search results
            music_query = f"{search_query} music audio song"
            
            # Configure yt-dlp for search
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,  # Get full video info
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Search for music using ytsearch: prefix
                search_results = ydl.extract_info(f'ytsearch1:{music_query}', download=False)
                
                if search_results and 'entries' in search_results and len(search_results['entries']) > 0:
                    music = search_results['entries'][0]
                    
                    if music and music.get('id'):
                        music_data = {
                            'song_title': music.get('title'),
                            'artist': music.get('uploader') or music.get('channel'),
                            'video_url': music.get('webpage_url') or f"https://youtube.com/watch?v={music.get('id')}",
                            'duration': music.get('duration_string') or str(music.get('duration', 'Unknown')),
                            'thumbnail': music.get('thumbnail')
                        }
                        logger.info(f"✅ Found music: {music_data['song_title']} by {music_data['artist']}")
                        return music_data
                
                logger.warning(f"❌ No music found for: {search_query}")
                return None
                    
        except Exception as e:
            logger.error(f"❌ Error searching for music: {e}")
            return None

    async def _decide_context_enhancement(self, context: LLMContext) -> Optional[Dict[str, Any]]:
        """Use LLM to decide if context should be enhanced and how"""
        if not (self.groq_client and PYDANTIC_AVAILABLE):
            return None
            
        message_type = context.current_message.message_type
        if message_type != "receive_speech":
            return None
            
        speech_text = context.current_message.data.get("speech", "")
        
        try:
            logger.info(f"🤔 Analyzing message for context enhancement: {speech_text}")
            
            system_prompt = """You are a context enhancement analyzer. Determine if the user's message requires additional context (like searching for videos, music, images, etc.) before processing.

ENHANCEMENT TYPES:
- "youtube": User wants to watch/see videos, documentaries, tutorials, shows
- "music": User wants to listen to songs, albums, playlists  
- "images": User wants to see pictures, photos, artwork
- "none": No enhancement needed

RESPONSE FORMAT:
- should_enhance: true/false
- enhancement_type: "youtube", "music", "images", or null
- search_query: concise search terms (max 20 tokens), or null

EXAMPLES:
- "show me funny cat videos" → should_enhance: true, enhancement_type: "youtube", search_query: "funny cat videos"
- "I want to watch a documentary about space" → should_enhance: true, enhancement_type: "youtube", search_query: "space documentary"
- "how are you today?" → should_enhance: false, enhancement_type: null, search_query: null
- "what's the weather like?" → should_enhance: false, enhancement_type: null, search_query: null"""

            completion = self.groq_client.chat.completions.create(
                model="openai/gpt-oss-120b",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"User message: \"{speech_text}\""}
                ],
                response_format={
                    "type": "json_schema", 
                    "json_schema": {
                        "name": "context_enhancement_decision",
                        "schema": ContextEnhancementDecision.model_json_schema()
                    }
                },
                temperature=0.3,
                max_tokens=200  # Enough for JSON response
            )
            
            response_content = completion.choices[0].message.content
            logger.info(f"🤔 Enhancement decision: {response_content}")
            
            decision = ContextEnhancementDecision.model_validate_json(response_content)
            
            if decision.should_enhance and decision.enhancement_type and decision.search_query:
                return {
                    'type': decision.enhancement_type,
                    'query': decision.search_query
                }
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Error in context enhancement decision: {e}")
            return None

    async def _enhance_context_with_search(self, context: LLMContext) -> LLMContext:
        """Use LLM to decide if context should be enhanced, then perform the enhancement"""
        
        # First, ask LLM if we should enhance context
        enhancement_decision = await self._decide_context_enhancement(context)
        
        if not enhancement_decision:
            return context  # No enhancement needed
            
        enhancement_type = enhancement_decision['type']
        search_query = enhancement_decision['query']
        
        logger.info(f"🔍 Enhancing context with {enhancement_type}: {search_query}")
        
        # Perform the appropriate enhancement
        if enhancement_type == "youtube":
            video_data = await self._search_youtube_video(search_query)
            
            if video_data:
                # Add the video search results to context memory
                enhanced_context_memory = context.app_state.context_memory.copy()
                enhanced_context_memory['found_videos'] = [video_data]
                enhanced_context_memory['enhancement_type'] = 'youtube'
                enhanced_context_memory['search_query'] = search_query
                
                # Create enhanced app state
                enhanced_app_state = AppState(
                    current_mode=context.app_state.current_mode,
                    command_history=context.app_state.command_history,
                    user_preferences=context.app_state.user_preferences,
                    config=context.app_state.config,
                    active_session_id=context.app_state.active_session_id,
                    last_activity=context.app_state.last_activity,
                    context_memory=enhanced_context_memory
                )
                
                # Return enhanced context
                return LLMContext(
                    current_message=context.current_message,
                    app_state=enhanced_app_state,
                    recent_history=context.recent_history,
                    available_actions=context.available_actions,
                    available_modes=context.available_modes,
                    session_info=context.session_info
                )
        
        elif enhancement_type == "music":
            music_data = await self._search_music(search_query)
            
            if music_data:
                # Add the music search results to context memory
                enhanced_context_memory = context.app_state.context_memory.copy()
                enhanced_context_memory['found_music'] = [music_data]
                enhanced_context_memory['enhancement_type'] = 'music'
                enhanced_context_memory['search_query'] = search_query
                
                # Create enhanced app state
                enhanced_app_state = AppState(
                    current_mode=context.app_state.current_mode,
                    command_history=context.app_state.command_history,
                    user_preferences=context.app_state.user_preferences,
                    config=context.app_state.config,
                    active_session_id=context.app_state.active_session_id,
                    last_activity=context.app_state.last_activity,
                    context_memory=enhanced_context_memory
                )
                
                # Return enhanced context
                return LLMContext(
                    current_message=context.current_message,
                    app_state=enhanced_app_state,
                    recent_history=context.recent_history,
                    available_actions=context.available_actions,
                    available_modes=context.available_modes,
                    session_info=context.session_info
                )
        
        # TODO: Add other enhancement types (images) here
        # elif enhancement_type == "images":
        #     # Search for images
        
        # Return original context if enhancement failed or type not supported
        return context

    async def _process_with_llm(self, context: LLMContext) -> LLMResponse:
        """
        Process context with Groq LLM and return response with structured output
        """
        if self.groq_client and PYDANTIC_AVAILABLE:
            print("Processing with Groq API")
            return await self._process_with_groq(context)
        else:
            reasons = []
            if not self.groq_client:
                reasons.append("no API key")
            if not PYDANTIC_AVAILABLE:
                reasons.append("no Pydantic")
            print(f"Processing with placeholder ({', '.join(reasons)})")
            return await self._process_with_placeholder(context)

    async def _process_with_groq(self, context: LLMContext) -> LLMResponse:
        """Process with Groq API using structured output"""
        try:
            message_type = context.current_message.message_type
            raw_data = context.current_message.data
            current_mode = context.app_state.current_mode
            
            # Pre-process requests by using LLM to decide on context enhancement
            enhanced_context = await self._enhance_context_with_search(context)
            
            # Build the system prompt
            system_prompt = self._build_system_prompt(enhanced_context)
            
            # Build the user message
            user_message = self._build_user_message(enhanced_context)
            
            logger.info(f"🤖 Sending to Groq: {user_message[:100]}...")
            
            # Call Groq with structured output
            if LLMResponse_Structured is None:
                raise Exception("LLMResponse_Structured is not available - Pydantic import failed")
                
            completion = self.groq_client.chat.completions.create(
                model="openai/gpt-oss-120b",  # Model that supports structured outputs
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "smart_glasses_response",
                        "schema": LLMResponse_Structured.model_json_schema()
                    }
                },
                temperature=0.7,
                max_tokens=1000
            )
            
            # Parse the structured response
            response_content = completion.choices[0].message.content
            logger.info(f"🤖 Groq response (FULL JSON): {response_content}")
            
            structured_response = LLMResponse_Structured.model_validate_json(response_content)
            
            # Convert to our standard LLMResponse format (no more post-processing needed)
            actions = [
                OutgoingAction(action=action.action, data=action.data)
                for action in structured_response.actions
            ]
            
            return LLMResponse(
                actions=actions,
                new_mode=structured_response.new_mode,
                context_updates=structured_response.context_updates,
                confidence=structured_response.confidence,
                reasoning=structured_response.reasoning
            )
            
        except Exception as e:
            logger.error(f"❌ Error processing with Groq: {e}")
            # Fallback to placeholder
            return await self._process_with_placeholder(context)

    async def _process_with_placeholder(self, context: LLMContext) -> LLMResponse:
        """Fallback placeholder logic when Groq is not available"""
        message_type = context.current_message.message_type
        raw_data = context.current_message.data
        current_mode = context.app_state.current_mode

        actions = []

        if message_type == "receive_speech":
            speech_text = raw_data.get("speech", "")

            # Simple routing based on keywords
            if "play music" in speech_text.lower() or "song" in speech_text.lower():
                actions.append(create_play_song_action("Default Song"))
            elif "video" in speech_text.lower() or "watch" in speech_text.lower():
                actions.append(create_play_video_action("https://example.com/video"))
            elif "picture" in speech_text.lower() or "visual" in speech_text.lower():
                actions.append(create_visual_action(speech_text))
            else:
                actions.append(self._create_tts_with_config(
                    f"I heard you say: {speech_text} in {current_mode} mode"
                ))

        elif message_type == "done_command":
            command_id = raw_data.get("command_id", "unknown")
            actions.append(self._create_tts_with_config(
                f"Command {command_id} completed successfully"
            ))

        elif message_type == "done_story":
            actions.append(self._create_tts_with_config(
                "Story finished! What would you like to do next?"
            ))

        elif message_type == "config_send":
            # Acknowledge config update
            actions.append(self._create_tts_with_config(
                "Configuration updated successfully"
            ))

        return LLMResponse(
            actions=actions,
            confidence=0.8,
            reasoning=f"Processed {message_type} in {current_mode} mode (placeholder)"
        )

    def _build_system_prompt(self, context: LLMContext) -> str:
        """Build the system prompt for Groq"""
        available_actions = ", ".join(context.available_actions)
        available_modes = ", ".join(context.available_modes)
        
        # Check if we have enhanced context data
        enhancement_context = ""
        enhancement_type = context.app_state.context_memory.get('enhancement_type')
        
        if enhancement_type == 'youtube':
            found_videos = context.app_state.context_memory.get('found_videos', [])
            search_query = context.app_state.context_memory.get('search_query', '')
            
            if found_videos:
                video = found_videos[0]  # Use the first/best video
                enhancement_context = f"""
CONTEXT ENHANCEMENT: YOUTUBE
I searched for "{search_query}" and found this relevant video:
- Title: {video.get('title')}
- URL: {video.get('video_url')}
- Channel: {video.get('channel')}
- Duration: {video.get('duration')}

Use this exact video URL in your play_video action."""
        
        elif enhancement_type == 'music':
            found_music = context.app_state.context_memory.get('found_music', [])
            search_query = context.app_state.context_memory.get('search_query', '')
            
            if found_music:
                music = found_music[0]  # Use the first/best music result
                enhancement_context = f"""
CONTEXT ENHANCEMENT: MUSIC
I searched for "{search_query}" and found this relevant music:
- Song Title: {music.get('song_title')}
- Artist: {music.get('artist')}
- URL: {music.get('video_url')}
- Duration: {music.get('duration')}

Use this information in your play_song action or play_video action for music playback."""
        
        config = context.app_state.config
        config_info = f"""
CURRENT CONFIG:
- Config type: {config.config_type}
- Voice type: {config.voice_type}
- Volume: {config.volume}
- Closed captions: {config.closed_captions}"""

        return f"""You are an AI sleep assistant for smart glasses. You help users by responding to their speech and commands in a way to guide them to sleep by either playing videos (can be music or other), reading passages, or other sleep-inducing activities like counting sheep

CURRENT CONTEXT:
- Current mode: {context.app_state.current_mode}
- Available actions: {available_actions}
- Available modes: {available_modes}
- Session duration: {context.session_info.get('session_duration', 0):.1f} seconds
- Total commands: {context.session_info.get('total_commands', 0)}{config_info}{enhancement_context}

RESPONSE FORMAT:
You must respond with a JSON object containing:
- actions: Array of action objects, each with "action" (type) and "data" (parameters)
- new_mode: Optional mode change
- context_updates: Optional context memory updates
- confidence: Your confidence level (0.0-1.0)
- reasoning: Brief explanation of your response

ACTION TYPES AND THEIR DATA:
- tts: {{"speech": "text to speak", "voice_type": "{config.voice_type}", "speed": 1.0, "volume": {config.volume}}}
- play_song: {{"song_title": "song name", "artist": "artist name", "video_url": "youtube_url_if_found"}}
- play_video: {{"video_url": "actual_youtube_url", "title": "video title", "duration": "duration"}}
- create_visual: {{"visual_prompt": "description", "style": "optional", "duration": 30}}
- change_mode: {{"mode": "new_mode"}}
- acknowledge: {{"message": "acknowledgment"}}
- config_send: {{"config_type": "tts", "voice_type": "voice_name", "volume": 1.0, "closed_captions": false}}

MUSIC INSTRUCTIONS:
- If I found music for you (shown above), use the song_title, artist, and video_url in your play_song action
- You can also use play_video with the music URL for audio playback
- You can announce the music with a TTS action first

VIDEO INSTRUCTIONS:
- If I found a video from youtube for you (shown above), use the exact video_url provided for playing songs or videos
- Include the title and other metadata in your play_video action
- You can announce the video with a TTS action first

BEHAVIOR:
- Be helpful and conversational for sleep assistance
- You can return multiple actions in sequence
- Match the user's energy and context
- Consider the current mode when responding
- Use appropriate actions for the request
- Focus on sleep-inducing content like calming music, nature sounds, bedtime stories"""

    def _build_user_message(self, context: LLMContext) -> str:
        """Build the user message for Groq"""
        message_type = context.current_message.message_type
        raw_data = context.current_message.data
        
        # Include recent history for context
        history_context = ""
        if context.recent_history:
            recent_commands = context.recent_history[-3:]  # Last 3 commands
            history_context = "\n\nRECENT HISTORY:\n"
            for i, cmd in enumerate(recent_commands, 1):
                history_context += f"{i}. {cmd.command_type}: {str(cmd.data)[:100]}\n"
        
        if message_type == "receive_speech":
            speech_text = raw_data.get("speech", "")
            return f"User said: \"{speech_text}\"{history_context}"
        
        elif message_type == "done_command":
            command_id = raw_data.get("command_id", "unknown")
            status = raw_data.get("status", "completed")
            return f"Command '{command_id}' finished with status: {status}{history_context}"
        
        elif message_type == "done_story":
            story_id = raw_data.get("story_id", "unknown")
            duration = raw_data.get("duration", "unknown")
            return f"Story '{story_id}' finished (duration: {duration}s){history_context}"
        
        else:
            return f"Received {message_type} with data: {raw_data}{history_context}"

    async def _execute_llm_actions(self, sid: str, llm_response: LLMResponse) -> None:
        """Execute all actions returned by the LLM"""

        # Update mode if LLM requested it
        if llm_response.new_mode:
            self.app_state.current_mode = llm_response.new_mode
            mode_data = {'type': 'mode_changed', 'mode': llm_response.new_mode}
            await self.send_to_client(sid, mode_data)
            logger.info(f"📤 WEBSOCKET SEND → {sid}: mode_changed | Data: {mode_data}")

        # Update context memory
        if llm_response.context_updates:
            self.app_state.context_memory.update(llm_response.context_updates)

        # Execute each action
        for action in llm_response.actions:
            await self._send_action(sid, action)

    async def _send_action(self, sid: str, action: OutgoingAction) -> None:
        """Send a single action to the glasses"""
        try:
            # Add to command history
            command = CommandHistory(
                timestamp=datetime.now().isoformat(),
                command_type=f"sent_{action.action}",
                data=action.data,
                mode=self.app_state.current_mode
            )
            self.app_state.command_history.append(command)

            # Send the action
            action_dict = serialize_dataclass(action)
            action_dict['type'] = action.action
            await self.send_to_client(sid, action_dict)

            logger.info(f"📤 WEBSOCKET SEND → {sid}: {action.action} | Data: {action_dict}")

        except Exception as e:
            logger.error(f"Error sending action {action.action}: {e}")

    # Public methods for sending specific actions (if needed from external code)
    async def send_tts(self, sid: str, speech: str, use_config: bool = True, **kwargs: Any) -> None:
        """Send TTS action with optional config usage"""
        if use_config:
            # Use config settings if no overrides provided
            if 'voice_type' not in kwargs:
                kwargs['voice_type'] = self.app_state.config.voice_type
            if 'volume' not in kwargs:
                kwargs['volume'] = self.app_state.config.volume
        
        action = create_tts_action(speech, **kwargs)
        await self._send_action(sid, action)

    async def send_tts_with_config(self, sid: str, speech: str) -> None:
        """Send TTS action using current config settings"""
        action = self._create_tts_with_config(speech)
        await self._send_action(sid, action)

    async def send_play_song(self, sid: str, song_title: str, **kwargs: Any) -> None:
        """Send play song action"""
        action = create_play_song_action(song_title, **kwargs)
        await self._send_action(sid, action)

    async def send_play_video(self, sid: str, video_url: str, **kwargs: Any) -> None:
        """Send play video action"""
        action = create_play_video_action(video_url, **kwargs)
        await self._send_action(sid, action)

    async def send_create_visual(self, sid: str, visual_prompt: str, **kwargs: Any) -> None:
        """Send create visual action"""
        action = create_visual_action(visual_prompt, **kwargs)
        await self._send_action(sid, action)

    # Utility methods
    def _print_recent_history(self, limit: int = 3) -> None:
        """Print the last N messages from command history"""
        if not self.app_state.command_history:
            logger.info("=== Command History (empty) ===")
            return

        recent_commands = self.app_state.command_history[-limit:]
        logger.info(f"=== Last {len(recent_commands)} Commands ===")

        for i, cmd in enumerate(recent_commands, 1):
            timestamp = cmd.timestamp
            command_type = cmd.command_type
            mode = cmd.mode
            data_summary = str(cmd.data)[:100] + "..." if len(str(cmd.data)) > 100 else str(cmd.data)

            logger.info(f"{i}. [{timestamp}] {command_type} (mode: {mode})")
            logger.info(f"   Data: {data_summary}")

        logger.info("=== End History ===")

    def get_app_state(self) -> Any:
        """Get current application state as dictionary"""
        return serialize_dataclass(self.app_state)

    def get_command_history(self, limit: int = 10) -> List[Any]:
        """Get recent command history"""
        recent_commands = self.app_state.command_history[-limit:]
        return [serialize_dataclass(cmd) for cmd in recent_commands]

    async def start_server(self):
        """Start the WebSocket server"""
        logger.info(f"Starting AgentWebSocket server on {self.host}:{self.port}")
        
        # Start WebSocket server
        server = await websockets.serve(
            self.handle_client,
            self.host,
            self.port,
            ping_interval=20,
            ping_timeout=10
        )
        
        logger.info(f"✅ WebSocket server running on ws://{self.host}:{self.port}")
        return server

# Global instance
agent_websocket = AgentWebSocket()

async def main():
    """Main function to start the WebSocket server"""
    server = await agent_websocket.start_server()
    
    # Keep the server running
    try:
        await server.wait_closed()
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
        server.close()
        await server.wait_closed()

if __name__ == "__main__":
    asyncio.run(main())
