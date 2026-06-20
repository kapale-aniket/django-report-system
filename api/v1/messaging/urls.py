from django.urls import path

from api.v1.messaging import views as api_views

app_name = 'messaging_api'

urlpatterns = [
    path('inbox/', api_views.InboxAPIView.as_view(), name='inbox'),
    path('sent/', api_views.SentAPIView.as_view(), name='sent'),
    path('compose/', api_views.ComposeAPIView.as_view(), name='compose'),
    path('<int:message_id>/reply/', api_views.ReplyAPIView.as_view(), name='reply'),
    path('<int:message_id>/read/', api_views.MarkReadAPIView.as_view(), name='mark_read'),
]
