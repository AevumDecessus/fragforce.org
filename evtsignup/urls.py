from django.urls import path

from evtsignup import views

urlpatterns = [
    path('<slug:event_slug>/', views.signup_view, name='evtsignup-signup'),
]
