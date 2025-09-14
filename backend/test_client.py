import socketio
import asyncio
import json
import time
from datetime import datetime
from typing import Dict, Any

class TestClient:
    """Test client for connecting to and testing the AgentSocket server"""

    def __init__(self, host: str = "localhost", port: int = 5000):
        self.host = host
        self.port = port
        self.url = f"http://{host}:{port}"
        self.sio = socketio.AsyncClient()
        self.connected = False

        # Register event handlers
        self._register_handlers()

    def _register_handlers(self):
        """Register socket event handlers"""

        @self.sio.event
        async def connect():
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            print(f"[{timestamp}] 📥 SOCKET RECV: connect | Connected to server at {self.url}")
            self.connected = True

        @self.sio.event
        async def disconnect():
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            print(f"[{timestamp}] 📥 SOCKET RECV: disconnect | Disconnected from server")
            self.connected = False

        @self.sio.event
        async def connection_status(data):
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            print(f"[{timestamp}] 📥 SOCKET RECV: connection_status | {data}")

        @self.sio.event
        async def mode_changed(data):
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            print(f"[{timestamp}] 📥 SOCKET RECV: mode_changed | {data}")

        @self.sio.event
        async def tts(data):
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            print(f"[{timestamp}] 📥 SOCKET RECV: tts | Speech: \"{data.get('data', {}).get('speech', 'N/A')}\"")

        @self.sio.event
        async def play_song(data):
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            song_title = data.get('data', {}).get('song_title', 'N/A')
            print(f"[{timestamp}] 📥 SOCKET RECV: play_song | Song: \"{song_title}\"")

        @self.sio.event
        async def play_video(data):
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            video_url = data.get('data', {}).get('video_url', 'N/A')
            video_title = data.get('data', {}).get('title', 'N/A')
            print(f"[{timestamp}] 📥 SOCKET RECV: play_video | Title: \"{video_title}\" | URL: {video_url}")

        @self.sio.event
        async def create_visual(data):
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            prompt = data.get('data', {}).get('visual_prompt', 'N/A')
            print(f"[{timestamp}] 📥 SOCKET RECV: create_visual | Prompt: \"{prompt}\"")

        @self.sio.event
        async def acknowledge(data):
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            message = data.get('data', {}).get('message', 'N/A')
            print(f"[{timestamp}] 📥 SOCKET RECV: acknowledge | Message: \"{message}\"")

        @self.sio.event
        async def error(data):
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            error_msg = data.get('data', {}).get('error_message', 'N/A')
            print(f"[{timestamp}] 📥 SOCKET RECV: error | Error: \"{error_msg}\"")

    async def connect_to_server(self):
        """Connect to the AgentSocket server"""
        try:
            await self.sio.connect(self.url)
            await asyncio.sleep(1)  # Give connection time to establish
            return True
        except Exception as e:
            print(f"❌ Failed to connect: {e}")
            return False

    async def disconnect_from_server(self):
        """Disconnect from the server"""
        if self.connected:
            await self.sio.disconnect()

    async def send_speech(self, speech_text: str, mode: str = None):
        """Send a speech message to the server"""
        if not self.connected:
            print("❌ Not connected to server")
            return

        data = {"speech": speech_text}
        if mode:
            data["mode"] = mode

        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        print(f"[{timestamp}] 📤 CLIENT SEND: receive_speech | Speech: \"{speech_text}\"")
        await self.sio.emit("receive_speech", data)

    async def send_done_command(self, command_id: str, status: str = "completed"):
        """Send a command completion message"""
        if not self.connected:
            print("❌ Not connected to server")
            return

        data = {
            "command_id": command_id,
            "status": status,
            "execution_time": 1.5
        }

        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        print(f"[{timestamp}] 📤 CLIENT SEND: done_command | Command: {command_id} - {status}")
        await self.sio.emit("done_command", data)

    async def send_done_story(self, story_id: str, duration: float = None):
        """Send a story completion message"""
        if not self.connected:
            print("❌ Not connected to server")
            return

        data = {
            "story_id": story_id,
            "duration": duration or 30.0,
            "user_engagement": "high"
        }

        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        print(f"[{timestamp}] 📤 CLIENT SEND: done_story | Story: {story_id}")
        await self.sio.emit("done_story", data)

    async def run_test_sequence(self):
        """Run a sequence of test messages"""
        print("\n🚀 Starting test sequence...\n")

        # Test 1: Basic speech in conversational mode
        await self.send_speech("Hello, how are you today?")
        await asyncio.sleep(2)

        # Test 2: Music request
        await self.send_speech("Can you play some music for me?")
        await asyncio.sleep(2)

        # Test 3: Video request
        await self.send_speech("Show me a video about cats")
        await asyncio.sleep(2)

        # Test 4: Visual request
        await self.send_speech("Create a picture of a sunset")
        await asyncio.sleep(2)

        # Test 5: Command completion
        await self.send_done_command("cmd_001", "completed")
        await asyncio.sleep(2)

        # Test 6: Story completion
        await self.send_done_story("story_001", 45.0)
        await asyncio.sleep(2)

        # Test 7: Mode-specific requests
        await self.send_speech("Let's play a game", mode="sheep")
        await asyncio.sleep(2)

        await self.send_speech("Search for funny videos", mode="youtube")
        await asyncio.sleep(2)

        print("\n✅ Test sequence completed!\n")

class InteractiveTestClient:
    """Interactive test client for manual testing"""

    def __init__(self):
        self.client = TestClient()

    async def run(self):
        """Run interactive test session"""
        print("🔧 Smart Glasses Test Client")
        print("=" * 40)

        # Connect to server
        if not await self.client.connect_to_server():
            return

        try:
            while True:
                print("\nChoose an option:")
                print("1. Send speech message")
                print("2. Send done_command")
                print("3. Send done_story")
                print("4. Run automated test sequence")
                print("5. Exit")

                choice = input("\nEnter choice (1-5): ").strip()

                if choice == "1":
                    speech = input("Enter speech text: ").strip()
                    mode = input("Enter mode (optional, press enter to skip): ").strip()
                    await self.client.send_speech(speech, mode if mode else None)

                elif choice == "2":
                    cmd_id = input("Enter command ID: ").strip()
                    status = input("Enter status (completed/failed/partial): ").strip()
                    await self.client.send_done_command(cmd_id, status or "completed")

                elif choice == "3":
                    story_id = input("Enter story ID: ").strip()
                    duration = input("Enter duration (seconds, optional): ").strip()
                    duration_val = float(duration) if duration else None
                    await self.client.send_done_story(story_id, duration_val)

                elif choice == "4":
                    await self.client.run_test_sequence()

                elif choice == "5":
                    break

                else:
                    print("❌ Invalid choice")

                await asyncio.sleep(1)

        except KeyboardInterrupt:
            print("\n👋 Exiting...")

        finally:
            await self.client.disconnect_from_server()

async def main():
    """Main function - choose between automated or interactive testing"""
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--auto":
        # Automated testing
        client = TestClient()

        if await client.connect_to_server():
            await client.run_test_sequence()
            await client.disconnect_from_server()
    else:
        # Interactive testing
        interactive_client = InteractiveTestClient()
        await interactive_client.run()

if __name__ == "__main__":
    # Usage:
    # python test_client.py           # Interactive mode
    # python test_client.py --auto    # Automated test sequence

    print("🔧 Smart Glasses Test Client Starting...")
    asyncio.run(main())
