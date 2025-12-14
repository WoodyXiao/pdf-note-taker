from __future__ import annotations

from typing import Any, Optional

from django.contrib.auth import get_user_model

from .models import ActivityLog

User = get_user_model()


def log_activity(
    *,
    user: User,
    action_type: str,
    target: Optional[Any] = None,
    target_type: str = "",
    target_id: str = "",
    target_name: str = "",
    metadata: Optional[dict] = None,
) -> None:
    """
    Best-effort helper to record a user activity.

    - `target` is optional; when provided, we try to infer type/id/name from the model.
    - Failures are swallowed to avoid impacting primary flows.
    """
    if not user or not getattr(user, "id", None):
        return

    try:
        if target is not None:
            if not target_type:
                target_type = target.__class__.__name__
            if not target_id:
                # Prefer external ids like file_id when present.
                target_id = getattr(target, "file_id", None) or getattr(
                    target, "id", ""
                )
            if not target_name:
                target_name = getattr(target, "file_name", None) or getattr(
                    target, "name", ""
                )

        ActivityLog.objects.create(
            user=user,
            action_type=action_type,
            target_type=target_type or "",
            target_id=str(target_id) if target_id else "",
            target_name=target_name or "",
            metadata=metadata or {},
        )
    except Exception:
        # Logging must never break main flows; swallow any error.
        return



