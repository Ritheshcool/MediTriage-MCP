<div align="center">

# 🏥 MediTriage MCP

**An AI-powered medical triage assistant built on the Model Context Protocol.**

Describe your symptoms in plain language — MediTriage triages your case, finds the right specialist, and shows you available appointment slots, all in real time.

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Azure OpenAI](https://img.shields.io/badge/Azure_OpenAI-GPT--4-0078D4?style=flat&logo=microsoftazure&logoColor=white)](https://azure.microsoft.com/en-us/products/ai-services/openai-service)
[![MCP](https://img.shields.io/badge/MCP-Model_Context_Protocol-8B5CF6?style=flat)](https://modelcontextprotocol.io)

</div>

---

## 📋 Table of contents

- [What is MediTriage?](#-what-is-meditriage)
- [Features](#-features)
- [Architecture](#-architecture)
- [Project structure](#-project-structure)
- [Tech stack](#-tech-stack)
- [Getting started](#-getting-started)
- [How it works](#-how-it-works)
- [API reference](#-api-reference)
- [Contributing](#-contributing)
- [Disclaimer](#-disclaimer)

---

## 🩺 What is MediTriage?

MediTriage is a real-time AI medical assistant that uses the **Model Context Protocol (MCP)** to connect an Azure OpenAI language model to a network of 6 specialized backend servers — each responsible for a distinct medical workflow: symptom triage, doctor discovery, appointment scheduling, and more.

Users interact through a chat interface. Behind the scenes, the AI agent dynamically selects and calls the right MCP tools, synthesizes the results, and returns a structured response complete with doctor cards and clickable booking slots.

---

## ✨ Features

| Feature | Description |
|---|---|
| 🤖 **AI Symptom Triage** | Describe symptoms in plain language — the agent classifies urgency and suggests the right specialty |
| 👨‍⚕️ **Doctor Discovery** | Finds relevant specialists based on your triage result |
| 📅 **Slot Booking** | Returns available appointment slots as interactive UI buttons |
| ⚡ **Real-time Chat** | Full-duplex WebSocket connection — zero page reloads |
| 🔌 **MCP Architecture** | 6 specialized MCP servers, each handling one domain |
| 🧠 **Persistent Sessions** | Per-session conversation history so the agent remembers context |
| 🖥️ **Built-in UI** | FastAPI serves the chat frontend — no separate server needed |

---

## 🏗️ Architecture

### System overview

```mermaid
graph TB
    subgraph Browser["🌐 Browser"]
        UI["Chat UI\nHTML · CSS · JS"]
    end

    subgraph Backend["⚙️ FastAPI Backend  (main.py)"]
        WS["WebSocket Handler\n/ws/chat"]
        AGENT["🧠 MediTriage Agent\norchestrator.py"]
        HUB["🔌 MCP Client Hub\nhub.py"]
    end

    subgraph MCP["🛠️ MCP Servers"]
        S1["Triage server\nSymptom analysis"]
        S2["Doctors server\nSpecialist lookup"]
        S3["Scheduler server\nSlot availability"]
        S4["Booking server\nAppointments"]
        S5["Records server\nPatient history"]
        S6["Alerts server\nNotifications"]
    end

    AZURE["☁️ Azure OpenAI\nGPT-4"]

    UI -->|"WebSocket /ws/chat"| WS
    WS --> AGENT
    AGENT <-->|"Tool calls"| HUB
    HUB <-->|"MCP protocol"| S1
    HUB <-->|"MCP protocol"| S2
    HUB <-->|"MCP protocol"| S3
    HUB <-->|"MCP protocol"| S4
    HUB <-->|"MCP protocol"| S5
    HUB <-->|"MCP protocol"| S6
    AGENT <-->|"LLM completions"| AZURE
    WS -->|"Response cards"| UI

    style Browser fill:#ede9fe,stroke:#7c3aed,color:#3b0764
    style Backend fill:#dcfce7,stroke:#16a34a,color:#14532d
    style MCP fill:#fff7ed,stroke:#ea580c,color:#431407
    style AZURE fill:#dbeafe,stroke:#2563eb,color:#1e3a8a
```

---

### Request flow

```mermaid
sequenceDiagram
    actor User
    participant UI as Chat UI
    participant WS as FastAPI WebSocket
    participant Agent as MediTriage Agent
    participant Hub as MCP Client Hub
    participant MCP as MCP Servers (×6)
    participant LLM as Azure OpenAI

    User->>UI: Types symptom message
    UI->>WS: JSON over WebSocket
    WS->>UI: status: "Analyzing your symptoms…"
    WS->>Agent: process_message(session_id, message)

    loop Agent tool-call loop (max 15 iterations)
        Agent->>LLM: chat.completions with all MCP tools
        LLM-->>Agent: tool_call plan
        Agent->>Hub: call_tool(tool_name, args)
        Hub->>MCP: MCP protocol request
        MCP-->>Hub: structured result
        Hub-->>Agent: result
    end

    LLM-->>Agent: final text response
    Agent-->>WS: response + tool_calls_made + doctors + slots

    WS->>UI: type: tool_calls
    WS->>UI: type: response (AI text)
    WS->>UI: type: doctors (doctor cards)
    WS->>UI: type: slots (booking buttons)
    UI->>User: Renders full triage result
```

---

### Agent loop detail

```mermaid
flowchart TD
    A([User message received]) --> B[Add to session history]
    B --> C[Fetch all MCP tool schemas]
    C --> D[Call Azure OpenAI with tools]
    D --> E{Tool calls returned?}
    E -- No --> F[Extract final text response]
    F --> G([Return to WebSocket handler])
    E -- Yes --> H[Identify server via tool_map]
    H --> I[Execute via MCP Hub]
    I --> J{Tool name?}
    J -- find_doctors --> K[Store doctor_data]
    J -- get_available_slots --> L[Store slot_data]
    J -- other --> M[Append result to history]
    K --> M
    L --> M
    M --> N{Max 15 iterations?}
    N -- No --> D
    N -- Yes --> O([Return partial result])

    style A fill:#7c3aed,color:#fff
    style G fill:#16a34a,color:#fff
    style O fill:#ea580c,color:#fff
```

---

## 📁 Project structure

```
MediTriage-MCP/
│
├── backend/                        # FastAPI application
│   ├── agent/
│   │   ├── orchestrator.py         # MediTriageAgent — the AI brain
│   │   └── prompts.py              # System prompt for the LLM
│   ├── mcp_client/
│   │   └── hub.py                  # MCPClientHub — manages 6 server connections
│   ├── config.py                   # Azure OpenAI + server config (loads .env)
│   └── main.py                     # FastAPI app, WebSocket handler, static file serving
│
├── frontend/
│   └── index.html                  # Chat UI (served by FastAPI as static files)
│
├── mcp_servers/
│   └── triage/
│       ├── data/                   # Medical triage knowledge base
│       └── server.py               # MCP triage server implementation
│
├── scripts/                        # Utility and startup scripts
├── requirements.txt                # Python dependencies
└── .gitignore
```

---

## 🛠️ Tech stack

| Layer | Technology | Purpose |
|---|---|---|
| **Backend framework** | FastAPI + Uvicorn | HTTP server, WebSocket handler, static file serving |
| **Real-time comms** | WebSockets | Full-duplex chat between browser and server |
| **AI / LLM** | Azure OpenAI (GPT-4) | Language model for triage, synthesis, and reasoning |
| **Agent protocol** | MCP (Model Context Protocol) | Standardized interface to all tool servers |
| **Frontend** | HTML / CSS / JavaScript | Chat UI — served directly from FastAPI |
| **Configuration** | python-dotenv | Loads `.env` variables for API keys and endpoints |

---

## 🚀 Getting started

### Prerequisites

- Python **3.10+**
- An **Azure OpenAI** resource with a GPT-4 deployment
- Git

### 1. Clone the repo

```bash
git clone https://github.com/Ritheshcool/MediTriage-MCP.git
cd MediTriage-MCP
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment variables

Create a `.env` file in the project root:

```env
# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your_azure_openai_api_key
AZURE_OPENAI_DEPLOYMENT=your_deployment_name
AZURE_OPENAI_API_VERSION=2024-02-15-preview
```

### 4. Start the application

```bash
python -m backend.main
```

Or with Uvicorn directly:

```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

### 5. Open the chat UI

Navigate to [http://localhost:8000](http://localhost:8000) — the frontend is served automatically.

At startup you'll see the 6 MCP servers connect in the logs:

```
✅ triage:     N tools — Symptom analysis
✅ doctors:    N tools — Specialist lookup
✅ scheduler:  N tools — Slot availability
✅ booking:    N tools — Appointment booking
✅ records:    N tools — Patient history
✅ alerts:     N tools — Notifications

MediTriage ready — X tools across 6 servers
```

---

## 🔍 How it works

### The MCP Client Hub

`hub.py` connects to all 6 MCP servers on startup and aggregates their tool schemas. When the agent needs a tool, the hub routes the call to the correct server using an internal `tool_map`.

### The AI Agent

`orchestrator.py` runs a **tool-calling loop** (up to 15 iterations per message):

1. Sends conversation history + all MCP tool schemas to Azure OpenAI
2. If the LLM returns tool calls, executes them via the hub and appends results to history
3. Loops until the LLM returns a plain-text response (no further tool calls)
4. Extracts `doctor_data` and `slot_data` from specific tool results for the frontend

### The WebSocket handler

`main.py` sends multiple typed messages back to the UI for each user message:

```
type: "status"      → "Analyzing your symptoms…"
type: "tool_calls"  → which servers were invoked
type: "response"    → the AI's triage text
type: "doctors"     → doctor cards (if applicable)
type: "slots"       → booking buttons (if applicable)
```

---

## 📡 API reference

### `GET /`

Serves the chat frontend (`index.html`).

### `GET /api/status`

Returns connection status and available tools for all 6 MCP servers.

```json
{
  "triage":    { "connected": true, "tools": ["..."], "description": "Symptom analysis" },
  "doctors":   { "connected": true, "tools": ["..."], "description": "Specialist lookup" },
  "scheduler": { "connected": true, "tools": ["..."], "description": "Slot availability" }
}
```

### `WS /ws/chat`

WebSocket endpoint for the real-time chat.

**Send** (client → server):

```json
{ "message": "I have a fever and sore throat for 3 days" }
```

**Receive** (server → client) — multiple messages per request:

| `type` | Payload | Description |
|---|---|---|
| `status` | `{ "message": "..." }` | Thinking indicator |
| `tool_calls` | `{ "calls": [{"server": "...", "tool": "..."}] }` | Which MCP tools were used |
| `response` | `{ "message": "...", "tool_calls_count": N }` | The AI's triage response |
| `doctors` | `{ "specialty": "...", "doctors": [...] }` | Doctor recommendation cards |
| `slots` | `{ "doctor": "...", "slots": [...] }` | Available booking slots |
| `error` | `{ "message": "..." }` | Error details |

---

## 🤝 Contributing

Contributions are welcome! Here's how:

1. **Fork** the repository
2. **Create** a feature branch: `git checkout -b feature/your-feature`
3. **Commit** your changes: `git commit -m "feat: add your feature"`
4. **Push** to the branch: `git push origin feature/your-feature`
5. **Open** a Pull Request

Please keep PRs focused — one feature or fix per PR makes review much easier.

---

## ⚠️ Disclaimer

> MediTriage is a **demonstration project** and is **not a substitute for professional medical advice, diagnosis, or treatment**. Always consult a qualified healthcare provider for any medical concerns. In a medical emergency, call your local emergency services immediately.

---

<div align="center">

Built with ❤️ using FastAPI · Azure OpenAI · Model Context Protocol

</div>
