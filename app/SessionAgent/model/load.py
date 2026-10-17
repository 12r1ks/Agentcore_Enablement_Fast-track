import os

from aws_bedrock_token_generator import provide_token
from strands.models.openai import OpenAIModel

MODEL_ID = "google.gemma-4-26b-a4b"


def load_model() -> OpenAIModel:
    """Get a Bedrock Mantle model client.

    Gemma 4 is served via the Bedrock Mantle endpoint, NOT the Converse API, so it is invoked
    through an OpenAI-style client authenticated with a short-lived Bedrock bearer token.
    Region is read from AWS_REGION (set by the AgentCore runtime).
    """
    region = os.environ.get("AWS_REGION", os.environ.get("AWS_DEFAULT_REGION", "eu-central-1"))
    token = provide_token(region=region)
    client_args = {"api_key": token, "base_url": f"https://bedrock-mantle.{region}.api.aws/openai/v1"}
    return OpenAIModel(client_args=client_args, model_id=MODEL_ID, params={})
