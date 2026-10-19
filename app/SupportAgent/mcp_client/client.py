import os

import botocore.session
import httpx
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from mcp.client.streamable_http import streamablehttp_client
from strands.tools.mcp.mcp_client import MCPClient

GATEWAY_URL = os.environ.get("AGENTCORE_GATEWAY_SUPPORT_GATEWAY_URL")
if not GATEWAY_URL:
    raise RuntimeError("AGENTCORE_GATEWAY_SUPPORT_GATEWAY_URL is not set. Is the gateway deployed?")


class _SigV4HttpxAuth(httpx.Auth):
    """Signs each request with SigV4, as required by a gateway with authorizerType AWS_IAM."""

    requires_request_body = True

    def __init__(self, region: str):
        self._session = botocore.session.Session()
        self._region = region

    def auth_flow(self, request: httpx.Request):
        # "connection" can be rewritten in transit, which would invalidate the signature
        headers = {k: v for k, v in request.headers.items() if k.lower() != "connection"}
        aws_request = AWSRequest(method=request.method, url=str(request.url), data=request.content, headers=headers)
        credentials = self._session.get_credentials().get_frozen_credentials()
        SigV4Auth(credentials, "bedrock-agentcore", self._region).add_auth(aws_request)
        request.headers.update(dict(aws_request.headers))
        yield request


def get_streamable_http_mcp_client() -> MCPClient:
    """Returns an MCP Client compatible with Strands"""
    region = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION", "eu-central-1")
    return MCPClient(lambda: streamablehttp_client(GATEWAY_URL, auth=_SigV4HttpxAuth(region)))
