from django.contrib import admin
from django.db.models import Count
from .models import Project, Task, Comment, ActivityLog


class TaskInline(admin.TabularInline):
    model = Task
    extra = 1
    fields = ('title', 'status', 'priority', 'due_date')


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'task_count', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('name', 'description', 'owner__username')
    readonly_fields = ('created_at',)
    inlines = [TaskInline]

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_task_count=Count('tasks'))

    @admin.display(description='Tasks', ordering='_task_count')
    def task_count(self, obj):
        return obj._task_count


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'project', 'status', 'priority', 'due_date')
    list_filter = ('status', 'priority', 'due_date')
    search_fields = ('title', 'description', 'project__name')
    readonly_fields = ('created_at',)
    actions = ['mark_done']

    @admin.action(description='Mark selected tasks as done')
    def mark_done(self, request, queryset):
        updated = queryset.update(status=Task.Status.DONE)
        self.message_user(request, f'{updated} task(s) marked as done.')

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('task', 'author', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('body', 'author__username')
    readonly_fields = ('created_at',)


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'action', 'target_type', 'target_id', 'created_at')
    list_filter = ('action', 'target_type')
    search_fields = ('user__username', 'target_type')
    readonly_fields = ('created_at',)

