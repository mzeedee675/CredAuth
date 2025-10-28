from django import forms
from .models import OwnerProfile, Certificate, VerificationRequest
from django.contrib.auth import get_user_model

from government.models import Business

class OwnerProfileForm(forms.ModelForm):
    class Meta:
        model = OwnerProfile
        fields = ['id_no', 'full_name', 'mobile', 'email']
        widgets = {
            'id_no': forms.TextInput(attrs={'placeholder': 'ID Number'}),
            'full_name': forms.TextInput(attrs={'placeholder': 'Full name'}),
            'mobile': forms.TextInput(attrs={'placeholder': '+2547...'}),
            'email': forms.EmailInput(attrs={'placeholder': 'owner@example.com'}),
        }


class CertificateForm(forms.ModelForm):
    class Meta:
        model = Certificate
        fields = ['institution', 'owner_id_no', 'owner_name', 'degree_name', 'program', 'conferral_date', 'certificate_reference']


class HRVerifyForm(forms.Form):
    id_no = forms.CharField(max_length=50, widget=forms.TextInput(attrs={'placeholder': 'Enter applicant ID number'}))
    # business will be set in __init__ to businesses the logged-in user belongs to
    business = forms.ModelChoiceField(queryset=Business.objects.none(), required=False, empty_label="Select business (if applicable)")

    def __init__(self, *args, **kwargs):
        # Accept `user` kwarg to restrict business choices
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user is not None:
            # limit to businesses where the user is staff
            self.fields['business'].queryset = Business.objects.filter(staff=user)
            # if user belongs to exactly one business, preselect it
            bs = self.fields['business'].queryset
            if bs.count() == 1:
                self.fields['business'].initial = bs.first()


class OTPConfirmForm(forms.Form):
    id_no = forms.CharField(max_length=50, widget=forms.TextInput(attrs={'placeholder': 'Your ID number'}))
    otp = forms.CharField(max_length=10, widget=forms.TextInput(attrs={'placeholder': 'Enter OTP received'}))