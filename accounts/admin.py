from django.contrib import admin

from .models import Profile


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("full_name", "npm", "mode", "is_onboarded")
    search_fields = ("full_name", "npm", "user__username")