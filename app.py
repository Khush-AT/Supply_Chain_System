import streamlit as st
import asyncio
import os
import sqlite3
import uuid
import streamlit.components.v1 as components
from typing import Annotated, Literal, TypedDict
from pydantic import BaseModel
from dotenv import load_dotenv

from langchain_openai import AzureChatOpenAI
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_core.messages import BaseMessage, HumanMessage, ToolMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver

# --- 0. State Definition ---
class AgentState(TypedDict):
    # 'add_messages' ensures new messages are appended, not overwritten
    messages: Annotated[list[BaseMessage], add_messages]
    # Tracks the supervisor's routing decision
    next_agent: str

class RouteDecision(BaseModel):
    """Decision on which worker should act next."""
    next: Literal["logistics", "inventory", "FINISH"]

# --- 1. UI Configuration ---
st.set_page_config(page_title="Swarm Command Center", page_icon="🐝", layout="wide")
st.title("🐝 Multi-Agent Supply Chain Swarm")
load_dotenv()

# --- 2. System Initialization & Graph Construction ---
@st.cache_resource
def init_swarm():
    import sys
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
    llm = AzureChatOpenAI(
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
        deployment_name=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
    )
    
    # Fetch MCP Tools
    async def fetch_tools():
        client = MultiServerMCPClient({
            "environment_tools": {
                "command": "python", 
                "args": ["mcp_server.py"], 
                "transport": "stdio"
            }
        })
        return await client.get_tools()
    
    all_tools = asyncio.run(fetch_tools())
    
    # Categorize Tools for Specialists
    logistics_tools = [t for t in all_tools if t.name in ["check_weather_disruptions", "track_shipment_status", "update_shipment_status"]]
    inventory_tools = [t for t in all_tools if t.name in ["query_inventory_db", "reorder_inventory", "get_supplier_info"]]

    # --- Node Definitions ---

    def supervisor_node(state: AgentState):
        """Analyzes the conversation and routes to the correct specialist."""
        system_prompt = (
            "You are the Triage Commander Supervisor for a supply chain network. "
            "Your job is to manage the conversation and delegate tasks to your workers.\n"
            "1. Route to 'logistics' for shipment tracking, status updates, and weather disruptions.\n"
            "2. Route to 'inventory' for stock checks, supplier info, and drafting Purchase Orders.\n"
            "If a request requires multiple steps (e.g., check weather, THEN reorder), route to the first step's agent. "
            "The worker will report back to you when finished. "
            "If all user requests have been fully resolved, route to 'FINISH'."
        )
        
        messages = [{"role": "system", "content": system_prompt}] + state["messages"]
        decision = llm.with_structured_output(RouteDecision).invoke(messages)
        return {"next_agent": decision.next}

    def logistics_node(state: AgentState):
        """Logistics Specialist Worker"""
        system_prompt = "You are the Logistics Specialist. You handle shipments, tracking, and weather data. Use your tools if needed."
        llm_with_tools = llm.bind_tools(logistics_tools)
        response = llm_with_tools.invoke([{"role": "system", "content": system_prompt}] + state["messages"])
        return {"messages": [response]}

    def inventory_node(state: AgentState):
        """Inventory Specialist Worker"""
        system_prompt = "You are the Inventory Specialist. You handle stock levels, suppliers, and purchase orders. Use your tools if needed."
        llm_with_tools = llm.bind_tools(inventory_tools)
        response = llm_with_tools.invoke([{"role": "system", "content": system_prompt}] + state["messages"])
        return {"messages": [response]}

    # --- Routing Logic ---

    def worker_router(state: AgentState):
        """Decides if a worker should use a tool or return to the supervisor."""
        last_message = state["messages"][-1]
        if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
            tool_name = last_message.tool_calls[0]["name"]
            if tool_name in [t.name for t in logistics_tools]: return "logistics_tools"
            if tool_name in [t.name for t in inventory_tools]: return "inventory_tools"
        return "supervisor"

    # --- Build the Graph ---
    workflow = StateGraph(AgentState)

    # Add Nodes
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("logistics", logistics_node)
    workflow.add_node("inventory", inventory_node)
    workflow.add_node("logistics_tools", ToolNode(logistics_tools))
    workflow.add_node("inventory_tools", ToolNode(inventory_tools))

    # Edges
    workflow.add_edge(START, "supervisor")

    workflow.add_conditional_edges(
        "supervisor",
        lambda state: state["next_agent"],
        {
            "logistics": "logistics",
            "inventory": "inventory",
            "FINISH": END
        }
    )

    workflow.add_conditional_edges("logistics", worker_router, {"logistics_tools": "logistics_tools", "supervisor": "supervisor"})
    workflow.add_conditional_edges("inventory", worker_router, {"inventory_tools": "inventory_tools", "supervisor": "supervisor"})
    
    workflow.add_edge("logistics_tools", "logistics")
    workflow.add_edge("inventory_tools", "inventory")

    memory = MemorySaver()
    # Interrupt before ANY tool is executed for Human-in-the-Loop safety
    return workflow.compile(checkpointer=memory, interrupt_before=["logistics_tools", "inventory_tools"])

