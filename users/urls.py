from django.urls import path

from users.apps import UsersConfig
from users.views import login_view, logout_view

app_name = UsersConfig.name

urlpatterns = [
    # Django template views
    path("login/", login_view, name="login"),
    path("logout/", logout_view, name="logout"),
]
