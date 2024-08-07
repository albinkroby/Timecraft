from django.core.files.storage import FileSystemStorage
from django.utils.deconstruct import deconstructible
import os
# from .models import WatchImage

# @deconstructible
# class WatchImageStorage(FileSystemStorage):

#     def get_available_name(self, name, max_length=None):
#         base, ext = os.path.splitext(name)
#         counter = 1
#         while self.exists(name):
#             name = f"{base}_{counter}{ext}"
#             counter += 1
#         return name

#     def generate_filename(self, base_watch, filename):
#         base, ext = os.path.splitext(filename)
#         base_watch_slug = base_watch.slug
#         existing_images = WatchImage.objects.filter(base_watch=base_watch).count()
#         return f"{base_watch_slug}_{existing_images + 1}{ext}"
