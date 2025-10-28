from django.contrib import admin
from .models import OwnerProfile, Institution, Certificate, VerificationRequest, AuditLog

@admin.register(OwnerProfile)
class OwnerProfileAdmin(admin.ModelAdmin):
    list_display = ('id_no', 'full_name', 'mobile', 'email', 'mobile_verified', 'created_at')
    search_fields = ('id_no', 'full_name', 'mobile', 'email')

    def mobile_verified(self, obj):
        """
        Placeholder boolean column for whether the owner's mobile has been verified.
        If you later add a real 'mobile_verified' field to OwnerProfile, remove this method
        and reference the model field instead.
        """
        # If you track verification elsewhere, replace this logic accordingly.
        # For now, return True if there's a mobile number present.
        return bool(obj.mobile)
    mobile_verified.boolean = True
    mobile_verified.short_description = 'Mobile verified'


@admin.register(Institution)
class InstitutionAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'contact_email', 'verified')
    filter_horizontal = ('staff',)


@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display = ('degree_name', 'owner_name', 'owner_id_no', 'institution', 'conferral_date')
    search_fields = ('owner_name', 'owner_id_no', 'degree_name')


@admin.register(VerificationRequest)
class VerificationRequestAdmin(admin.ModelAdmin):
    list_display = ('uuid', 'id_no', 'hr_user', 'hr_business', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('id_no', 'uuid')


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """
    Expose a read-only 'timestamp' column mapped to AuditLog.created_at.
    Using a method here avoids assuming the model has a 'timestamp' field.
    """
    readonly_fields = ('timestamp', 'action', 'user', 'details', 'created_at')
    list_display = ('timestamp', 'action', 'user', 'created_at')
    search_fields = ('action', 'details', 'user__username')

    def timestamp(self, obj):
        # Mirror created_at; format as a string if you'd prefer.
        return obj.created_at
    timestamp.admin_order_field = 'created_at'
    timestamp.short_description = 'Timestamp'