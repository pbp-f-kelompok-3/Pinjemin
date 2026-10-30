from django.contrib import admin

from .models import HelpCenterSetting


@admin.register(HelpCenterSetting)
class HelpCenterSettingAdmin(admin.ModelAdmin):
    list_display = ("__str__", "whatsapp_number", "is_active")

    def has_add_permission(self, request):
        # Singleton: cukup satu baris.
        return not HelpCenterSetting.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False