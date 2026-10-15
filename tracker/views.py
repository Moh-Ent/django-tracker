from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, render
from django.contrib.auth.decorators import login_required

from .models import Project


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