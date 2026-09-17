from __future__ import annotations

"""Compatibility entry point for shared specialization effects."""

from specialization_modules import render_shared_effects as _render_shared_effects


def render_shared_effects() -> str:
    return _render_shared_effects()


__all__ = ["render_shared_effects"]
