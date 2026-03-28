# Mini Agent Orchestrator

An event-driven order processing agent. It takes natural language requests, uses Claude to plan a sequence of actions, then executes them asynchronously with dependency tracking and error handling.

## Architecture

```
User Request (natural language)
        |
        v
   +---------+
   | Planner |  <-- Anthropic Claude API
   +----+----+
        | Produces a DAG of TaskSteps
        v
  +--------------+
  | Orchestrator |  <-- Executes steps, respects dependencies
  +------+-------+
         | Calls registered tools
    +----+----+
    v         v
cancel_order  send_email
```

## Design Decisions

- **No LangChain.** The planner, orchestrator, and tool registry are written from scratch.
- **DAG-based parallel execution.** The orchestrator groups steps into layers based on their dependencies. Steps within the same layer (no dependency between them) run concurrently via `asyncio.gather`. Steps that depend on earlier ones wait for that layer to finish first.
- **Failure propagation.** If a step fails, all downstream steps that depend on it are automatically skipped. This prevents sending a confirmation email when the cancellation itself failed.
- **Simulated failures.** `cancel_order` has a random 20% failure rate to test the guardrail logic.

## Setup

```bash
git clone <repo-url>
cd mini-agent-orchestrator

python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

pip install -r requirements.txt
```

## Environment Variables

Create a `.env` file in the project root:

```
ANTHROPIC_API_KEY=sk-ant-api03-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | Yes | Your Anthropic API key for Claude. |

## Running

```bash
python -m uvicorn app.main:app --reload --port 8080
```

The server starts at `http://localhost:8080`.

## Endpoints

### GET /health

Returns `{"status": "ok"}`. Useful for readiness checks.

### POST /process

```bash
curl -X POST http://localhost:8080/process \
  -H "Content-Type: application/json" \
  -d '{"message": "Cancel my order #9921 and email me the confirmation at user@example.com"}'
```

### Success Response

```json
{
  "status": "success",
  "plan": [
    {"step_id": 0, "action": "cancel_order", "params": {"order_id": "9921"}, "depends_on": []},
    {"step_id": 1, "action": "send_email", "params": {"email": "user@example.com", "message": "Your order #9921 has been cancelled."}, "depends_on": [0]}
  ],
  "execution": [
    {"step_id": 0, "action": "cancel_order", "status": "success", "result": {"success": true, "order_id": "9921", "message": "Order 9921 has been cancelled successfully"}, "error": null},
    {"step_id": 1, "action": "send_email", "status": "success", "result": {"success": true, "email": "user@example.com", "message": "Email sent to user@example.com"}, "error": null}
  ]
}
```

### Failure Response (cancel_order fails, send_email skipped)

```json
{
  "status": "failed",
  "plan": ["..."],
  "execution": [
    {"step_id": 0, "action": "cancel_order", "status": "failed", "result": {"success": false, "order_id": "9921", "error": "Order cancellation failed: order is already shipped"}, "error": "Order cancellation failed: order is already shipped"},
    {"step_id": 1, "action": "send_email", "status": "skipped", "result": null, "error": "Skipped because dependency step 0 failed"}
  ]
}
```

## API Docs

FastAPI auto-generates interactive docs:
- Swagger UI: `http://localhost:8080/docs`
- ReDoc: `http://localhost:8080/redoc`

## Project Structure

```
app/
├── main.py           # FastAPI app, /process and /health endpoints
├── models.py         # Pydantic models for requests, responses, plan steps
├── planner.py        # LLM planner using Anthropic Claude
├── orchestrator.py   # DAG executor with parallel layer support
└── tools.py          # Simulated async tools (cancel_order, send_email)
```
