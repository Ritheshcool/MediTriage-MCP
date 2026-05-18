# 🏥 MediTriage — Intelligent Multi-Agent Healthcare Coordination

> **Next-generation patient triage & appointment scheduling powered by the Model Context Protocol (MCP)**

MediTriage is a multi-agent AI system that acts as an intelligent hospital front-desk coordinator. A patient describes their symptoms in natural language, and the system autonomously triages them, validates findings against real medical data, finds the right specialist, and books an appointment — all within a single, seamless conversation.

---

## ✨ Key Features

| Feature | Description |
|---|---|
| 🧠 **AI-Powered Triage** | Classifies symptom severity (1–10) and recommends the right medical specialty |
| 🔍 **Real-Time Validation** | Cross-references symptoms against live medical sources via Tavily web search |
| 🏥 **Doctor Discovery** | Queries the hospital's Notion database for available specialists |
| 📅 **One-Click Booking** | Renders interactive time slot buttons; books directly to Google Calendar |
| 🚨 **Priority Alerts** | Automatically sends Slack notifications for high-severity cases |
| 🧠 **Patient Memory** | Remembers returning patients via a persistent knowledge graph |
| ⚡ **Real-Time UI** | WebSocket-driven interface with dynamic doctor cards and clickable slot grids |

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     FRONTEND (Browser)                      │
│         HTML + Vanilla CSS + JavaScript + WebSocket          │
│     Dynamic Doctor Cards │ Clickable Slot Grid │ Chat UI     │
└────────────────────────────┬────────────────────────────────┘
                             │ WebSocket (ws://localhost:8000)
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                 BACKEND (Python + FastAPI)                    │
│                                                              │
│  ┌──────────────────┐    ┌─────────────────────────────┐     │
│  │   Orchestrator    │◄──►│      Azure OpenAI GPT-4      │     │
│  │  (Agent Loop)     │    │   (Reasoning & Tool Calls)   │     │
│  └────────┬─────────┘    └─────────────────────────────┘     │
│           │                                                   │
│  ┌────────▼─────────┐                                        │
│  │    MCP Hub        │  ← Dynamic Tool Discovery (56 tools)  │
│  │  (Router/Facade)  │                                        │
│  └────────┬─────────┘                                        │
└───────────┼──────────────────────────────────────────────────┘
            │
   ┌────────┴────────────────────────────────────────┐
   │              6 MCP Servers (Subprocesses)        │
   │                                                  │
   │  🏥 Triage    🔍 Tavily    📋 Notion             │
   │  📅 Calendar  💬 Slack     🧠 Memory             │
   └──────────────────────────────────────────────────┘
```

---

## 🔧 The 6 MCP Servers

| # | Server | Type | Tools | Purpose |
|---|--------|------|-------|---------|
| 1 | **Triage** | Custom Python | `classify_severity`, `recommend_specialty`, `get_symptom_info`, `find_doctors`, `get_available_slots`, `book_appointment` | Core medical logic, doctor lookup, and calendar booking wrapper |
| 2 | **Tavily** | NPM Package | `tavily_search`, `tavily_extract`, `tavily_crawl`, `tavily_map`, `tavily_research` | Web search to validate symptoms against real medical data |
| 3 | **Notion** | NPM Package | 22 API tools | Hospital database — doctor directory & patient records |
| 4 | **Google Calendar** | NPM Package | `list_calendars`, `create_calendar_event`, etc. | Doctor scheduling and appointment management |
| 5 | **Slack** | NPM Package | `slack_post_message`, `slack_list_channels`, etc. | Staff notifications for priority/emergency cases |
| 6 | **Memory** | NPM Package | `create_entities`, `search_nodes`, `read_graph`, etc. | Persistent knowledge graph for patient history |

---

## 🚀 Getting Started

### Prerequisites

- **Python 3.10+**
- **Node.js 18+** (for NPM-based MCP servers)
- **Azure OpenAI** API access
- **API Keys** for: Notion, Tavily, Slack, Google Calendar

### 1. Clone the repository

```bash
git clone https://github.com/Ritheshcool/MediTriage-MCP.git
cd MediTriage-MCP
```

### 2. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment variables

Create a `.env` file in the project root:

```env
# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://your-endpoint.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key
AZURE_OPENAI_DEPLOYMENT=your-deployment-name
AZURE_OPENAI_API_VERSION=2024-08-01-preview

# Tavily Search
TAVILY_API_KEY=your-tavily-key

# Notion
NOTION_API_KEY=your-notion-key
NOTION_DOCTOR_DB_ID=your-doctor-database-id
NOTION_PATIENT_DB_ID=your-patient-database-id

# Slack
SLACK_BOT_TOKEN=xoxb-your-slack-token
SLACK_TEAM_ID=your-team-id

# Google Calendar
GOOGLE_CREDENTIALS_PATH=./credentials.json
```

### 4. Set up Google Calendar

Place your `credentials.json` (OAuth client secret) in the project root. On first booking, a browser window will open for one-time OAuth consent. After that, a `token.json` is saved and reused automatically.

### 5. Seed the Notion database (optional)

```bash
python scripts/seed_notion.py
```

### 6. Run the application

```bash
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

Open [http://localhost:8000](http://localhost:8000) in your browser.

---

## 📂 Project Structure

```
MediTriage-MCP/
├── backend/
│   ├── main.py                 # FastAPI app + WebSocket handler
│   ├── config.py               # MCP server definitions + env vars
│   ├── agent/
│   │   ├── orchestrator.py     # AI Agent Loop (ReAct pattern)
│   │   └── prompts.py          # System prompt for the LLM
│   └── mcp_client/
│       └── hub.py              # MCP Hub — dynamic tool discovery & routing
├── frontend/
│   ├── index.html              # Main page
│   ├── app.js                  # WebSocket handler + dynamic UI rendering
│   └── style.css               # Premium dark-mode UI styles
├── mcp_servers/
│   └── triage/
│       ├── server.py           # Custom FastMCP server (6 tools)
│       └── data/
│           ├── symptoms.json   # Symptom severity knowledge base
│           └── specialties.json# Medical specialty mappings
├── scripts/
│   └── seed_notion.py          # Seeds the Notion doctor directory
├── requirements.txt
└── .gitignore
```

---

## 🔄 How It Works

1. **Patient** describes symptoms in the chat UI
2. **Orchestrator** sends the message to Azure OpenAI with all 56 tool schemas
3. **AI** decides to call `triage.classify_severity` → Hub routes it to the Triage subprocess
4. **AI** calls `tavily.tavily_search` to validate findings against real medical data
5. **AI** checks `memory.search_nodes` for any previous visits by this patient
6. **AI** presents triage summary and asks if the patient wants to book
7. **AI** calls `triage.find_doctors` → Backend intercepts and sends structured data via WebSocket
8. **Frontend** renders interactive **Doctor Cards** with "View Slots" buttons
9. Patient clicks a doctor → **AI** calls `triage.get_available_slots`
10. **Frontend** renders a **clickable time slot grid**
11. Patient clicks a slot → **AI** calls `triage.book_appointment` → Google Calendar event created
12. For priority cases, **AI** sends a Slack alert to the medical team

---

## 🛠️ Technical Highlights

- **Dynamic Tool Discovery**: Tools are not hardcoded — they are discovered at runtime via MCP's `list_tools` protocol. Adding a new server is a single config line.
- **Schema Sanitization**: Built an interceptor in `hub.py` that normalizes third-party MCP schemas to satisfy Azure OpenAI's strict JSON Schema validation.
- **Hybrid UI Architecture**: The backend sends parallel WebSocket events (text + structured JSON), enabling the frontend to render rich, interactive components inside a conversational chat flow.
- **Wrapper Pattern**: Abstracted complex Google Calendar API requirements into a simple `book_appointment(doctor, patient, date, time, reason)` tool to eliminate LLM hallucination issues.

---

## 📄 License

This project is for educational and demonstration purposes.

---

**Built with ❤️ using MCP, FastAPI, Azure OpenAI, and a lot of coffee.**
