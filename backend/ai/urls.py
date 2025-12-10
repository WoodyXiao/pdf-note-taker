from django.urls import path

from . import views

urlpatterns = [
    path("answer/", views.answer, name="ai_answer"),
]


