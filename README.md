
```
# 🛡️ Supply Chain Swarm Command Center

An enterprise-grade, agentic AI system designed to monitor logistics, manage inventory, and handle procurement with **Human-in-the-Loop (HITL)** safety protocols. Built using **LangGraph**, **MCP (Model Context Protocol)**, and **Streamlit**.

---

## 🏗️ Architecture Overview

The system operates as an autonomous "Triage Commander" that utilizes a swarm of specialized tools to bridge the gap between AI reasoning and real-world database operations.

- **Orchestration:** LangGraph (Stateful, multi-turn agentic workflows).
- **Communication:** MCP (Model Context Protocol) for secure tool execution.
- **Frontend:** Streamlit (Real-time monitoring and chat interface).
- **Safety:** HITL Breakpoints (AI proposes actions; Human approves/rejects).
- **Memory:** Persistent `MemorySaver` with unique session threading.

---

## 🚀 Quick Start

### 1. Prerequisites
- **Python 3.10+**
- **Azure OpenAI API Access**
- **VS Code** (Recommended) with the "SQLite Viewer" extension.

### 2. Installation
Clone the repository and set up your virtual environment:

```
bash
# Clone the repository
git clone <your-repo-url>
cd supply-chain-swarm

# Create and activate virtual environment
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Mac/Linux:
source venv/bin/activate

# Install dependencies
pip install streamlit asyncio python-dotenv langchain-openai langchain-mcp-adapters langgraph

```

### 3. Environment Setup

Create a `.env` file in the root directory and add your credentials:

```
env
AZURE_OPENAI_ENDPOINT="your-endpoint"
AZURE_OPENAI_API_KEY="your-key"
AZURE_OPENAI_API_VERSION="2024-05-01-preview"
AZURE_OPENAI_DEPLOYMENT_NAME="gpt-4o"

```

### 4. Database Initialization

Generate the mock SQLite databases (`inventory.db` and `logistics.db`):

```
bash
python setup_db.py

```

### 5. Launch the Command Center

Start the application:

```
bash
streamlit run app.py

```
```
---

## 🛠️ Key Features

### 📦 Agentic Tools (MCP Server)

* **Logistics:** Track shipments via coordinates and update status in real-time.
* **Inventory:** Query SKU stock levels, daily burn rates, and forecast stockouts.
* **Procurement:** Draft Purchase Orders and retrieve supplier lead times/contact info.
* **Weather:** Check real-time weather conditions at shipment coordinates using Open-Meteo.

### 🛡️ Human-in-the-Loop (HITL)

The agent is restricted from performing "Write" actions (like drafting POs or changing shipment statuses) without explicit authorization. The UI intercepts these requests and presents an **Approve/Reject** interface.

### 📊 Operations Dashboard

The sidebar provides real-time business intelligence:

* **Delayed Shipments:** Count of shipments requiring immediate attention.
* **Low Stock Alerts:** Items with < 5 days of inventory remaining.
* **Pending POs:** Active procurement requests currently in draft.

---

## 📂 Project Structure

* `app.py`: Streamlit frontend, LangGraph orchestration, and UI rendering.
* `mcp_server.py`: The MCP Tool Server defining all database and API interfaces.
* `setup_db.py`: Database schema definition and mock data population script.
* `databases/`: Local SQLite storage directory (ignored by Git).
* `.gitignore`: Configured to protect API keys and local data.

---

## 📝 Example Queries

* *"What is the status of SHP-123 and is weather impacting it?"*
* *"We are low on SKU-101. Draft a PO for 500 units from our supplier."*
* *"Who is the supplier for SKU-103 and what is their lead time?"*
* *"Set shipment SHP-999 to 'In Transit' now that the delay is resolved."*
```
