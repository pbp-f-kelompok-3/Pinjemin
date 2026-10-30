from django.views.generic import TemplateView

from .models import HelpCenterSetting


class HelpCenterView(TemplateView):
    template_name = "help_center/help.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["wa_link"] = HelpCenterSetting.load().whatsapp_url
        return context