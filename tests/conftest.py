import os

# main.py reads these at import time; tests never reach AWS, so placeholder values are enough.
os.environ.setdefault("AWS_REGION", "eu-central-1")
os.environ.setdefault("AWS_DEFAULT_REGION", "eu-central-1")
os.environ.setdefault("AGENTCORE_GATEWAY_SUPPORT_GATEWAY_URL", "https://gateway.test/mcp")
# Memory stays off unless a test turns it on.
os.environ.pop("MEMORY_USERPREFERENCE_ID", None)
