from django.urls import path

from . import views

urlpatterns = [
    path('', views.dashboard, name='manage_dashboard'),
    path('users/', views.user_list, name='manage_users'),
    path('users/<int:user_id>/active/', views.toggle_user_active, name='manage_user_toggle'),
]