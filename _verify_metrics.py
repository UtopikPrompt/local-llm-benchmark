"""Temporary verification script for the quality Aggregator (deleted after use)."""
import json
from local_llm_benchmark.quality.metrics import Aggregator, DIMENSIONS
from local_llm_benchmark.quality.judge import make_judge

judge = make_judge()
a = Aggregator(judges={d.name: make_judge() for d in DIMENSIONS if d.requires_judge})
a.add_many([
    {
        "answer": "Yes, the answer is correct and relevant to the question.",
        "question": "What is 2+2?",
        "instruction": "Answer concisely",
        "source": "The premise states 2+2=4.",
        "context": "Math question",
        "topic": "math",
    }
])
print("MEAN", json.dumps(a.mean(), default=str))
print("STD", json.dumps(a.std(), default=str))
print("N", {k: len(v) for k, v in a.scores.items()})
