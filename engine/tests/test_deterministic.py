import json

import pytest

from app.scoring.deterministic import (
    ScenarioType,
    Scenario,
    Sentiment,
    ParseErrorType,
    Constraint,
    is_valid_json,
    contains_keyword,
    field_min_length,
    score_scenario,
    score_structured_data,
    score_sentiment,
    score_constraints,
)

STRUCTURED_SCHEMA = {
    "type": "object",
    "required": ["name", "age"],
    "properties": {
        "name": "string",
        "age": "integer",
        "active": "boolean",
        "tags": "array",
        "address": {
            "type": "object",
            "required": ["city"],
            "properties": {"city": "string", "zip": "string"},
        },
    },
}


@pytest.fixture
def valid_structured_response() -> str:
    return json.dumps(
        {"name": "Alice", "age": 30, "active": True, "tags": ["a", "b"]}
    )


def test_structured_data_success(valid_structured_response: str) -> None:
    score = score_structured_data(valid_structured_response, STRUCTURED_SCHEMA)
    assert score.deterministic_success is True
    assert score.parse_error_type is ParseErrorType.NONE
    assert score.parsed_data["name"] == "Alice"


def test_structured_data_missing_key() -> None:
    score = score_structured_data(json.dumps({"name": "Bob"}), STRUCTURED_SCHEMA)
    assert score.deterministic_success is False
    assert score.parse_error_type is ParseErrorType.MISSING_KEY


def test_structured_data_type_mismatch() -> None:
    score = score_structured_data(
        json.dumps({"name": "Bob", "age": "thirty"}), STRUCTURED_SCHEMA
    )
    assert score.deterministic_success is False
    assert score.parse_error_type is ParseErrorType.TYPE_MISMATCH


def test_structured_data_nested_missing() -> None:
    response = json.dumps({"name": "Bob", "age": 1, "address": {"zip": "00000"}})
    score = score_structured_data(response, STRUCTURED_SCHEMA)
    assert score.deterministic_success is False
    assert score.parse_error_type is ParseErrorType.MISSING_KEY


def test_structured_data_not_json() -> None:
    score = score_structured_data("this is not json", STRUCTURED_SCHEMA)
    assert score.deterministic_success is False
    assert score.parse_error_type is ParseErrorType.NOT_JSON


def test_structured_data_empty() -> None:
    score = score_structured_data("   ", STRUCTURED_SCHEMA)
    assert score.deterministic_success is False
    assert score.parse_error_type is ParseErrorType.EMPTY_RESPONSE


def test_sentiment_positive() -> None:
    score = score_sentiment("I love this, it is great and amazing!", "Positive")
    assert score.deterministic_success is True
    assert score.predicted_sentiment is Sentiment.POSITIVE


def test_sentiment_negative() -> None:
    score = score_sentiment("This is terrible and awful, I hate it.", "Negative")
    assert score.deterministic_success is True
    assert score.predicted_sentiment is Sentiment.NEGATIVE


def test_sentiment_negation() -> None:
    score = score_sentiment("The food was not bad at all", "Positive")
    assert score.predicted_sentiment is Sentiment.POSITIVE


def test_sentiment_neutral() -> None:
    score = score_sentiment("The package arrived on Tuesday.", "Neutral")
    assert score.predicted_sentiment is Sentiment.NEUTRAL


def test_sentiment_mismatch() -> None:
    score = score_sentiment("This is terrible.", "Positive")
    assert score.deterministic_success is False


def test_constraint_all_satisfied() -> None:
    constraints = [
        Constraint("is_json", is_valid_json()),
        Constraint("mentions_price", contains_keyword("price")),
        Constraint("long_enough", field_min_length("response", 5)),
    ]
    raw = json.dumps({"response": "The total price is 20 dollars"})
    score = score_constraints(raw, constraints)
    assert score.deterministic_success is True
    assert score.satisfied_constraints == ["is_json", "mentions_price", "long_enough"]
    assert score.violated_constraints == []


def test_constraint_some_violated() -> None:
    constraints = [
        Constraint("is_json", is_valid_json()),
        Constraint("mentions_refund", contains_keyword("refund")),
    ]
    raw = json.dumps({"response": "Total cost 20"})
    score = score_constraints(raw, constraints)
    assert score.deterministic_success is False
    assert score.satisfied_constraints == ["is_json"]
    assert score.violated_constraints == ["mentions_refund"]


def test_score_scenario_dispatch_structured(valid_structured_response: str) -> None:
    scenario = Scenario(
        scenario_type=ScenarioType.STRUCTURED_DATA_EXTRACTION,
        expected=STRUCTURED_SCHEMA,
    )
    score = score_scenario(scenario, valid_structured_response)
    assert score.deterministic_success is True


def test_score_scenario_dispatch_sentiment() -> None:
    scenario = Scenario(
        scenario_type=ScenarioType.SENTIMENT,
        expected_sentiment="Positive",
    )
    score = score_scenario(scenario, "Amazing product!")
    assert score.deterministic_success is True


def test_score_scenario_dispatch_constraint() -> None:
    scenario = Scenario(
        scenario_type=ScenarioType.CONSTRAINT_SATISFACTION,
        constraints=[Constraint("is_json", is_valid_json())],
    )
    score = score_scenario(scenario, json.dumps({"a": 1}))
    assert score.deterministic_success is True