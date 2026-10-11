from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("login/", views.login_page, name="login"),
    path("sso/login/", views.sso_login, name="sso_login"),
    path("sso/callback/", views.sso_callback, name="sso_callback"),
    path("logout/", views.logout_view, name="logout"),
    path("onboarding/", views.onboarding, name="onboarding"),
    path("profil/", views.profile_detail, name="profile"),
    path("profil/edit/", views.profile_edit, name="profile_edit"),
    path("mode/toggle/", views.toggle_mode, name="toggle_mode"),
]
