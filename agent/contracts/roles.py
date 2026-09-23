"""The closed role vocabulary (C1).

Exactly two values. No `admin`, no `public`, no `guest`.

A run whose `context.role` is missing or not in ROLES is rejected before the
first model call — it does NOT silently downgrade to a least-privilege
surface. A silent downgrade is the wrong lesson to teach from a stage: if a
caller does not declare a role, the honest behaviour is to refuse, and the
refusal is visible in the trace. The UI always sets a role (C5), so this path
only fires for a raw client, which is exactly when it should.
"""

from __future__ import annotations

from typing import Literal, get_args

Role = Literal["engineer", "employee"]

#: The two valid role strings. This module is the only place they are literals.
ROLES: tuple[str, ...] = get_args(Role)
