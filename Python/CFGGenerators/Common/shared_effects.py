from __future__ import annotations

"""Compatibility entry point for shared and Unique-signature effects."""

from specialization_modules import render_shared_effects as _render_shared_effects
from unique_weapon_modules import render_unique_signature_effects


def render_shared_effects() -> str:
    shared = _render_shared_effects().rstrip()
    unique = render_unique_signature_effects().strip()
    return shared + "\n\n" + unique + "\n"


__all__ = ["render_shared_effects"]
