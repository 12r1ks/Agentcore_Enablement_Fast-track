import re
from functools import lru_cache
from pathlib import Path

from .errors import ToolError, invalid_parameter

# Short topic names the model chooses from, mapped to the "## " section titles of the company document.
TOPICS = {
    "about": "About Lumora",
    "contact": "Contact and Support Hours",
    "order_statuses": "Order Statuses",
    "shipping": "Shipping and Delivery",
    "delays": "Common Reasons for Delays",
    "returns": "Returns Policy",
    "refunds": "Refund Policy",
    "warranty": "Warranty",
    "payment": "Payment Methods",
    "privacy": "Privacy and Data Handling",
    "escalation": "Escalation to a Human Agent",
    "faq": "Frequently Asked Questions",
}

_SECTION_PATTERN = re.compile(r"^## (.+?)\n(.*?)(?=^## |\Z)", flags=re.MULTILINE | re.DOTALL)


@lru_cache(maxsize=1)
def _sections() -> dict[str, str]:
    document = Path(__file__).with_name("lumora-company-info.md").read_text(encoding="utf-8")
    return {title.strip(): body.strip() for title, body in _SECTION_PATTERN.findall(document)}


def get_company_policy(args: dict) -> dict:
    """Tool: return one section of the company document. `args` are the arguments sent by the agent."""
    topic = args.get("topic")
    if not isinstance(topic, str):
        raise invalid_parameter("topic", "is required and must be a string")
    topic = topic.strip().lower()
    if topic not in TOPICS:
        raise invalid_parameter("topic", f"must be one of: {', '.join(sorted(TOPICS))}")
    title = TOPICS[topic]
    text = _sections().get(title)
    if text is None:
        raise ToolError("POLICY_SECTION_MISSING", f"Company document has no section '{title}'.")
    return {"topic": topic, "title": title, "text": text}
