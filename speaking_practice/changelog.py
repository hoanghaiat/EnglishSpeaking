"""Explicit, human-readable change history for management actions.

Every management view calls log_change() with a specific summary — never a
generic message. Visibility is enforced by changelog_for().
"""
from django.db.models import Q

from .models import ChangeLog, StudentProfile


def log_change(actor, category, action, summary, target_user=None,
               related_teacher=None, related_student=None):
    """Write one changelog entry. Returns the entry."""
    return ChangeLog.objects.create(
        actor=actor,
        category=category,
        action=action,
        summary=summary,
        target_user=target_user,
        related_teacher=related_teacher,
        related_student=related_student,
    )


def changelog_for(user, limit=None):
    """Entries visible to ``user``.

    - admin: everything.
    - teacher: own entries + admin entries related to them
      (their classes/students).
    - other roles: nothing.
    """
    qs = ChangeLog.objects.select_related(
        'actor', 'target_user').order_by('-created_at')
    if user.role == 'admin':
        pass
    elif user.role == 'teacher':
        profile = getattr(user, 'teacher_profile', None)
        if profile is None:
            return ChangeLog.objects.none()
        own_students = StudentProfile.objects.filter(
            assigned_teachers__teacher=profile)
        qs = qs.filter(
            Q(actor=user)
            | (Q(actor__role='admin')
               & (Q(related_teacher=profile)
                  | Q(related_student__in=own_students)))
        ).distinct()
    else:
        return ChangeLog.objects.none()
    if limit is not None:
        qs = qs[:limit]
    return qs
