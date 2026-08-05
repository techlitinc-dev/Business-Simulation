"""Prefixed, URL-safe id generation (bp_, bpv_, run_, evt_, ...)."""

import secrets


def new_prefixed_id(prefix: str) -> str:
    """Generate a prefixed id like ``bp_a1b2c3d4e5f6a7b8c9d0e1f2``."""
    return f"{prefix}_{secrets.token_hex(10)}"
