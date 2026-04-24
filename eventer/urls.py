from django.urls import path

from eventer import views

urlpatterns = [
    path('', views.event_list, name='eventer-event-list'),
    path('<slug:event_slug>/', views.event_detail, name='eventer-event-detail'),
]
