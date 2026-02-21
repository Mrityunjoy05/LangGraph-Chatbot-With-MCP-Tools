import asyncio
import sys
from core.agent_manager import Agent_Manager
from langgraph.types import Command
from langchain_core.messages import ToolMessage

async def main():
    manager = Agent_Manager()
    agent = await manager.initialize()
    # thread_id = "004"
    thread_id = "014"
    config = {"configurable": {"thread_id": thread_id}}

    print("--- ✅ System Online & Secure ---")

    while True:
        user_input = input("\nYou: ").strip()
        if user_input.lower() in ["exit", "quit"]: break
        if not user_input: continue

        # 1. Initial execution
        # We use stream_mode="updates" to avoid the "Values" wall of text
        async for event in agent.astream({"messages": [("user", user_input)]}, config, stream_mode="updates"):
            for node_name, output in event.items():
                if node_name == "agent":
                    msg = output["messages"][-1]
                    if msg.content:
                        print(f"AI: {msg.content}")

        # 2. HITL Check
        state = await agent.aget_state(config)
        while state.next and "tools" in state.next:
            last_ai_msg = state.values["messages"][-1]
            
            for tool_call in last_ai_msg.tool_calls:
                t_name = tool_call["name"]
                t_args = tool_call["args"]

                # FIX: If the AI tries to list 100 repos, it breaks the response. 
                # Let's cap it at 10 for the terminal.
                if t_name == "list_repositories" and t_args.get("limit", 0) > 10:
                    t_args["limit"] = 10

                if t_name in ["delete_repository", "create_repository"]:
                    print(f"\n🛑 [SECURITY CHECK]: AI wants to {t_name}")
                    print(f"Details: {t_args}")
                    confirm = input("Allow this? (y/n): ").lower()
                    
                    if confirm != 'y':
                        # 1. Create a fake tool response telling the AI you denied it
                        reject_msg = ToolMessage(
                            tool_call_id=tool_call["id"],
                            name=t_name,
                            content="ACTION FAILED: The user explicitly denied this security check. Do not proceed."
                        )
                        
                        # 2. Update the state ACTING AS the 'tools' node (This skips the real tool!)
                        await agent.aupdate_state(config, {"messages": [reject_msg]}, as_node="tools")
                        
                        print("System: Action cancelled.")
                        
                        # 3. Resume the graph from the agent node so it reads your rejection
                        async for update in agent.astream(None, config, stream_mode="updates"):
                            if "agent" in update:
                                final_msg = update["agent"]["messages"][-1]
                                if final_msg.content:
                                    print(f"AI: {final_msg.content}")
                        break # Exit the tool loop
                
                # ... (Keep your Resume execution logic for when confirm == 'y' here)
                
                # Resume execution
                print(f"🚀 Running {t_name}...")
                async for update in agent.astream(Command(resume=True), config, stream_mode="updates"):
                    if "agent" in update:
                        final_msg = update["agent"]["messages"][-1]
                        if final_msg.content:
                            print(f"AI: {final_msg.content}")

            state = await agent.aget_state(config)

    await manager.database_manager.close_connection()

if __name__ == "__main__":
    asyncio.run(main())