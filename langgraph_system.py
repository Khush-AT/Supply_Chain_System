import streamlit as st
import asyncio
import os
import sqlite3
import uuid
from typing import Annotated, Literal, TypedDict
from dotenv import load_dotenv

from langchain_openai import AzureChatOpenAI
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_core.messages import BaseMessage, HumanMessage, ToolMessage
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver

# --- 0. State Definition ---
class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]

# --- 1. UI Configuration ---
st.set_page_config(page_title="Swarm Commander", page_icon="🐝", layout="wide")
st.title("🐝 Multi-Agent Supply Chain Swarm")
load_dotenv()

# --- 2. System Initialization & Graph Construction ---
@st.cache_resource
def init_swarm():
    llm = AzureChatOpenAI(
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
        deployment_name=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
    )
    
    # Fetch MCP Tools
    async def fetch_tools():
        client = MultiServerMCPClient({
            "env_tools": {"command": "python", "args": ["mcp_server.py"], "transport": "stdio"}
        })
        return await client.get_tools()
    
    all_tools = asyncio.run(fetch_tools())
    
    # Categorize Tools for Specialists
    logistics_tools = [t for t in all_tools if t.name in ["check_weather_disruptions", "track_shipment_status", "update_shipment_status"]]
    inventory_tools = [t for t in all_tools if t.name in ["query_inventory_db", "reorder_inventory", "get_supplier_info"]]

    # Define Specialist Nodes
    def create_specialist(tools, system_prompt):
        return lambda state: llm.bind_tools(tools).invoke([
            {"role": "system", "content": system_prompt}
        ] + state["messages"])

    logistics_agent = create_specialist(logistics_tools, "You are the Logistics Specialist. Handle shipments and weather.")
    inventory_agent = create_specialist(inventory_tools, "You are the Inventory Specialist. Handle stock, POs, and suppliers.")

    # --- Router / Supervisor Logic ---
    def router(state: AgentState) -> Literal["logistics", "inventory", "__end__"]:
        last_message = state["messages"][-1]
        if last_message.tool_calls:
            # Route based on tool name
            tool_name = last_message.tool_calls[0]["name"]
            if tool_name in [t.name for t in logistics_tools]: return "logistics_tools"
            return "inventory_tools"
        
        if "shipment" in last_message.content.lower() or "weather" in last_message.content.lower():
            return "logistics"
        if "stock" in last_message.content.lower() or "order" in last_message.content.lower():
            return "inventory"
        return END

    # Build the Graph
    workflow = StateGraph(AgentState)

    workflow.add_node("logistics", logistics_agent)
    workflow.add_node("inventory", inventory_agent)
    workflow.add_node("logistics_tools", ToolNode(logistics_tools))
    workflow.add_node("inventory_tools", ToolNode(inventory_tools))

    workflow.set_entry_point("logistics") # Default entry, or build a supervisor node

    workflow.add_conditional_edges("logistics", router, {"logistics_tools": "logistics_tools", "inventory": "inventory", "__end__": END})
    workflow.add_conditional_edges("inventory", router, {"inventory_tools": "inventory_tools", "logistics": "logistics", "__end__": END})
    
    workflow.add_edge("logistics_tools", "logistics")
    workflow.add_edge("inventory_tools", "inventory")

    memory = MemorySaver()
    return workflow.compile(checkpointer=memory, interrupt_before=["logistics_tools", "inventory_tools"])

agent_graph = init_swarm()

# --- 3. Streamlit UI Logic ---
if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())

config = {"configurable": {"thread_id": st.session_state.thread_id}}

# Sidebar Dashboard (same as your original)
# ... [Insert your sidebar logic here] ...

async def process_stream(inputs):
    async for _ in agent_graph.astream(inputs, config=config, stream_mode="values"):
        pass
    st.rerun()

# Render History
state = agent_graph.get_state(config)
messages = state.values.get("messages", [])

for msg in messages:
    role = "user" if isinstance(msg, HumanMessage) else "assistant"
    with st.chat_message(role):
        st.markdown(msg.content if msg.content else f"Invoking tool: {msg.tool_calls[0]['name'] if hasattr(msg, 'tool_calls') else 'Processing...'}")

# HITL Intercept
if state.next and any("tools" in n for n in state.next):
    st.warning("⚠️ **Swarm Action Pending Approval**")
    last_msg = messages[-1]
    for tc in last_msg.tool_calls:
        st.info(f"Specialist wants to use: `{tc['name']}`")
    
    if st.button("✅ Execute Swarm Command"):
        asyncio.run(process_stream(None))
    if st.button("❌ Abort"):
        # Logic to update state with rejection
        st.rerun()

elif prompt := st.chat_input("Command the Swarm..."):
    asyncio.run(process_stream({"messages": [HumanMessage(content=prompt)]}))