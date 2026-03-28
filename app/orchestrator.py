import asyncio
import logging
from app.models import PlanResult, StepOutcome, StepStatus
from app.tools import TOOL_REGISTRY

logger = logging.getLogger(__name__)


async def _run_step(step, outcomes: dict[int, StepOutcome], all_step_ids: set[int]) -> StepOutcome:
    """Run a single step, checking dependencies first."""
    for dep_id in step.depends_on:
        if dep_id not in all_step_ids:
            logger.error("Step %d: depends on non-existent step %d", step.step_id, dep_id)
            return StepOutcome(
                step_id=step.step_id,
                action=step.action,
                status=StepStatus.FAILED,
                error=f"Invalid dependency: step {dep_id} does not exist",
            )
        dep = outcomes.get(dep_id)
        if dep and dep.status in (StepStatus.FAILED, StepStatus.SKIPPED):
            logger.info("Step %d (%s) skipped: dependency %d %s", step.step_id, step.action, dep_id, dep.status.value)
            return StepOutcome(
                step_id=step.step_id,
                action=step.action,
                status=StepStatus.SKIPPED,
                error=f"Skipped because step {dep_id} {dep.status.value}",
            )

    tool_fn = TOOL_REGISTRY.get(step.action)
    if not tool_fn:
        logger.error("Step %d: unknown tool '%s'", step.step_id, step.action)
        return StepOutcome(
            step_id=step.step_id,
            action=step.action,
            status=StepStatus.FAILED,
            error=f"Unknown tool: {step.action}",
        )

    try:
        logger.info("Step %d: running %s(%s)", step.step_id, step.action, step.params)
        result = await tool_fn(**step.params)
        if result.get("success"):
            logger.info("Step %d: %s succeeded", step.step_id, step.action)
            return StepOutcome(step_id=step.step_id, action=step.action, status=StepStatus.SUCCESS, result=result)
        else:
            logger.warning("Step %d: %s failed - %s", step.step_id, step.action, result.get("error"))
            return StepOutcome(step_id=step.step_id, action=step.action, status=StepStatus.FAILED, result=result, error=result.get("error", "Tool returned failure"))
    except Exception as e:
        logger.exception("Step %d: %s raised an exception", step.step_id, step.action)
        return StepOutcome(step_id=step.step_id, action=step.action, status=StepStatus.FAILED, error=str(e))


def _build_layers(plan: PlanResult) -> list[list]:
    """Group steps into layers that can run in parallel.

    Steps with no unresolved dependencies go into the current layer.
    Once a layer finishes, its step IDs are marked as resolved and
    the next layer is built from the remaining steps.
    """
    resolved: set[int] = set()
    remaining = list(plan.steps)
    layers = []

    while remaining:
        layer = [s for s in remaining if all(d in resolved for d in s.depends_on)]
        if not layer:
            # Remaining steps have unresolvable dependencies; push them as a final layer
            layer = remaining
            remaining = []
        else:
            remaining = [s for s in remaining if s not in layer]
        layers.append(layer)
        resolved.update(s.step_id for s in layer)

    return layers


async def execute(plan: PlanResult) -> list[StepOutcome]:
    """Execute a plan as a DAG. Independent steps within a layer run concurrently."""
    outcomes: dict[int, StepOutcome] = {}
    all_step_ids = {s.step_id for s in plan.steps}

    for layer in _build_layers(plan):
        results = await asyncio.gather(*[_run_step(step, outcomes, all_step_ids) for step in layer])
        for outcome in results:
            outcomes[outcome.step_id] = outcome

    return [outcomes[step.step_id] for step in plan.steps]
