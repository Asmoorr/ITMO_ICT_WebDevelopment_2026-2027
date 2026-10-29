from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    organization = models.CharField("Организация", max_length=160, blank=True)

    def __str__(self) -> str:
        return self.get_full_name() or self.username
