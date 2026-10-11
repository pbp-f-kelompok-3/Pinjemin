from django.urls import path
from django.views.generic import TemplateView

app_name = "help_center"

urlpatterns = [
    path("bantuan/", TemplateView.as_view(template_name="help_center/help.html"), name="help"),
    path("tutorial/meminjam/", TemplateView.as_view(template_name="help_center/tutorial_borrow.html"), name="tutorial_borrow"),
    path("tutorial/menyewakan/", TemplateView.as_view(template_name="help_center/tutorial_lend.html"), name="tutorial_lend"),
    path("kebijakan-privasi/", TemplateView.as_view(template_name="help_center/privacy.html"), name="privacy"),
]
