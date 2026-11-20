from django.urls import path

from . import views, api_views

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
    path("profil/aktivitas/", views.profile_activity, name="profile_activity"),
    path("pengguna/<int:pk>/", views.profile_public, name="profile_public"),
    path("nonaktifkan/", views.deactivate_account, name="deactivate"),
    path("api/sso/start/", api_views.sso_start, name="api_sso_start"),
    path("api/sso/callback/", api_views.sso_callback_landing, name="api_sso_callback"),
    path("api/sso/exchange/", api_views.sso_exchange, name="api_sso_exchange"),
    path("api/me/", api_views.me, name="api_me"),
]