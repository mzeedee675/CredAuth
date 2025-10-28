from django.db import models
from django.conf import settings

class Business(models.Model):
    name = models.CharField(max_length=255)
    registration_number = models.CharField(max_length=100, unique=True)
    contact_email = models.EmailField(blank=True, null=True)
    address = models.TextField(blank=True)
    # New: staff users that can act on behalf of this business (HR users)
    staff = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name='businesses'
    )
    registered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='businesses_registered'
    )
    registered_at = models.DateTimeField(auto_now_add=True)
    verified = models.BooleanField(default=False)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='businesses_verified'
    )
    verified_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.name} ({self.registration_number})"