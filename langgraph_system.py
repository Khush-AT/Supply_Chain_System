import os
import asyncio
from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain.agents import create_agent

# NEW: Import LangGraph's persistent memory checkpointer
from langgraph.checkpoint.memory import MemorySaver 

load_dotenv()

async def run_swarm():
    # 1. Initialize Azure OpenAI Brain
    llm = AzureChatOpenAI(
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
        deployment_name=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
    )

    # 2. Connect to the local MCP Server via stdio
    print("[System] Connecting to MCP Environment Layer...")
    client = MultiServerMCPClient({
        "environment_tools": {
            "command": "python",
            "args": ["mcp_server.py"],
            "transport": "stdio"
        }
    })
    
    # 3. Load tools dynamically from the MCP server
    tools = await client.get_tools()
    print(f"[System] Successfully bound {len(tools)} tools to the LLM.")

    # 4. Compile the LangChain v1 Agent with Memory
    system_prompt = (
        "You are the Triage Commander for a supply chain network. "
        "Use your tools to investigate delayed shipments, check inventory, assess weather disruptions, "
        "and proactively reorder inventory if necessary to prevent stockouts. "
        "Always synthesize the raw data into a clean, final executive summary."
    )
    
    # Initialize the memory saver
    memory = MemorySaver()
    
    # Compile the agent and attach the memory
    agent = create_agent(
        model=llm,
        tools=tools,
        system_prompt=system_prompt,
        checkpointer=memory
    )

    # Define a thread ID so the agent knows which conversation to remember
    config = {"configurable": {"thread_id": "supply-chain-session-01"}}

    # 5. The Interactive Command Loop
    print("\n" + "="*50)
    print("  AUTONOMOUS SUPPLY CHAIN SYSTEM")
    print("="*50)
    print("Type 'exit' to shut down the SYSTEM.\n")

    while True:
        user_input = input("\n[Commander Desk] Enter task: ")
        
        if user_input.lower() in ['exit', 'quit']:
            print("[System] Shutting down system...")
            break
            
        if not user_input.strip():
            continue

        inputs = {"messages": [{"role": "user", "content": user_input}]}
        
        print("\n[System Network Activity]")
        
        # Stream the graph's state and pass the config for memory tracking
        async for chunk in agent.astream(inputs, config=config, stream_mode="values"):
            message = chunk["messages"][-1]
            
            # Print Tool Actions
            if hasattr(message, 'tool_calls') and message.tool_calls:
                for tc in message.tool_calls:
                    print(f"[Action] Requesting tool: {tc['name']} -> Args: {tc['args']}")
            
            # Print AI Responses (Ignore echoing the user's prompt back)
            elif message.content and getattr(message, "type", "") == "ai":
                print(f"[Agent] {message.content}")

if __name__ == "__main__":
    # Prevent Windows event loop closure errors
    import sys
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    asyncio.run(run_swarm())