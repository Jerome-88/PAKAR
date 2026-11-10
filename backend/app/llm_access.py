"""Optional endpoint lock, shared by the API and isolated inference workers."""
import os
from urllib.parse import urlsplit


def require_allowed_llm_endpoint(base_url):
    allowed = {host.strip().lower() for host in os.getenv("PAKAR_ALLOWED_LLM_HOSTS", "").split(",") if host.strip()}
    if not allowed:
        return
    endpoint = urlsplit(base_url or "")
    if (endpoint.scheme != "https" or endpoint.hostname not in allowed
            or endpoint.username or endpoint.password or endpoint.port not in (None, 443)):
        raise ValueError("LLM endpoint blocked by PAKAR_ALLOWED_LLM_HOSTS")
