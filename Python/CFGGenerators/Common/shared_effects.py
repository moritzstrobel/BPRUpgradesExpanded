from __future__ import annotations

"""Compatibility entry point for shared specialization effects.

The implementation lives in specialization_modules.py; generate_all_cfg imports
this small module so the unified generator has a stable API.
"""

from specialization_modules import render_shared_effects

__all__ = ["render_shared_effects"]
