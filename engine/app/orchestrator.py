"""Orchestrator coordinates benchmark execution end-to-end."""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.storage.db import JudgeModel, Run, RunResult, RunStatus


@dataclass
class OrchestrationOutcome:
    """Result of executing a single benchmark task."""

    run: Run
    score: float
    detail: str


class Orchestrator:
    """Wires tasks, judges and storage together to run benchmarks."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def execute(self, *, task_id: str, judge: JudgeModel) -> OrchestrationOutcome:
        """Run ``task_id`` against ``judge`` and persist the outcome."""
        run = Run(task_id=task_id, judge=judge, status=RunStatus.RUNNING)
        self._session.add(run)
        self._session.commit()
        self._session.refresh(run)

        score, detail = self._score(run, judge)

        run.status = RunStatus.COMPLETED
        self._session.add(
            RunResult(run_id=run.id, score=int(score), detail=detail)
        )
        self._session.commit()
        self._session.refresh(run)

        return OrchestrationOutcome(run=run, score=score, detail=detail)

    def _score(self, run: Run, judge: JudgeModel) -> tuple[float, str]:
        prompt = f"Evaluate this response for task '{run.task_id}'."
        # In production this invokes the judge model; here it returns a
        # deterministic placeholder so the pipeline stays runnable.
        return 1.0, f"{judge.name} scored '{run.task_id}' ({prompt})"