from django import forms
# reuse CertificateForm from core if present; fallback local simplified form
try:
    from core.forms import CertificateForm as CoreCertificateForm
    CertificateForm = CoreCertificateForm
except Exception:
    from django.forms import ModelForm
    from core.models import Certificate
    class CertificateForm(ModelForm):
        class Meta:
            model = Certificate
            fields = ['institution', 'owner_id_no', 'owner_name', 'degree_name', 'program', 'conferral_date', 'certificate_reference']