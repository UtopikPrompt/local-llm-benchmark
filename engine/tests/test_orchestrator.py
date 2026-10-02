"""Slice 6 — Orchestrator tests (restored)."""

import sqlite3

from engine.app.orchestrator.orchestrator import (
    ConfigMatrix,
    EngineConfig,
    JudgeConfig,
    MatrixCell,
    ModelConfig,
    Orchestrator,
    Phase,
    ResultStore,
    ScenarioConfig,
    default_config,
)


def test_default_ollama_config() -> None:
    matrix = default_config()

    assert matrix.cells, "default matrix must contain at least one cell"
    assert matrix.expected_cells == len(matrix.cells)

    for cell in matrix.cells:
        assert cell.engine.kind == "ollama"
        assert cell.engine.model == "llama3.1"
        assert cell.model.provider == "ollama"
        assert cell.model.name == "llama3.1"


def test_orchestrator_runs_phases(tmp_path) -> None:
    matrix = default_config()

    calls = {"run": 0, "score": 0, "persist": 0}

    def engine_runner(cell: MatrixCell) -> str:
        calls["run"] += 1
        return f"run-output:{cell.scenario.name}"

    def judge(cell: MatrixCell, run_output: str) -> int:
        calls["score"] += 1
        return 1 if "repeat" in run_output else 0

    db_path = tmp_path / "matrix.db"
    store = ResultStore(db_path)
    orchestrator = Orchestrator(
        matrix,
        engine_runner=engine_runner,
        judge=judge,
        store=store,
    )

    metrics = orchestrator.run()

    # Full matrix run produces a row for every cell.
    assert metrics.cells == matrix.expected_cells == 2
    assert store.count() == matrix.expected_cells

    # Each phase ran exactly once per cell (phase accounting).
    assert calls["run"] == matrix.expected_cells
    assert calls["score"] == matrix.expected_cells
    for phase in Phase:
        assert metrics.phase_counts[phase.value] == matrix.expected_cells
    assert metrics.errors == []

    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute(
            "SELECT engine, model, scenario, judge, score "
            "FROM results ORDER BY scenario LIMIT 1"
        ).fetchone()
    finally:
        conn.close()

    assert row is not None
    engine, model, scenario, judge, score = row
    assert engine == "ollama"
    assert model == "llama3.1"
    assert judge == "gpt-judge"
    assert score in {"0", "1"}