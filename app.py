import streamlit as st
import asyncio
import os
import sqlite3
import uuid
from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import ToolMessage

# --- 0. UI Configuration ---
st.set_page_config(page_title="Triage Commander System", page_icon="🛡️", layout="wide")
st.title("🛡️ Supply Chain System Command Center")

# Load environment
load_dotenv()

# --- 1. Dashboard Logic (Sidebar) ---
# --- 1. Session & Thread Management ---
# This ensures that every fresh start gets a unique ID
if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())

def render_sidebar_dashboard():
    st.sidebar.title("📊 System Operations")
    st.sidebar.caption(f"Active Session: {st.session_state.thread_id[:8]}...")
    
    # --- Database Queries (Keep your existing logic) ---
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

    # Render UI Metrics
    st.sidebar.metric("Delayed Shipments", delayed_count, delta=delayed_count, delta_color="inverse")
    st.sidebar.metric("Low Stock Alerts", low_stock_count, delta=low_stock_count, delta_color="inverse")
    st.sidebar.metric("Pending Purchase Orders", pending_pos)
    
    st.sidebar.divider()
    
    # --- The Fixed Clear Memory Logic ---
    if st.sidebar.button("🗑️ Clear System Memory", use_container_width=True):
        # 1. Clear the LangGraph Agent cache
        st.cache_resource.clear()
        
        # 2. Change the thread_id to a brand new one (THIS IS THE KEY)
        st.session_state.thread_id = str(uuid.uuid4())
        
        # 3. Optional: Add a success message that disappears on rerun
        st.sidebar.success("Memory Nuked!")
        st.rerun()

# Call the dashboard
render_sidebar_dashboard()

# --- Update your config to use the dynamic thread_id ---
config = {"configurable": {"thread_id": st.session_state.thread_id}}

# --- 2. System Initialization ---
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
    
    async def get_tools():
        client = MultiServerMCPClient({
            "environment_tools": {"command": "python", "args": ["mcp_server.py"], "transport": "stdio"}
        })
        return await client.get_tools()

    tools = asyncio.run(get_tools())
    
    # Domain-Locked System Prompt
    system_prompt = (
        "You are the Triage Commander, a specialized Supply Chain AI Agent. "
        "Your expertise is EXCLUSIVELY limited to Supply Chain Management (SCM), "
        "Logistics, Inventory, and Procurement.\n\n"
        "--- OPERATIONAL SCOPE ---\n"
        "1. SHIPMENTS: Track status, investigate delays, and assess weather impact.\n"
        "2. INVENTORY: Query stock levels, burn rates, and forecast stockouts.\n"
        "3. PURCHASING: Draft Purchase Orders (POs) and identify suppliers.\n"
        "4. GENERAL SCM: Answer questions about supply chain concepts.\n\n"
        "--- STRICT CONSTRAINTS ---\n"
        "- If a user asks a non-supply chain question, politely refuse and pivot back to SCM.\n"
        "- If asked about Machine Learning, only explain it in the context of SCM.\n"
        "- Never perform actions (like drafting POs) without human approval via the tools."
    )
    
    memory = MemorySaver()
    
    # Initialize the Agent with Breakpoints
    agent = create_react_agent(
        model=llm, 
        tools=tools, 
        prompt=system_prompt, 
        checkpointer=memory,
        interrupt_before=["tools"] 
    )
    return agent

agent = init_swarm()
config = {"configurable": {"thread_id": "main-scm-session"}}

# --- 3. Helper: Run Agent Stream ---
async def process_stream(inputs):
    """Processes the LangGraph stream and updates the UI."""
    async for chunk in agent.astream(inputs, config=config, stream_mode="values"):
        # We don't need to print here because we render history from memory below
        pass
    st.rerun()

# --- 4. Render Chat History Directly from Agent Memory ---
state = agent.get_state(config)
messages = state.values.get("messages", [])

for msg in messages:
    if msg.type == "human":
        with st.chat_message("user"):
            st.markdown(msg.content)
    elif msg.type == "ai" and msg.content:
        with st.chat_message("assistant"):
            st.markdown(msg.content)
    elif msg.type == "tool":
        with st.chat_message("tool", avatar="🛠️"):
            st.caption(f"**Action Log:** {msg.content}")

# --- 5. Human-in-the-Loop (HITL) Intercept ---
if state.next and "tools" in state.next:
    st.warning("⚠️ **Approval Required!** The Commander has proposed an action.")
    
    last_msg = messages[-1]
    for tc in last_msg.tool_calls:
        st.code(f"Tool: {tc['name']}\nArguments: {tc['args']}")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ Approve Action", use_container_width=True):
            asyncio.run(process_stream(None))
    with col2:
        if st.button("❌ Reject Action", use_container_width=True):
            rejection_messages = [
                ToolMessage(
                    tool_call_id=tc["id"],
                    content="ERROR: The Human Supervisor rejected this action. Do NOT proceed. Acknowledge this."
                ) for tc in last_msg.tool_calls
            ]
            agent.update_state(config, {"messages": rejection_messages}, as_node="tools")
            asyncio.run(process_stream(None))

# --- 6. Chat Input ---
elif prompt := st.chat_input("Enter a task for the System..."):
    # Render user prompt immediately
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Process the request
    asyncio.run(process_stream({"messages": [{"role": "user", "content": prompt}]}))