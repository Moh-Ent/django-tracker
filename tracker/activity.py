from .models import ActivityLog


def log_action(user, action, obj):
    return ActivityLog.objects.create(
        user=user,
        action=action,
        target_type=obj._meta.model_name,
        target_id=obj.pk,
    )