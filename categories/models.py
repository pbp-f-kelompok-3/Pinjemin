from django.db import models

# Create your models here.

from django.db import models


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    icon_url = models.URLField(max_length=500, blank=True, null=True)

    def __str__(self):
        return self.name
