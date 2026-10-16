from datetime import timedelta
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.contrib.auth import get_user_model
from django.shortcuts import render
from django.utils import timezone

from tracker.models import Project, Task, ActivityLog

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

@staff_required
def user_list(request):
    search_query = request.GET.get('q', '').strip()

    users = User.objects.annotate(
        project_count=Count('projects', distinct=True)
    ).order_by('username')

    if search_query:
        users = users.filter(
            Q(username__icontains=search_query)
            | Q(email__icontains=search_query)
        )
    paginator = Paginator(users, 20)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'manage_panel/users.html', {
        'users': page_obj.object_list,
        'page_obj': page_obj,
        'search_query': search_query,
    })


@staff_required
@require_POST
def toggle_user_active(request, user_id):
    target = get_object_or_404(User, pk=user_id)
    action = request.POST.get('action')

    if action not in ('activate', 'deactivate'):
        return HttpResponseBadRequest('Invalid action.')

    if action == 'deactivate' and target.pk == request.user.pk:
        messages.error(request, 'You cannot deactivate your own account.')
        return redirect('manage_users')

    target.is_active = action == 'activate'
    target.save(update_fields=['is_active'])

    messages.success(
        request,
        f"User '{target.username}' has been "
        f"{'activated' if target.is_active else 'deactivated'}.",
    )
    return redirect('manage_users')

@staff_required
def activity_list(request):
    action = request.GET.get('action', '').strip()
    query = request.GET.get('q', '').strip()

    logs = ActivityLog.objects.select_related('user').all()

    valid_actions = ActivityLog.Action.values
    if action in valid_actions:
        logs = logs.filter(action=action)

    if query:
        search_filter = (
            Q(user__username__icontains=query)
            | Q(target_type__icontains=query)
        )

        if query.isdigit():
            search_filter |= Q(target_id=int(query))

        logs = logs.filter(search_filter)

    paginator = Paginator(logs, 25)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'manage_panel/activity.html', {
        'logs': page_obj.object_list,
        'page_obj': page_obj,
        'selected_action': action if action in valid_actions else '',
        'search_query': query,
        'action_choices': ActivityLog.Action.choices,
    })