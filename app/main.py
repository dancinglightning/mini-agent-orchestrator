import logging
from fastapi import FastAPI, HTTPException
from dotenv import load_dotenv

load_dotenv()

from app.models import UserRequest, AgentResponse, StepStatus
from app.planner import plan
from app.orchestrator import execute

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="Mini Agent Orchestrator", version="1.0.0")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/process", response_model=AgentResponse)
async def process_request(request: UserRequest):
    if request.is_empty:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    logger.info("Processing request: %s", request.message[:100])

    try:
        plan_result = await plan(request.message)
    except Exception as e:
        logger.error("Planning failed: %s", e)
        raise HTTPException(status_code=502, detail="Planning failed. Please try again.")

    if not plan_result.steps:
        logger.info("Planner returned empty plan")
        return AgentResponse(status="no_action", plan=[], execution=[])

    logger.info("Plan created with %d steps", len(plan_result.steps))
    outcomes = await execute(plan_result)

    has_failures = any(o.status == StepStatus.FAILED for o in outcomes)
    has_skips = any(o.status == StepStatus.SKIPPED for o in outcomes)

    if has_failures:
        status = "failed"
    elif has_skips:
        status = "partial_failure"
    else:
        status = "success"

    logger.info("Request completed with status: %s", status)
    return AgentResponse(status=status, plan=plan_result.steps, execution=outcomes)
