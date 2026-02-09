import asyncio
import sys
from core.agent_manager import Agent_Manager
import os 

async def main():
    # 1. Instantiate the Manager
    # This pulls in your Database_Manager and ClientManager automatically
    manager = Agent_Manager()

    print("--- 🤖 System Starting ---")
    
    try:
        # 2. The critical Async Boot-up
        # This connects to MCP servers, binds tools, and connects to the SQLite DB
        await manager.initialize()
        print("--- ✅ Agent Ready for Chat ---")
        print("(Type 'exit' or 'quit' to stop)\n")

        # 3. Persistent Thread ID 
        # (Change this per user or session in a real production app)
        thread_id = "user_session_002"

        while True:
            # Get user input
            user_input = input("You: ").strip()

            if user_input.lower() in ["exit", "quit"]:
                print("Goodbye!")
                break

            if not user_input:
                continue

            print("AI: ", end="", flush=True)

            # 4. Use the Streaming method for real-time feedback
            try:
                async for chunk in manager.get_streaming_response(
                    user_input=user_input, 
                    thread_id=thread_id
                ):
                    # In stream_mode="messages", we yield the full content.
                    # To prevent repeating the whole history, we print just the latest.
                    # For a simple terminal, we clear and print or just print the final bit.
                    print(chunk, end="", flush=True) 
                
                # Print a newline after the stream finishes
                print("\n")

            except Exception as e:
                print(f"\n❌ Error during execution: {e}")

    except Exception as e:
        print(f"❌ Failed to initialize system: {e}")
    
    finally:
        # 5. Cleanup (Optional: close MCP connections if your ClientManager has a close method)
        print("--- 🔌 System Shutdown ---")

        # await manager.shutdown()
        # os._exit(0)
        await manager.database_manager.close_connection()
        print("--- 👋 System Offline ---")
if __name__ == "__main__":
    # Standard way to run an async main loop in Python 3.7+
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)