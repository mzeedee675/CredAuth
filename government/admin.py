from django.contrib import admin
from .models import Business

@admin.register(Business)
class BusinessAdmin(admin.ModelAdmin):
    list_display = ('name', 'registration_number', 'contact_email', 'verified', 'registered_at')
    search_fields = ('name', 'registration_number', 'contact_email')
    list_filter = ('verified',)
    filter_horizontal = ('staff',)  # let admin assign staff users easily