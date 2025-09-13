import logging
from datetime import datetime
from typing import Dict, List, Any

try:
    import socketio
except ImportError:
    print("python-socketio is required. Install with: pip install python-socketio")
    exit(1)

try:
    from data_types import (
        MessageType, IncomingMessage, OutgoingAction, ActionType, AppMode,
        AppState, CommandHistory, LLMContext, LLMResponse,
        create_incoming_message, create_tts_action, create_play_song_action,
        create_play_video_action, create_visual_action, create_error_action,
        serialize_dataclass
    )
except ImportError:
    print("data_types.py not found. Make sure it's in the same directory.")
    exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AgentSocket:
    """Main socket class for handling all smart glasses communication"""
    
    # Define available actions and modes using our types
    AVAILABLE_ACTIONS: list[ActionType] = ["tts", "play_song", "play_video", "create_visual", "change_mode", "acknowledge"]
    AVAILABLE_MODES: list[AppMode] = ["sheep", "youtube", "conversational", "visual_story", "zzz"]

    def __init__(self, host: str = "localhost", port: int = 5000) -> None:
        self.host = host
        self.port = port
        self.sio = socketio.AsyncServer(cors_allowed_origins="*")
        self.app_state = AppState()

        # Register all socket event handlers
        self._register_handlers()

    def _register_handlers(self) -> None:
        """Register all socket message handlers"""

        @self.sio.event
        async def connect(sid, environ):
            logger.info(f"Client {sid} connected")
            self.app_state.active_session_id = sid
            await self.sio.emit('connection_status', {
                'status': 'connected',
                'mode': self.app_state.current_mode,
                'session_id': sid
            }, room=sid)

        @self.sio.event
        async def disconnect(sid):
            logger.info(f"Client {sid} disconnected")
            if self.app_state.active_session_id == sid:
                self.app_state.active_session_id = None

        # Incoming message handlers - all route to single handler
        @self.sio.event
        async def receive_speech(sid, data):
            await self._handle_incoming_message(sid, "receive_speech", data)

        @self.sio.event
        async def done_command(sid, data):
            await self._handle_incoming_message(sid, "done_command", data)

        @self.sio.event
        async def done_story(sid, data):
            await self._handle_incoming_message(sid, "done_story", data)

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

    async def _process_with_llm(self, context: LLMContext) -> LLMResponse:
        """
        Process context with LLM and return response

        THIS IS WHERE YOU INTEGRATE YOUR LLM:
        - Send context to OpenAI/Claude/Local LLM
        - Get back structured response with actions
        - Return LLMResponse object
        """

        # TODO: Replace this placeholder with actual LLM integration

        message_type = context.current_message.message_type
        raw_data = context.current_message.data
        current_mode = context.app_state.current_mode

        # Placeholder logic - replace with your LLM call
        actions = []

        if message_type == "receive_speech":
            speech_text = raw_data.get("speech", "")

            # Simple routing based on keywords (replace with LLM logic)
            if "play music" in speech_text.lower() or "song" in speech_text.lower():
                actions.append(create_play_song_action("Default Song"))
            elif "video" in speech_text.lower() or "watch" in speech_text.lower():
                actions.append(create_play_video_action("https://example.com/video"))
            elif "picture" in speech_text.lower() or "visual" in speech_text.lower():
                actions.append(create_visual_action(speech_text))
            else:
                actions.append(create_tts_action(
                    f"I heard you say: {speech_text} in {current_mode} mode"
                ))

        elif message_type == "done_command":
            command_id = raw_data.get("command_id", "unknown")
            actions.append(create_tts_action(
                f"Command {command_id} completed successfully"
            ))

        elif message_type == "done_story":
            actions.append(create_tts_action(
                "Story finished! What would you like to do next?"
            ))

        return LLMResponse(
            actions=actions,
            confidence=0.8,
            reasoning=f"Processed {message_type} in {current_mode} mode"
        )

    async def _execute_llm_actions(self, sid: str, llm_response: LLMResponse) -> None:
        """Execute all actions returned by the LLM"""

        # Update mode if LLM requested it
        if llm_response.new_mode:
            self.app_state.current_mode = llm_response.new_mode
            await self.sio.emit('mode_changed', {'mode': llm_response.new_mode}, room=sid)

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
            await self.sio.emit(action.action, action_dict, room=sid)

            logger.info(f"Sent {action.action} to {sid}")

        except Exception as e:
            logger.error(f"Error sending action {action.action}: {e}")

    # Public methods for sending specific actions (if needed from external code)
    async def send_tts(self, sid: str, speech: str, **kwargs: Any) -> None:
        """Send TTS action"""
        action = create_tts_action(speech, **kwargs)
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

    async def run(self):
        """Run the socket server"""
        try:
            from aiohttp import web
        except ImportError:
            print("aiohttp is required. Install with: pip install aiohttp")
            exit(1)

        # Create aiohttp app
        app = web.Application()

        # Add HTTP endpoints for debugging/monitoring
        app.router.add_get('/health', self._health_check)
        app.router.add_get('/state', self._get_state)
        app.router.add_get('/history', self._get_history)
        app.router.add_post('/mode', self._set_mode)

        # Attach socket.io to the app
        self.sio.attach(app)

        logger.info(f"Starting AgentSocket server on {self.host}:{self.port}")
        return app

    # HTTP endpoint handlers
    async def _health_check(self, request: Any) -> Any:
        """Health check endpoint"""
        from aiohttp import web

        return web.json_response({
            "status": "healthy",
            "mode": self.app_state.current_mode,
            "active_session": self.app_state.active_session_id is not None,
            "uptime": self._calculate_session_duration()
        })

    async def _get_state(self, request: Any) -> Any:
        """Get current state endpoint"""
        from aiohttp import web

        return web.json_response(self.get_app_state())

    async def _get_history(self, request: Any) -> Any:
        """Get command history endpoint"""
        from aiohttp import web

        limit = int(request.query.get('limit', 10))
        return web.json_response(self.get_command_history(limit))

    async def _set_mode(self, request: Any) -> Any:
        """Set mode endpoint"""
        from aiohttp import web

        data = await request.json()
        new_mode = data.get('mode')
        if new_mode in self.AVAILABLE_MODES:
            self.app_state.current_mode = new_mode
            return web.json_response({"mode": self.app_state.current_mode})
        else:
            return web.json_response({"error": "Invalid mode"}, status=400)

# Global instance
agent_socket = AgentSocket()

async def create_app() -> Any:
    """Factory function to create the app"""
    return await agent_socket.run()

if __name__ == "__main__":
    try:
        from aiohttp import web
    except ImportError:
        print("aiohttp is required. Install with: pip install aiohttp")
        exit(1)

    async def init() -> Any:
        app = await create_app()
        return app

    # Run the server
    web.run_app(init(), host="localhost", port=5000)
