import asyncio
import json
import websockets
import time
from datetime import datetime
from typing import Dict, Any, Optional

class TestClient:
    """Test client for connecting to and testing the AgentWebSocket server"""

    def __init__(self, host: str = "localhost", port: int = 5000):
        self.host = host
        self.port = port
        self.url = f"ws://{host}:{port}"
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.connected = False

    async def connect(self):
        """Connect to the WebSocket server"""
        try:
            self.websocket = await websockets.connect(self.url)
            self.connected = True
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            print(f"[{timestamp}] 📥 WEBSOCKET RECV: connect | Connected to server at {self.url}")
            
            # Start listening for messages
            asyncio.create_task(self._listen_for_messages())
            
        except Exception as e:
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            print(f"[{timestamp}] ❌ Failed to connect: {e}")
            self.connected = False

    async def disconnect(self):
        """Disconnect from the WebSocket server"""
        if self.websocket and self.connected:
            await self.websocket.close()
            self.connected = False
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            print(f"[{timestamp}] 📥 WEBSOCKET RECV: disconnect | Disconnected from server")

    async def _listen_for_messages(self):
        """Listen for incoming messages from the server"""
        try:
            async for message in self.websocket:
                await self._handle_message(message)
        except websockets.exceptions.ConnectionClosed:
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            print(f"[{timestamp}] 📥 WEBSOCKET RECV: disconnect | Connection closed by server")
            self.connected = False
        except Exception as e:
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            print(f"[{timestamp}] ❌ Error listening for messages: {e}")
            self.connected = False

    async def _handle_message(self, raw_message: str):
        """Handle incoming message from server"""
        try:
            data = json.loads(raw_message)
            message_type = data.get('type', 'unknown')
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            print(f"[{timestamp}] 📥 WEBSOCKET RECV: {message_type} | Data: {data}")
        except json.JSONDecodeError:
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            print(f"[{timestamp}] ❌ Invalid JSON received: {raw_message}")

    async def send_message(self, message_type: str, data: Dict[str, Any]):
        """Send a message to the server"""
        if not self.connected or not self.websocket:
            print("❌ Not connected to server")
            return

        message = {
            "type": message_type,
            **data
        }

        try:
            await self.websocket.send(json.dumps(message))
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            print(f"[{timestamp}] 📤 WEBSOCKET SEND: {message_type} | Data: {data}")
        except Exception as e:
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            print(f"[{timestamp}] ❌ Failed to send message: {e}")

    async def send_speech(self, speech_text: str, mode: str = None):
        """Send a speech message to the server"""
        data = {"speech": speech_text}
        if mode:
            data["mode"] = mode
        await self.send_message("receive_speech", data)

    async def send_done_command(self, command_id: str, status: str = "completed"):
        """Send a command completion message"""
        data = {
            "command_id": command_id,
            "status": status,
            "execution_time": 1.5
        }
        await self.send_message("done_command", data)

    async def send_done_story(self, story_id: str, duration: float = None):
        """Send a story completion message"""
        data = {
            "story_id": story_id,
            "duration": duration or 30.0,
            "user_engagement": "high"
        }
        await self.send_message("done_story", data)

    async def send_button_press(self, button_type: str):
        """Send a button press message"""
        data = {"button_type": button_type}
        await self.send_message("button_press", data)

    async def send_config_update(self, config: Dict[str, Any]):
        """Send a config update message"""
        await self.send_message("config_update", config)

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
        await self.client.connect()
        if not self.client.connected:
            return

        try:
            while True:
                print("\nChoose an option:")
                print("1. Send speech message")
                print("2. Send done_command")
                print("3. Send done_story")
                print("4. Send button press")
                print("5. Run automated test sequence")
                print("6. Exit")

                choice = input("\nEnter choice (1-6): ").strip()

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
                    button_type = input("Enter button type (main/secondary/voice): ").strip()
                    await self.client.send_button_press(button_type or "main")

                elif choice == "5":
                    await self.client.run_test_sequence()

                elif choice == "6":
                    break

                else:
                    print("❌ Invalid choice")

                await asyncio.sleep(1)

        except KeyboardInterrupt:
            print("\n👋 Exiting...")

        finally:
            await self.client.disconnect()

async def main():
    """Main function - choose between automated or interactive testing"""
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--auto":
        # Automated testing
        client = TestClient()
        await client.connect()
        
        if client.connected:
            await client.run_test_sequence()
            await client.disconnect()
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
