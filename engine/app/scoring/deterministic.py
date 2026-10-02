"""Deterministic (non-LLM) scoring for scenario types that do not need a judge model.

Supports the scenario types defined in design section 4:
  * Structured Data Extraction - JSON schema validation.
  * Sentiment                  - lexicon based Positive / Negative / Neutral.
  * Constraint Satisfaction    - multi-constraint boolean checks.

Every scorer returns a small dataclass exposing ``deterministic_success`` and,
where relevant, a ``parse_error_type`` so a subset of scenarios can be evaluated
without any LLM judge.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Iterable


class ScenarioType(str, Enum):
    STRUCTURED_DATA_EXTRACTION = "structured_data_extraction"
    SENTIMENT = "sentiment"
    CONSTRAINT_SATISFACTION = "constraint_satisfaction"


class Sentiment(str, Enum):
    POSITIVE = "Positive"
    NEGATIVE = "Negative"
    NEUTRAL = "Neutral"


class ParseErrorType(str, Enum):
    NONE = "none"
    EMPTY_RESPONSE = "empty_response"
    NOT_JSON = "not_json"
    MISSING_KEY = "missing_key"
    TYPE_MISMATCH = "type_mismatch"


_PYTHON_TYPES: dict[str, tuple[type, ...]] = {
    "string": (str,),
    "str": (str,),
    "integer": (int,),
    "int": (int,),
    "number": (int, float),
    "float": (float,),
    "boolean": (bool,),
    "bool": (bool,),
    "object": (dict,),
    "array": (list,),
    "null": (type(None),),
}


def _matches_type(value: Any, type_name: str) -> bool:
    """Type check that honours the bool/int and null distinctions."""
    if type_name in ("boolean", "bool"):
        return isinstance(value, bool)
    if type_name in ("integer", "int"):
        return isinstance(value, int) and not isinstance(value, bool)
    py_types = _PYTHON_TYPES.get(type_name)
    if py_types is None:
        return True
    return isinstance(value, py_types)


@dataclass
class ParsedResult:
    success: bool
    error_type: ParseErrorType = ParseErrorType.NONE
    raw: str | None = None
    data: Any = None
    error_detail: str | None = None


@dataclass
class StructuredDataScore:
    deterministic_success: bool
    parse_error_type: ParseErrorType = ParseErrorType.NONE
    parsed_data: Any = None


@dataclass
class SentimentScore:
    deterministic_success: bool
    predicted_sentiment: Sentiment
    expected_sentiment: Sentiment | None = None


@dataclass
class ConstraintScore:
    name: str
    satisfied: bool
    detail: str = ""


@dataclass
class ConstraintSatisfactionScore:
    deterministic_success: bool
    constraints: list[ConstraintScore] = field(default_factory=list)

    @property
    def satisfied_constraints(self) -> list[str]:
        return [c.name for c in self.constraints if c.satisfied]

    @property
    def violated_constraints(self) -> list[str]:
        return [c.name for c in self.constraints if not c.satisfied]


@dataclass
class Constraint:
    name: str
    predicate: Callable[[str, Any], bool]
    description: str = ""


@dataclass
class Scenario:
    scenario_type: ScenarioType
    expected: dict = field(default_factory=dict)
    expected_sentiment: str | None = None
    constraints: list[Constraint] = field(default_factory=list)


class JSONSchemaParser:
    """Validate a raw JSON response against a declared schema."""

    def parse(self, raw: str, expected: dict) -> ParsedResult:
        stripped = (raw or "").strip()
        if not stripped:
            return ParsedResult(
                success=False,
                error_type=ParseErrorType.EMPTY_RESPONSE,
                raw=raw,
            )
        try:
            data = json.loads(stripped)
        except (json.JSONDecodeError, TypeError):
            return ParsedResult(
                success=False,
                error_type=ParseErrorType.NOT_JSON,
                raw=raw,
            )
        error = self._validate(data, expected, path="root")
        if error is None:
            return ParsedResult(
                success=True,
                error_type=ParseErrorType.NONE,
                raw=raw,
                data=data,
            )
        return ParsedResult(
            success=False,
            error_type=error[0],
            raw=raw,
            data=data,
            error_detail=error[1],
        )

    def _validate(
        self, value: Any, schema: Any, path: str
    ) -> tuple[ParseErrorType, str] | None:
        if isinstance(schema, str):
            if not _matches_type(value, schema):
                return ParseErrorType.TYPE_MISMATCH, f"{path}: expected {schema}"
            return None
        if not isinstance(schema, dict):
            return None

        schema_type = schema.get("type")
        if schema_type and not _matches_type(value, schema_type):
            return ParseErrorType.TYPE_MISMATCH, f"{path}: expected {schema_type}"

        if isinstance(value, dict):
            for key in schema.get("required", []):
                if key not in value:
                    return (
                        ParseErrorType.MISSING_KEY,
                        f"{path}.{key} (missing required key)",
                    )
            for key, sub_schema in schema.get("properties", {}).items():
                if key in value:
                    err = self._validate(value[key], sub_schema, f"{path}.{key}")
                    if err:
                        return err

        if isinstance(value, list):
            items_schema = schema.get("items")
            if items_schema:
                for idx, item in enumerate(value):
                    err = self._validate(item, items_schema, f"{path}[{idx}]")
                    if err:
                        return err

        return None


_POSITIVE_WORDS: set[str] = {
    "good", "great", "excellent", "amazing", "wonderful", "loved", "love",
    "best", "happy", "joy", "joyful", "fantastic", "awesome", "perfect",
    "nice", "beautiful", "brilliant", "outstanding", "superb", "delightful",
    "positive", "win", "wins", "pros", "recommend", "recommends", "enjoy",
    "pleased", "thank", "thanks", "grateful", "satisfied", "fave",
}

_NEGATIVE_WORDS: set[str] = {
    "bad", "terrible", "awful", "horrible", "hated", "hate", "worst", "sad",
    "angry", "disappointing", "disappointed", "poor", "broken", "wrong",
    "negative", "lose", "loses", "cons", "fail", "fails", "failure", "ugly",
    "useless", "annoying", "frustrating", "annoyed", "upset", "dislike",
    "waste", "regret",
}

_NEGATIONS: set[str] = {"not", "no", "never", "without", "hardly", "barely"}


class SentimentAnalyzer:
    """Lexicon based Positive / Negative / Neutral classifier."""

    def analyze(self, text: str) -> Sentiment:
        words = self._tokenize(text or "")
        score = 0
        for i, word in enumerate(words):
            if word in _NEGATIVE_WORDS:
                score += -1 if not self._is_negated(words, i) else 1
            elif word in _POSITIVE_WORDS:
                score += 1 if not self._is_negated(words, i) else -1
        if score > 0:
            return Sentiment.POSITIVE
        if score < 0:
            return Sentiment.NEGATIVE
        return Sentiment.NEUTRAL

    def _tokenize(self, text: str) -> list[str]:
        return re.findall(r"[a-z']+", text.lower())

    def _is_negated(self, words: list[str], index: int) -> bool:
        if index == 0:
            return False
        prev = words[index - 1]
        return prev in _NEGATIONS or prev.endswith("n't")


def is_valid_json() -> Callable[[str, Any], bool]:
    def _predicate(raw: str, data: Any) -> bool:
        return isinstance(data, dict) or isinstance(data, list)

    return _predicate


def contains_keyword(keyword: str) -> Callable[[str, Any], bool]:
    needle = keyword.lower()

    def _predicate(raw: str, data: Any) -> bool:
        return needle in (raw or "").lower()

    return _predicate


def field_min_length(field_name: str, minimum: int) -> Callable[[str, Any], bool]:
    def _predicate(raw: str, data: Any) -> bool:
        if isinstance(data, dict) and field_name in data:
            return len(str(data[field_name])) >= minimum
        return False

    return _predicate


def score_structured_data(raw: str, expected: dict) -> StructuredDataScore:
    parsed = JSONSchemaParser().parse(raw, expected)
    return StructuredDataScore(
        deterministic_success=parsed.success,
        parse_error_type=parsed.error_type,
        parsed_data=parsed.data,
    )


def score_sentiment(raw: str, expected_sentiment: str | None) -> SentimentScore:
    predicted = SentimentAnalyzer().analyze(raw)
    expected = Sentiment(expected_sentiment) if expected_sentiment else None
    return SentimentScore(
        deterministic_success=expected is None or predicted == expected,
        predicted_sentiment=predicted,
        expected_sentiment=expected,
    )


def score_constraints(
    raw: str, constraints: Iterable[Constraint]
) -> ConstraintSatisfactionScore:
    parsed = JSONSchemaParser().parse(raw, {})
    results: list[ConstraintScore] = []
    for constraint in constraints:
        try:
            satisfied = bool(constraint.predicate(raw, parsed.data))
        except Exception as exc:  # pragma: no cover - defensive guard
            satisfied = False
            detail = f"error: {exc}"
        else:
            detail = constraint.description or ""
        results.append(
            ConstraintScore(
                name=constraint.name,
                satisfied=satisfied,
                detail=detail,
            )
        )
    return ConstraintSatisfactionScore(
        deterministic_success=bool(results) and all(c.satisfied for c in results),
        constraints=results,
    )


def score_scenario(scenario: Scenario, raw: str) -> Any:
    if scenario.scenario_type is ScenarioType.STRUCTURED_DATA_EXTRACTION:
        return score_structured_data(raw, scenario.expected)
    if scenario.scenario_type is ScenarioType.SENTIMENT:
        return score_sentiment(raw, scenario.expected_sentiment)
    if scenario.scenario_type is ScenarioType.CONSTRAINT_SATISFACTION:
        return score_constraints(raw, scenario.constraints)
    raise ValueError(f"Unsupported scenario type: {scenario.scenario_type}")