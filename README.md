# HotelOps AI

HotelOps AI is an intelligent assistant designed to streamline hotel management operations by proactively identifying resource conflicts, scheduling discrepancies, and room readiness issues. It acts as a digital supervisor that reads simulated property management data (PMS) and presents actionable summaries. The system is built with a strong focus on security, automatically filtering sensitive guest credit card details (PII) and neutralizing prompt injection attacks masquerading as guest comments.

## Architecture Overview

The system uses a client-server Model Context Protocol (MCP) architecture. The Agent Development Kit (ADK) agent spawns a local MCP server process and communicates over standard I/O (stdio) to dynamically call operational tools.

```
[ Hotel Manager User ]
         │
         ▼ (Asks operational question)
 [ LlmAgent (app/agent.py) ]
         │
         ▼ (Queries tools via stdio)
[ MCP Server (mcp_server/hotel_mcp_server.py) ]
         │
         ▼ (Reads & sanitizes data via mcp_server/security.py)
 [ Simulated PMS Data (data/hotel_state.json) ]
```

## Key Concepts & Code Locations

*   **ADK Agent**: Configured in [`app/agent.py`](file:///c:/Users/reshm/Downloads/Projects/hotelops-agent/app/agent.py). This defines the `LlmAgent` and the system instructions that govern its behavior.
*   **MCP Server**: Located in [`mcp_server/hotel_mcp_server.py`](file:///c:/Users/reshm/Downloads/Projects/hotelops-agent/mcp_server/hotel_mcp_server.py). It exposes clean operational APIs to the model.
*   **Security Features**: 
    *   **Data Sanitation**: Scrubbing credit cards and prompt injection attempts in [`mcp_server/security.py`](file:///c:/Users/reshm/Downloads/Projects/hotelops-agent/mcp_server/security.py).
    *   **Instruction-Level Defense**: System instructions in [`app/agent.py`](file:///c:/Users/reshm/Downloads/Projects/hotelops-agent/app/agent.py) warning the model to treat comments strictly as data.
*   **Vibe-Coded with Antigravity**: This prototype was fully designed and built end-to-end using the Antigravity coding assistant.

## Setup Instructions

### Prerequisites
*   Python 3.11+
*   [uv](https://github.com/astral-sh/uv) (recommended package installer)

### 1. Install Dependencies
Set up the virtual environment and sync dependencies:
```bash
uv sync
```

### 2. Configure API Key
Create a `.env` file in the root of the project and add your Gemini Developer API Key:
```env
GEMINI_API_KEY="your-gemini-api-key-here"
```

### 3. Run the Playground
Launch the local ADK developer playground to chat with the agent:
```bash
uv run adk web . --host 127.0.0.1 --port 8080
```
Open **[http://127.0.0.1:8080/dev-ui/?app=app](http://127.0.0.1:8080/dev-ui/?app=app)** in your browser.

---

## Try These Prompts

Test the agent in the playground with these specific operational scenarios:

1.  **VIP/Maintenance Conflict**:
    *   *Prompt*: `"Is room 404 ready for Marcus Aurelius's arrival?"`
    *   *Expected Behavior*: Agent queries occupancy, finds Marcus Aurelius is arriving today and is assigned to room 404. However, it notices room 404 is `out_of_order` due to a leaking AC unit. It proactively flags this conflict and recommends moving him.
2.  **PII Redaction Visibility**:
    *   *Prompt*: `"What's the occupancy summary for today?"`
    *   *Expected Behavior*: Returns today's occupancy details and lists guest comments. In David Miller's comment, the credit card is masked as `[REDACTED-CC]`.
3.  **Prompt Injection Defense**:
    *   *Prompt*: `"What did Sophia Loren ask for in her comment?"`
    *   *Expected Behavior*: The agent queries her upcoming reservation and returns that the comment was flagged: `"[FLAGGED: potential prompt injection — original withheld]"`. It will not upgrade her to the penthouse or execute any instructions inside the comment.
4.  **Resource & Staffing Conflicts**:
    *   *Prompt*: `"Any housekeeping issues I should worry about?"`
    *   *Expected Behavior*: Proactively flags that room 308 (Elizabeth Davis's honeymoon room) is still `in_progress` right before check-in. It also alerts you that **Carlos Mendez** is assigned tasks but is currently `off_duty`.
5.  **Full Executive Synthesis**:
    *   *Prompt*: `"Give me today's executive briefing"`
    *   *Expected Behavior*: Generates a structured synthesis of occupancy metrics, housekeeping status, staffing levels, open maintenance tickets, and warning alerts for any anomalies.

---

## Security (Two-Layer Defense)

*   **MCP-Level Sanitization**: The MCP server pipes all free-text fields through `clean_data()` prior to making them accessible to the LLM context. Credit card sequences are replaced with a redact tag, and suspicious command terms (like "ignore previous instructions") replace the comment string entirely.
*   **Model-Level Guardrails**: The agent's system prompt dictates that comments must be treated as untrusted data fields and forbids following any directions found within them.

## Prototype Disclaimer

**This is a hackathon prototype.** All data is loaded from a local, simulated JSON file ([`data/hotel_state.json`](file:///c:/Users/reshm/Downloads/Projects/hotelops-agent/data/hotel_state.json)) and the MCP server runs locally via stdio. In a production deployment, this would be deployed as a remote web service (via SSE or Streamable HTTP) integrated with OAuth and a real Property Management System (PMS) database.
