import pytest

from support_tools.company_info import TOPICS, get_company_policy
from support_tools.errors import ToolError


def error_code(args) -> str:
    with pytest.raises(ToolError) as raised:
        get_company_policy(args)
    return raised.value.code


@pytest.mark.parametrize("topic", sorted(TOPICS))
def test_every_topic_maps_to_a_section(topic):
    section = get_company_policy({"topic": topic})
    assert section["title"] == TOPICS[topic]
    assert section["text"]


def test_refund_policy_mentions_limit():
    assert "1,000 EUR" in get_company_policy({"topic": "refunds"})["text"]


def test_topic_is_case_and_whitespace_insensitive():
    assert get_company_policy({"topic": "  Warranty "})["topic"] == "warranty"


def test_unknown_topic_lists_valid_topics():
    with pytest.raises(ToolError) as raised:
        get_company_policy({"topic": "pricing"})
    assert raised.value.code == "INVALID_PARAMETER"
    assert "returns" in raised.value.message


@pytest.mark.parametrize("args", [{}, {"topic": None}, {"topic": 5}])
def test_missing_or_non_string_topic(args):
    assert error_code(args) == "INVALID_PARAMETER"
