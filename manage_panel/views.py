from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.views.decorators.http import require_POST

from tracker.models import ActivityLog, Project, Task

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
    user_id = request.GET.get('user', '').strip()
    date_from = request.GET.get('date_from', '').strip()
    date_to = request.GET.get('date_to', '').strip()

    valid_actions = ActivityLog.Action.values

    # Validate the optional filters.
    if user_id and not user_id.isdigit():
        return HttpResponseBadRequest('Invalid user filter.')

    from_date = parse_date(date_from) if date_from else None
    to_date = parse_date(date_to) if date_to else None

    if date_from and from_date is None:
        return HttpResponseBadRequest('Invalid start date.')
    if date_to and to_date is None:
        return HttpResponseBadRequest('Invalid end date.')
    if from_date and to_date and from_date > to_date:
        return HttpResponseBadRequest(
            'Start date must be on or before end date.'
        )
    logs = ActivityLog.objects.select_related('user').all()

    if action in valid_actions:
        logs = logs.filter(action=action)

    if user_id:
        logs = logs.filter(user_id=user_id)

    if from_date:
        logs = logs.filter(created_at__date__gte=from_date)

    if to_date:
        logs = logs.filter(created_at__date__lte=to_date)

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

    users = User.objects.order_by('username')

    return render(request, 'manage_panel/activity.html', {
        'logs': page_obj.object_list,
        'page_obj': page_obj,
        'selected_action': action if action in valid_actions else '',
        'search_query': query,
        'action_choices': ActivityLog.Action.choices,
        'users': users,
        'selected_user': user_id,
        'date_from': date_from,
        'date_to': date_to,
        'filters': {
            'action': action,
            'user': user_id,
            'date_from': date_from,
            'date_to': date_to,
            'q': query,
        },
    })
