from django.db import models
from django.contrib.auth import get_user_model
from adminapp.models import BaseWatch

# Create your models here.
User = get_user_model()

class Wishlist(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    watches = models.ManyToManyField(BaseWatch)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s Wishlist"