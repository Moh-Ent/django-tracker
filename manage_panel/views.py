from datetime import timedelta

from django.contrib.auth import get_user_model
from django.shortcuts import render
from django.utils import timezone

from tracker.models import Project, Task

from .decorators import staff_required

User = get_user_model()


@staff_required
def dashboard(request):
    today = timezone.localdate()
    week_ago = timezone.now() - timedelta(days=7)
    stats = {
        'total_users': User.objects.count(),
        'total_projects': Project.objects.count(),
        'total_tasks': Task.objects.count(),
        'overdue_tasks': Task.objects.exclude(status=Task.Status.DONE)
        .filter(due_date__lt=today)
        .count(),
        'new_signups_week': User.objects.filter(date_joined__gte=week_ago).count(),
    }
    return render(request, 'manage_panel/dashboard.html', {'stats': stats})