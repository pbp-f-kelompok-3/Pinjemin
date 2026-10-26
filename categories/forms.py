from django import forms
from .models import Category


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name", "icon_url"]
        widgets = {
            "name": forms.TextInput(attrs={
                "placeholder": "Nama kategori",
            }),
            "icon_url": forms.URLInput(attrs={
                "placeholder": "URL icon",
            }),
        }
