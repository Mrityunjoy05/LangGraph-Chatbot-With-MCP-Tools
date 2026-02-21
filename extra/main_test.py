import asyncio
import sys
from extra.agent_manager2_copy import Agent_Manager
from langgraph.types import Command

async def main():
    manager = Agent_Manager()
    agent = await manager.initialize()
    # thread_id = "004"
    thread_id = "012"
    config = {"configurable": {"thread_id": thread_id}}

    print("--- ✅ System Online & Secure ---")

    while True:
        user_input = input("\nYou: ").strip()
        if user_input.lower() in ["exit", "quit"]: break
        if not user_input: continue

        # 1. Initial execution
        # We use stream_mode="updates" to avoid the "Values" wall of text
        await manager.get_streaming_response1(user_input=user_input,config=config)


    await manager.database_manager.close_connection()

if __name__ == "__main__":
    asyncio.run(main())