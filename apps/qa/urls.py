from django.urls import path

from . import views

app_name = 'qa'

urlpatterns = [
    path('', views.qa_home, name='home'),
    path('reply/<int:pk>/', views.qa_reply, name='reply'),
    path('visitor-reply/<int:pk>/', views.visitor_reply, name='visitor_reply'),
]
