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

class Review(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    watch = models.ForeignKey(BaseWatch, on_delete=models.CASCADE, related_name='reviews')
    rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)])
    title = models.CharField(max_length=255, blank=True, null=True)  # New field
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'watch')

    def __str__(self):
        return f"{self.user.username}'s review of {self.watch.model_name}"

class ReviewImage(models.Model):
    review = models.ForeignKey('Review', related_name='images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='review_images/')