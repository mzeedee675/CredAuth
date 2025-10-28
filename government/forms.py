from django import forms
from .models import Business
from core.models import Institution

class BusinessForm(forms.ModelForm):
    class Meta:
        model = Business
        fields = ['name', 'registration_number', 'contact_email', 'address']

class InstitutionCreateForm(forms.ModelForm):
    """
    Form for government users to create Institutions (uses the core.Institution model).
    """
    class Meta:
        model = Institution
        fields = ['name', 'code', 'contact_email']