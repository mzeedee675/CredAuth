from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import HttpResponseForbidden
from django.contrib.auth.decorators import login_required
from django.utils import timezone

from core.models import Institution, Certificate, OwnerProfile, VerificationRequest, AuditLog
from .forms import CertificateForm

# Helper: is user staff for institution
def _user_is_institution_staff(user, institution):
    if user.is_superuser:
        return True
    try:
        return institution.staff.filter(pk=user.pk).exists()
    except Exception:
        return False


@login_required
def institution_cert_list(request, inst_id):
    inst = get_object_or_404(Institution, pk=inst_id)
    if not _user_is_institution_staff(request.user, inst):
        return HttpResponseForbidden("You are not authorized to manage this institution.")
    certs = inst.certificates.order_by('-created_at')
    return render(request, 'institution/institution_cert_list.html', {'institution': inst, 'certificates': certs})


@login_required
def institution_cert_create(request, inst_id):
    inst = get_object_or_404(Institution, pk=inst_id)
    if not _user_is_institution_staff(request.user, inst):
        return HttpResponseForbidden("You are not authorized to manage this institution.")
    if request.method == 'POST':
        form = CertificateForm(request.POST)
        if form.is_valid():
            cert = form.save(commit=False)
            cert.institution = inst
            # link owner profile when available
            try:
                owner = OwnerProfile.objects.get(id_no=cert.owner_id_no)
                cert.owner = owner
            except OwnerProfile.DoesNotExist:
                cert.owner = None
            cert.save()
            AuditLog.objects.create(user=request.user, action='certificate_added', details=f"Added certificate {cert.pk} for institution {inst.pk}")
            messages.success(request, 'Certificate added.')
            return redirect('institution:cert_list', inst_id=inst.pk)
    else:
        form = CertificateForm(initial={'institution': inst.pk})
    return render(request, 'institution/institution_cert_form.html', {'form': form, 'institution': inst, 'creating': True})


@login_required
def institution_cert_edit(request, inst_id, pk):
    inst = get_object_or_404(Institution, pk=inst_id)
    if not _user_is_institution_staff(request.user, inst):
        return HttpResponseForbidden("You are not authorized to manage this institution.")
    cert = get_object_or_404(Certificate, pk=pk, institution=inst)
    if request.method == 'POST':
        form = CertificateForm(request.POST, instance=cert)
        if form.is_valid():
            cert = form.save(commit=False)
            try:
                owner = OwnerProfile.objects.get(id_no=cert.owner_id_no)
                cert.owner = owner
            except OwnerProfile.DoesNotExist:
                cert.owner = None
            cert.save()
            AuditLog.objects.create(user=request.user, action='certificate_edited', details=f"Edited certificate {cert.pk} for institution {inst.pk}")
            messages.success(request, 'Certificate updated.')
            return redirect('institution:cert_list', inst_id=inst.pk)
    else:
        form = CertificateForm(instance=cert)
    return render(request, 'institution/institution_cert_form.html', {'form': form, 'institution': inst, 'creating': False, 'cert': cert})


@login_required
def institution_cert_delete(request, inst_id, pk):
    inst = get_object_or_404(Institution, pk=inst_id)
    if not _user_is_institution_staff(request.user, inst):
        return HttpResponseForbidden("You are not authorized to manage this institution.")
    cert = get_object_or_404(Certificate, pk=pk, institution=inst)
    if request.method == 'POST':
        cert_pk = cert.pk
        cert.delete()
        AuditLog.objects.create(user=request.user, action='certificate_deleted', details=f"Deleted certificate {cert_pk} for institution {inst.pk}")
        messages.success(request, 'Certificate deleted.')
        return redirect('institution:cert_list', inst_id=inst.pk)
    return render(request, 'institution/institution_cert_confirm_delete.html', {'cert': cert, 'institution': inst})


@login_required
def hr_view_owner(request, uuid):
    """
    HR views owner's academic details for a given VerificationRequest UUID.
    Only the HR user who requested the verification or a superuser can view it.
    The VerificationRequest must be confirmed by the owner (status == confirmed).
    """
    vr = get_object_or_404(VerificationRequest, uuid=uuid)
    # only allow the requesting HR user (vr.hr_user) or superuser
    if not (request.user.is_superuser or (vr.hr_user and vr.hr_user.pk == request.user.pk)):
        return HttpResponseForbidden("You are not authorized to view this verification request.")

    can_view = vr.status == VerificationRequest.STATUS_CONFIRMED and not vr.is_expired()
    certificates = []
    if can_view:
        certificates = Certificate.objects.filter(owner_id_no=vr.id_no)
        # record viewed_at
        vr.viewed_at = timezone.now()
        vr.save()
        AuditLog.objects.create(user=request.user, action='hr_viewed', details=f"HR {request.user} viewed records for {vr.id_no} (request {vr.uuid})")

    return render(request, 'institution/hr_view_owner.html', {'vr': vr, 'can_view': can_view, 'certificates': certificates})