from django.conf import settings
from django.db import models
from django.utils import timezone
import uuid

class OwnerProfile(models.Model):
    id_no = models.CharField(max_length=50, unique=True)
    full_name = models.CharField(max_length=255, blank=True)
    mobile = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.full_name or self.id_no} ({self.id_no})"


class Institution(models.Model):
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=64, unique=True)
    contact_email = models.EmailField(blank=True, null=True)
    staff = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name="institutions")
    verified = models.BooleanField(default=False)

    def __str__(self):
        return self.name


class Certificate(models.Model):
    institution = models.ForeignKey(Institution, related_name="certificates", on_delete=models.CASCADE)
    owner = models.ForeignKey(OwnerProfile, null=True, blank=True, on_delete=models.SET_NULL)
    owner_id_no = models.CharField(max_length=50, db_index=True)
    owner_name = models.CharField(max_length=255, blank=True)
    degree_name = models.CharField(max_length=255, blank=True)
    program = models.CharField(max_length=255, blank=True)
    conferral_date = models.DateField(null=True, blank=True)
    certificate_reference = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.degree_name} — {self.owner_name or self.owner_id_no}"


class AuditLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    action = models.CharField(max_length=200)
    details = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class VerificationRequest(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_CONFIRMED = 'confirmed'
    STATUS_EXPIRED = 'expired'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_CONFIRMED, 'Confirmed'),
        (STATUS_EXPIRED, 'Expired'),
    ]

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    hr_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    # hr_business points to the government.Business model (nullable if not used)
    hr_business = models.ForeignKey('government.Business', on_delete=models.SET_NULL, null=True, blank=True, related_name='verification_requests')
    id_no = models.CharField(max_length=50, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    otp = models.CharField(max_length=10)
    otp_expires_at = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    viewed_at = models.DateTimeField(null=True, blank=True)
    note = models.TextField(blank=True)

    def is_expired(self):
        return timezone.now() > self.otp_expires_at

    def mark_confirmed(self):
        self.status = self.STATUS_CONFIRMED
        self.confirmed_at = timezone.now()
        self.save()

    def __str__(self):
        return f"VR {self.uuid} for {self.id_no} ({self.status})"