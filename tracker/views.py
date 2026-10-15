from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, render
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import redirect
from .activity import log_action
from .forms import ProjectForm, TaskForm
from .models import ActivityLog, Project, Task



def home(request):
    return render(request, 'home.html')

@login_required
def project_list(request):
    projects = Project.objects.filter(owner=request.user)
    page_obj = Paginator(projects, 10).get_page(request.GET.get('page'))
    return render(request, 'tracker/project_list.html', {'page_obj': page_obj})

@login_required
def project_detail(request, pk):
    project = get_object_or_404(Project, pk=pk, owner=request.user)
    return render(request, 'tracker/project_detail.html', {'project': project})

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