agent_graph = init_swarm()

# --- 3. Streamlit UI Logic ---
if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())

config = {"configurable": {"thread_id": st.session_state.thread_id}}

# --- Sidebar Dashboard ---
st.sidebar.title("📊 System Operations")
st.sidebar.caption(f"Active Session: {st.session_state.thread_id[:8]}...")

try:
    log_conn = sqlite3.connect("databases/logistics.db")
    log_cursor = log_conn.cursor()
    log_cursor.execute("SELECT COUNT(*) FROM shipments WHERE status LIKE '%Delayed%'")
    delayed_count = log_cursor.fetchone()[0]
    log_conn.close()
except Exception:
    delayed_count = 0

try:
    inv_conn = sqlite3.connect("databases/inventory.db")
    inv_cursor = inv_conn.cursor()
    inv_cursor.execute("SELECT COUNT(*) FROM inventory WHERE current_stock < (daily_burn_rate * 5)")
    low_stock_count = inv_cursor.fetchone()[0]
    inv_cursor.execute("SELECT COUNT(*) FROM purchase_orders WHERE status != 'Completed'")
    pending_pos = inv_cursor.fetchone()[0]
    inv_conn.close()
except Exception:
    low_stock_count = 0
    pending_pos = 0

st.sidebar.metric("Delayed Shipments", delayed_count, delta=delayed_count, delta_color="inverse")
st.sidebar.metric("Low Stock Alerts", low_stock_count, delta=low_stock_count, delta_color="inverse")
st.sidebar.metric("Pending Purchase Orders", pending_pos)
st.sidebar.divider()

if st.sidebar.button("🗑️ Clear System Memory", use_container_width=True):
    st.cache_resource.clear()
    st.session_state.thread_id = str(uuid.uuid4())
    st.rerun()

# --- Async Stream Processor ---
async def process_stream(inputs):
    async for _ in agent_graph.astream(inputs, config=config, stream_mode="values"):
        pass
    st.rerun()

# --- 4. Render Chat History ---
state = agent_graph.get_state(config)
messages = state.values.get("messages", [])

for msg in messages:
    if isinstance(msg, HumanMessage):
        with st.chat_message("user"):
            st.markdown(msg.content)
    elif isinstance(msg, ToolMessage):
        with st.chat_message("tool", avatar="🛠️"):
            st.caption(f"**Action Log:** {msg.content}")
    elif msg.content: # AI messages
        with st.chat_message("assistant"):
            st.markdown(msg.content)

# --- 5. Human-in-the-Loop (HITL) Intercept ---
if state.next and any("tools" in n for n in state.next):
    # Determine which agent is asking for permission
    pending_node = state.next[0]
    agent_name = "🚚 Logistics Specialist" if pending_node == "logistics_tools" else "📦 Inventory Specialist"
    
    st.warning(f"⚠️ **Approval Required!** The {agent_name} has proposed an action.")
    
    last_msg = messages[-1]
    for tc in last_msg.tool_calls:
        st.code(f"Tool: {tc['name']}\nArguments: {tc['args']}")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ Approve Action", use_container_width=True):
            asyncio.run(process_stream(None))
    with col2:
        if st.button("❌ Reject Action", use_container_width=True):
            # Formally reject the tool call so the agent knows it was blocked
            rejection_messages = [
                ToolMessage(
                    tool_call_id=tc["id"],
                    name=tc["name"],
                    content="ERROR: The Human Supervisor rejected this action. Do NOT proceed. Acknowledge this."
                ) for tc in last_msg.tool_calls
            ]
            agent_graph.update_state(config, {"messages": rejection_messages}, as_node=pending_node)
            asyncio.run(process_stream(None))

# --- 6. Chat Input ---
elif prompt := st.chat_input("Command the Swarm (e.g., 'Check weather for shipment S-100, if delayed, reorder stock')..."):
    with st.chat_message("user"):
        st.markdown(prompt)
    asyncio.run(process_stream({"messages": [HumanMessage(content=prompt)]}))