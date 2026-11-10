"""Read compatibility for identities created before the PAKAR rename."""

LEGACY_SESSION_COOKIE = "rk_session"
LEGACY_OASIS_RUNTIME_ENV = "REKAKEBIJAKAN_OASIS_RUNTIME_PATH"


def session_cookie_names(configured_name: str) -> tuple[str, ...]:
    # Explicit custom namespaces remain isolated from the standard application.
    if configured_name == "pakar_session":
        return (configured_name, LEGACY_SESSION_COOKIE)
    return (configured_name,)
