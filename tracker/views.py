from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .activity import log_action
from .forms import CommentForm, ProjectForm, TaskForm
from .models import ActivityLog, Comment, Project, Task
from .utils import count_by_status, days_until_due, is_overdue

def home(request):
    return render(request, 'home.html')

def home(request):
    return render(request, 'home.html')


@login_required
def project_list(request):
    query = request.GET.get('q', '').strip()
    projects = Project.objects.filter(owner=request.user).annotate(
        task_count=Count('tasks'),
        done_count=Count('tasks', filter=Q(tasks__status=Task.Status.DONE)),
    ).order_by('-created_at', '-pk')
    if query:
        projects = projects.filter(
            Q(name__icontains=query) | Q(description__icontains=query)
        )
    page_obj = Paginator(projects, 10).get_page(request.GET.get('page'))
    return render(request, 'tracker/project_list.html', {
        'page_obj': page_obj,
        'query': query,
    })

@login_required
def project_detail(request, pk):
    project = get_object_or_404(Project, pk=pk, owner=request.user)
    tasks = project.tasks.all()

    status = request.GET.get('status', '')
    priority = request.GET.get('priority', '')
    query = request.GET.get('q', '').strip()

    if status in Task.Status.values:
        tasks = tasks.filter(status=status)
    if priority in Task.Priority.values:
        tasks = tasks.filter(priority=priority)
    if query:
        tasks = tasks.filter(
            Q(title__icontains=query) | Q(description__icontains=query)
        )

    page_obj = Paginator(tasks, 10).get_page(request.GET.get('page'))

    return render(request, 'tracker/project_detail.html', {
        'project': project,
        'page_obj': page_obj,
        'filters': {'status': status, 'priority': priority, 'q': query},
    })

@login_required
def project_create(request):
    if request.method == 'POST':
        form = ProjectForm(request.POST)
        if form.is_valid():
            project = form.save(commit=False)
            project.owner = request.user
            project.save()
            log_action(request.user, ActivityLog.Action.CREATED, project)
            messages.success(request, 'Project created.')
            return redirect('project_detail', pk=project.pk)
    else:
        form = ProjectForm()
    return render(request, 'tracker/project_form.html', {'form': form})

@login_required
def project_update(request, pk):
    project = get_object_or_404(Project, pk=pk, owner=request.user)
    if request.method == 'POST':
        form = ProjectForm(request.POST, instance=project)
        if form.is_valid():
            form.save()
            log_action(request.user, ActivityLog.Action.UPDATED, project)
            messages.success(request, 'Project updated.')
            return redirect('project_detail', pk=project.pk)
    else:
        form = ProjectForm(instance=project)
    return render(request, 'tracker/project_form.html', {'form': form})


@login_required
def project_delete(request, pk):
    project = get_object_or_404(Project, pk=pk, owner=request.user)
    if request.method == 'POST':
        log_action(request.user, ActivityLog.Action.DELETED, project)
        project.delete()
        messages.success(request, 'Project deleted.')
        return redirect('project_list')
    return render(request, 'tracker/project_confirm_delete.html', {'project': project})

@login_required
def task_create(request, project_pk):
    project = get_object_or_404(Project, pk=project_pk, owner=request.user)
    if request.method == 'POST':
        form = TaskForm(request.POST)
        if form.is_valid():
            task = form.save(commit=False)
            task.project = project
            task.save()
            log_action(request.user, ActivityLog.Action.CREATED, task)
            messages.success(request, 'Task created.')
            return redirect('project_detail', pk=project.pk)
    else:
        form = TaskForm()
    return render(request, 'tracker/task_form.html', {'form': form, 'project': project})

@login_required
def task_update(request, pk):
    task = get_object_or_404(Task, pk=pk, project__owner=request.user)
    if request.method == 'POST':
        form = TaskForm(request.POST, instance=task)
        if form.is_valid():
            form.save()
            log_action(request.user, ActivityLog.Action.UPDATED, task)
            messages.success(request, 'Task updated.')
            return redirect('project_detail', pk=task.project.pk)
    else:
        form = TaskForm(instance=task)
    return render(request, 'tracker/task_form.html', {'form': form, 'project': task.project})


@login_required
def task_delete(request, pk):
    task = get_object_or_404(Task, pk=pk, project__owner=request.user)
    project_pk = task.project.pk
    if request.method == 'POST':
        log_action(request.user, ActivityLog.Action.DELETED, task)
        task.delete()
        messages.success(request, 'Task deleted.')
        return redirect('project_detail', pk=project_pk)
    return render(request, 'tracker/task_confirm_delete.html', {'task': task})

NEXT_STATUS = {
    Task.Status.TODO: Task.Status.DOING,
    Task.Status.DOING: Task.Status.DONE,
}

@login_required
@require_POST
def task_advance(request, pk):
    task = get_object_or_404(Task, pk=pk, project__owner=request.user)
    new_status = NEXT_STATUS.get(task.status)
    if new_status:
        task.status = new_status
        task.save(update_fields=['status'])
        log_action(request.user, ActivityLog.Action.UPDATED, task)
        messages.success(request, f'Task moved to {task.get_status_display()}.')
    return redirect('project_detail', pk=task.project.pk)

@login_required
def task_detail(request, pk):
    task = get_object_or_404(Task, pk=pk, project__owner=request.user)
    if request.method == 'POST':
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.task = task
            comment.author = request.user
            comment.save()
            messages.success(request, 'Comment added.')
            return redirect('task_detail', pk=task.pk)
    else:
        form = CommentForm()
    return render(request, 'tracker/task_detail.html', {
        'task': task,
        'comments': task.comments.select_related('author'),
        'comment_form': form,
    })


@login_required
@require_POST
def comment_delete(request, pk):
    comment = get_object_or_404(Comment, pk=pk, author=request.user)
    task_pk = comment.task.pk
    comment.delete()
    messages.success(request, 'Comment deleted.')
    return redirect('task_detail', pk=task_pk)

@login_required
def dashboard(request):
    today = timezone.localdate()
    tasks = Task.objects.filter(project__owner=request.user).select_related('project')

    status_counts = count_by_status(tasks.values_list('status', flat=True))

    open_dated = (
        tasks.exclude(status=Task.Status.DONE)
        .exclude(due_date=None)
        .order_by('due_date')
    )
    overdue_tasks = [
        t for t in open_dated if is_overdue(t.due_date, t.status, today)
    ]
    due_this_week = [
        t for t in open_dated if 0 <= days_until_due(t.due_date, today) <= 7
    ]

    return render(request, 'tracker/dashboard.html', {
        'status_counts': status_counts,
        'overdue_tasks': overdue_tasks,
        'due_this_week': due_this_week,
    })