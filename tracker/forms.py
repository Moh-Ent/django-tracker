from django import forms
from django.utils import timezone

from .models import Project, Task


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ['name', 'description']


class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ['title', 'description', 'status', 'priority', 'due_date']
        widgets = {
            'due_date': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
        }

    def clean_due_date(self):
        due = self.cleaned_data.get('due_date')
        if due and not self.instance.pk and due < timezone.localdate():
            raise forms.ValidationError("Due date can't be in the past.")
        return due