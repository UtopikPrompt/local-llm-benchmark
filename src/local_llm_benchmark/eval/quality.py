"""Quality evaluation: deterministic checks plus an optional judge model.

Quality scoring has two layers:

1. **Deterministic checks** — substring matches against an expected signature
   or exact answer, and/or a callable validator. These require no network or
   extra cost.
2. **Judge model** — an optional remote LLM scores the answer. An answer passes
   if any deterministic check passes *or* the judge agrees. Without a judge,
   there is no extra latency or cost.

An answer is *deterministic* only if it passed a deterministic check; the judge
is an additional, probabilistic confirmation.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from local_llm_benchmark.engines.base import Engine
from local_llm_benchmark.results import Row
from local_llm_benchmark.tasks.corpus import Task, TaskValidator


@dataclass
class Judge:
    """An optional judge model used for quality scoring."""

    engine: Engine
    name: str

    async def score(self, task: Task, answer: str) -> tuple[bool, str]:
        """Return ``(agreed, note)`` for *answer*.

        Args:
            task: The task being judged.
            answer: The model's generated answer.

        Returns:
            A tuple ``(agreed, note)`` where *agreed* is ``True`` if the judge
            considers the answer correct and *note* is a human-readable reason.
        """
        prompt = task.prompt
        if task.system:
            prompt = f"{task.system}\n\n{prompt}"
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a meticulous grader. Judge whether the model's "
                    "answer is correct based on the task. Reply with exactly "
                    "'yes' or 'no' and a one-line reason."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Task:\n"
                    f"{task.prompt}\n\n"
                    f"Expected answer:\n{task.expected if task.expected else ''}\n\n"
                    f"Model answer:\n{answer}"
                ),
            },
        ]
        tokens = []
        async for token in self.engine.chat(
            messages, max_tokens=64, stream=False
        ):
            tokens.append(token)
        response = "".join(tokens).strip().lower()
        agreed = "yes" in response
        note = f"judge said {response or 'empty'}" if not agreed else "judge agreed"
        return agreed, note


async def evaluate_quality(
    task: Task,
    answer: str,
    *,
    expected: Optional[str],
    validate: Optional[TaskValidator],
    judge: Optional[Judge] = None,
) -> Row:
    """Evaluate *answer* against *task*'s quality checks.

    Args:
        task: The task being evaluated.
        answer: The model's generated answer.
        expected: Expected substring to search for.
        validate: Optional callable validator.
        judge: Optional :class:`Judge` used to score the answer.

    Returns:
        A :class:`~local_llm_benchmark.results.Row` with the quality verdict.
    """
    deterministic = False
    note = ""

    if expected is not None and re.search(re.escape(expected), answer, flags=re.IGNORECASE):
        deterministic = True
        note = "expected substring found"
    elif validate is not None and validate(answer):
        deterministic = True
        note = "validator passed"
    else:
        note = "no deterministic match"

    judge_agreed = False
    if judge is not None:
        agreed, reason = await judge.score(task, answer)
        judge_agreed = agreed
        note = f"{note}; {reason}"

    passed = deterministic or judge_agreed
    return Row(
        engine="",
        model="",
        task_id=task.id,
        category=getattr(task, "category", "").value if hasattr(task, "category") else "",
        prompt=task.prompt,
        expected=task.expected or "",
        output=answer,
        quality_passed=passed,
        quality_deterministic=deterministic,
        quality_judge=judge_agreed,
        quality_note=note,
    )
