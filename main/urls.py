from django.urls import path
from .views import web_app_view
urlpatterns = [
    path("", web_app_view, name="menu_page"),
]
