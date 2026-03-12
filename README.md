# 🛡️ Supply Chain Swarm Command Center

An enterprise-grade, agentic AI system designed to monitor logistics, manage inventory, and handle procurement with **Human-in-the-Loop (HITL)** safety protocols. Built using **LangGraph**, **MCP (Model Context Protocol)**, and **Streamlit**.

---

# 🏗️ Architecture Overview

The system operates as an autonomous **"Triage Commander"** that utilizes a swarm of specialized tools to bridge the gap between AI reasoning and real-world database operations.

- **Orchestration:** LangGraph (Stateful, multi-turn agentic workflows)
- **Communication:** MCP (Model Context Protocol) for secure tool execution
- **Frontend:** Streamlit (Real-time monitoring and chat interface)
- **Safety:** HITL Breakpoints (AI proposes actions; Human approves/rejects)
- **Memory:** Persistent `MemorySaver` with unique session threading

---

# 🧩 System Architecture

```
            USER INTERACTION
                  |
          [ 1. FRONTEND LAYER ] <--------------------------+
          +-------------------------------------------+    |
          |   Streamlit Web UI (app.py)               |    |
          |                                           |    |
          |  +----------------+   +----------------+  |    | (Updates metrics)
          |  | Chat Interface |   | Live Dashboard |<-+----+
          |  +-------+--------+   +----------------+  |    |
          |          |                   ^            |    |
          |  +-------v--------+          |            |    |
          |  | HITL Intercept |----------+            |    |
          |  | Approve/Reject | (Manual Gatekeeper)   |    |
          |  +-------+--------+                       |    |
          +----------|--------------------------------+    |
                     |                                     |
          [ 2. ORCHESTRATION LAYER ]                       |
          +----------v--------------------------------+    |
          |   LangGraph Agent Engine                  |    |
          |                                           |    |
          |  +---------------+   +-----------------+  |    |
          |  | Triage Agent  |-->|  Memory Saver   |  |    |
          |  | (ReAct Logic) |   | (thread_id/UUID)|  |    |
          |  +-------+-------+   +-----------------+  |    |
          |          |                                |    |
          |  +-------v-------+ (Breakpoint)           |    |
          |  | interrupt_before ["tools"]             |    |
          |  +-------+-------+                        |    |
          +----------|--------------------------------+    |
                     |                                     |
          [ 3. COMMUNICATION LAYER ]                       |
          +----------v--------------------------------+    |
          |   MCP Bridge (Client/Server)              |    |
          |                                           |    |
          |  +------------+       +---------------+   |    |
          |  | MCP Client |<----->|  MCP Server   |   |    |
          |  +------------+       | (mcp_server.py)|  |    |
          |                       +-------+-------+   |    |
          +-------------------------------|-----------+    |
                                          |                |
          [ 4. DATA & API LAYER ]         |                |
          +-------------------------------v-----------+    |
          |                                           |    |
          |  +--------------+       +--------------+  |    |
          |  | inventory.db |       | logistics.db |--+----+
          |  +--------------+       +--------------+  |
          |          ^                     ^          |
          |          |        +------------+          |
          |          +--------| Open-Meteo |          |
          |                   | Weather API|          |
          |                   +------------+          |
          +-------------------------------------------+
```

---

# 🚀 Quick Start

## 1️⃣ Prerequisites

- Python **3.10+**
- Azure OpenAI API Access
- **VS Code** (Recommended) with **SQLite Viewer extension**

---

## 2️⃣ Installation

Clone the repository and set up your virtual environment.

```bash
# Clone the repository
git clone <your-repo-url>
cd supply-chain-swarm

# Create virtual environment
python -m venv venv

# Activate environment

# Windows
venv\Scripts\activate

# Mac/Linux
source venv/bin/activate

# Install dependencies
pip install streamlit asyncio python-dotenv langchain-openai langchain-mcp-adapters langgraph
```

---

## 3️⃣ Environment Setup

Create a `.env` file in the root directory:

```env
AZURE_OPENAI_ENDPOINT="your-endpoint"
AZURE_OPENAI_API_KEY="your-key"
AZURE_OPENAI_API_VERSION="2024-05-01-preview"
AZURE_OPENAI_DEPLOYMENT_NAME="gpt-4o"
```

---

## 4️⃣ Database Initialization

Generate the mock SQLite databases.

```bash
python setup_db.py
```

This creates:

- `inventory.db`
- `logistics.db`

---

## 5️⃣ Launch the Command Center

Start the application.

```bash
streamlit run app.py
```

---

# 🛠️ Key Features

## 📦 Agentic Tools (MCP Server)

- **Logistics**
  - Track shipments via coordinates
  - Update shipment status in real-time

- **Inventory**
  - Query SKU stock levels
  - Calculate daily burn rates
  - Forecast stockouts

- **Procurement**
  - Draft Purchase Orders
  - Retrieve supplier lead times and contacts

- **Weather**
  - Check real-time conditions using **Open-Meteo API**

---

## 🛡️ Human-in-the-Loop (HITL)

The agent is restricted from performing **write operations** without human approval.

Examples:
- Draft Purchase Orders
- Change shipment status
- Update logistics records

The UI intercepts these actions and presents an **Approve / Reject interface**.

---

# 📊 Operations Dashboard

The sidebar provides real-time operational insights.

**Metrics include:**

- 🚚 **Delayed Shipments**  
  Shipments requiring immediate attention

- 📦 **Low Stock Alerts**  
  SKUs with **less than 5 days** of inventory remaining

- 📑 **Pending POs**  
  Procurement requests currently in draft state

---

# 📂 Project Structure

```
supply-chain-swarm/

├── app.py
├── mcp_server.py
├── setup_db.py
│
├── databases/
│   ├── inventory.db
│   └── logistics.db
│
└── .gitignore
```

### File Descriptions

- **app.py**  
  Streamlit frontend, LangGraph orchestration, UI rendering

- **mcp_server.py**  
  MCP Tool Server defining database and API interfaces

- **setup_db.py**  
  Database schema creation and mock data population

- **databases/**  
  Local SQLite storage (ignored by Git)

- **.gitignore**  
  Protects API keys and local data

---

# 📝 Example Queries

Try asking the system:

- *"What is the status of SHP-123 and is weather impacting it?"*
- *"We are low on SKU-101. Draft a PO for 500 units from our supplier."*
- *"Who is the supplier for SKU-103 and what is their lead time?"*
- *"Set shipment SHP-999 to 'In Transit' now that the delay is resolved."*
