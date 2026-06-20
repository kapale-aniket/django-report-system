from django.urls import path

from api.v1.qa import views as api_views

app_name = 'qa_api'

urlpatterns = [
    path('faqs/', api_views.FAQListAPIView.as_view(), name='faq_list'),
    path('ask/', api_views.AskQuestionAPIView.as_view(), name='ask'),
    path('questions/', api_views.QuestionListAPIView.as_view(), name='question_list'),
    path('reply/<int:question_id>/', api_views.ReplyQuestionAPIView.as_view(), name='reply'),
    path('visitor-ask/', api_views.VisitorAskAPIView.as_view(), name='visitor_ask'),
    path(
        'visitor-reply/<int:question_id>/',
        api_views.VisitorReplyAPIView.as_view(),
        name='visitor_reply',
    ),
    path('suggest-reply/', api_views.SuggestReplyAPIView.as_view(), name='suggest_reply'),
]
