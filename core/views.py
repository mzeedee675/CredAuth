"""
Consolidated core views: dashboard/home, owner flows, HR flows, and institution certificate
management. This file is a single, self-contained replacement for the existing core/views.py.

Notes:
- Keeps send_otp_to_owner helper (console/email).
- Tries to import government.Business optionally so the app can run before/after government app added.
- HR flows support hr_business on VerificationRequest and restrict business selection/actions to staff.
- Institution views render templates from the institution app (institution/...).
- Dashboard/home collects role flags and quick lists for display.
"""
from datetime import timedelta
import random

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.mail import send_mail
from django.db.models import Count
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import (
    CertificateForm,
    HRVerifyForm,
    OTPConfirmForm,
    OwnerProfileForm,
)
from .models import (
    AuditLog,
    Certificate,
    Institution,
    OwnerProfile,
    VerificationRequest,
)

# optional import — government app may be absent in some setups
try:
    from government.models import Business
except Exception:
    Business = None


# -------------------------
# Helper: send OTP (dev)
# -------------------------
def send_otp_to_owner(owner: OwnerProfile, otp: str, request_obj: VerificationRequest):
    """
    Send OTP to owner. For development we use Django console/email backend.
    """
    subject = "OTP for verification request"
    message = (
        f"Hello {owner.full_name or owner.id_no},\n\n"
        f"An organization requested to view your academic credentials.\n"
        f"OTP: {otp}\n"
        f"This OTP expires at {request_obj.otp_expires_at}.\n\n"
        "If you didn't request this, contact system admin."
    )
    recipient = [owner.email] if getattr(owner, "email", None) else []
    if recipient:
        send_mail(subject, message, getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@example.com"), recipient)
    # Always print to console for development/demo
    print("DEBUG OTP SEND:", message)


# -------------------------
# Dashboard / Home
# -------------------------
def _user_roles(user):
    """
    Return a dict of boolean flags for roles: government, institution_staff, business_hr, owner, admin
    based on group membership and superuser flag.
    """
    roles = {
        "is_government": False,
        "is_institution_staff": False,
        "is_business_hr": False,
        "is_owner": False,
        "is_admin": user.is_superuser,
    }
    if user.is_anonymous:
        return roles

    user_groups = set(g.name for g in user.groups.all())
    roles["is_government"] = user.is_superuser or ("government" in user_groups)
    roles["is_institution_staff"] = user.is_superuser or ("institution_staff" in user_groups)
    roles["is_business_hr"] = user.is_superuser or ("business_hr" in user_groups)
    roles["is_owner"] = user.is_superuser or ("owner" in user_groups)
    return roles


def home(request):
    """
    Dashboard landing page — shows overview for all stakeholders.
    If the user is authenticated, show role-specific quick actions.
    """
    inst_count = Institution.objects.count()
    owner_count = OwnerProfile.objects.count()
    vr_pending = VerificationRequest.objects.filter(status=VerificationRequest.STATUS_PENDING).count()
    vr_confirmed = VerificationRequest.objects.filter(status=VerificationRequest.STATUS_CONFIRMED).count()
    business_count = Business.objects.count() if Business is not None else 0

    context = {
        "inst_count": inst_count,
        "owner_count": owner_count,
        "business_count": business_count,
        "vr_pending": vr_pending,
        "vr_confirmed": vr_confirmed,
    }
    context.update(_user_roles(request.user))

    if context.get("is_government"):
        context["recent_institutions"] = Institution.objects.order_by("-id")[:5]
        if Business is not None:
            context["recent_businesses"] = Business.objects.order_by("-registered_at")[:5]

    if context.get("is_institution_staff") and not request.user.is_superuser:
        try:
            context["user_institutions"] = Institution.objects.filter(staff=request.user)
        except Exception:
            context["user_institutions"] = Institution.objects.none()

    if context.get("is_business_hr") and Business is not None:
        try:
            context["user_businesses"] = Business.objects.filter(staff=request.user)
        except Exception:
            context["user_businesses"] = Business.objects.none()

    return render(request, "core/dashboard.html", context)


# -------------------------
# Owner flows
# -------------------------
def owner_profile(request):
    """
    Create / update owner profile (id_no, full_name, mobile, email)
    """
    if request.method == "POST":
        form = OwnerProfileForm(request.POST)
        if form.is_valid():
            id_no = form.cleaned_data["id_no"]
            profile, created = OwnerProfile.objects.update_or_create(
                id_no=id_no,
                defaults={
                    "full_name": form.cleaned_data.get("full_name"),
                    "mobile": form.cleaned_data.get("mobile"),
                    "email": form.cleaned_data.get("email"),
                },
            )
            messages.success(
                request,
                "Profile saved. If this is your mobile/email, you will receive OTPs when verification is requested.",
            )
            return redirect("core:owner_profile")
    else:
        form = OwnerProfileForm()
    return render(request, "core/owner_profile.html", {"form": form})


def owner_confirm_otp(request):
    """
    Owner supplies ID and OTP to confirm a pending verification request.
    """
    if request.method == "POST":
        form = OTPConfirmForm(request.POST)
        if form.is_valid():
            id_no = form.cleaned_data["id_no"]
            otp = form.cleaned_data["otp"]
            qs = VerificationRequest.objects.filter(
                id_no=id_no, otp=otp, status=VerificationRequest.STATUS_PENDING
            ).order_by("-created_at")
            if not qs.exists():
                messages.error(request, "No matching pending verification request found or OTP invalid/expired.")
                return render(request, "core/owner_confirm.html", {"form": form})
            vr = qs.first()
            if vr.is_expired():
                vr.status = VerificationRequest.STATUS_EXPIRED
                vr.save()
                messages.error(request, "OTP has expired.")
                return render(request, "core/owner_confirm.html", {"form": form})
            vr.mark_confirmed()
            AuditLog.objects.create(user=None, action="owner_confirmed", details=f"Owner {id_no} confirmed request {vr.uuid}")
            messages.success(request, "OTP accepted. HR may now view your records for that request.")
            return redirect("core:owner_confirm_otp")
    else:
        form = OTPConfirmForm()
    return render(request, "core/owner_confirm.html", {"form": form})


# -------------------------
# HR flows
# -------------------------
@login_required
def hr_verify(request):
    """
    HR requests verification by entering applicant ID.
    If Business model exists, form shows allowed business choices for the logged-in user.
    """
    if request.method == "POST":
        form = HRVerifyForm(request.POST, user=request.user)
        if form.is_valid():
            id_no = form.cleaned_data["id_no"]
            business = form.cleaned_data.get("business") if "business" in form.cleaned_data else None

            # enforce staff membership for selected business
            if business and not (request.user.is_superuser or (Business is not None and business.staff.filter(pk=request.user.pk).exists())):
                messages.error(request, "You are not authorized to act on behalf of that business.")
                return render(request, "core/hr_verify.html", {"form": form})

            try:
                owner = OwnerProfile.objects.get(id_no=id_no)
            except OwnerProfile.DoesNotExist:
                messages.error(request, "No owner profile found for that ID. Ask the applicant to register first.")
                return render(request, "core/hr_verify.html", {"form": form})

            otp = f"{random.randint(100000, 999999)}"
            expires = timezone.now() + timedelta(minutes=10)
            vr = VerificationRequest.objects.create(
                hr_user=request.user,
                hr_business=business if Business is not None else None,
                id_no=id_no,
                otp=otp,
                otp_expires_at=expires,
            )

            # send OTP
            try:
                send_otp_to_owner(owner, otp, vr)
            except Exception:
                # fallback: print to console
                print(f"DEBUG OTP: {otp} for ID {id_no} expires at {expires}")

            AuditLog.objects.create(user=request.user, action="requested_verification", details=f"Requested verification for {id_no} on behalf of {business}")
            messages.success(request, f"OTP sent to owner (if owner has registered email). Request ID: {vr.uuid}")
            return redirect("core:hr_request_status", uuid=vr.uuid)
    else:
        form = HRVerifyForm(user=request.user)

    # Show info if user isn't staff of any business and not superuser
    if Business is not None:
        user_businesses = Business.objects.filter(staff=request.user)
        if not request.user.is_superuser and not user_businesses.exists():
            messages.info(request, "You are not assigned as staff to any business. You may still request verifications but cannot act on behalf of a business until assigned.")
    return render(request, "core/hr_verify.html", {"form": form})


@login_required
def hr_request_list(request):
    """
    List verification requests created by the logged-in HR.
    Superuser sees all. Optionally expand visibility to staff of same business.
    """
    if request.user.is_superuser:
        qs = VerificationRequest.objects.order_by("-created_at")
    else:
        # requests created by the user OR requests for businesses the user belongs to
        qs = VerificationRequest.objects.filter(hr_user=request.user).order_by("-created_at")
        if Business is not None:
            # include requests for any business where user is staff
            business_pks = Business.objects.filter(staff=request.user).values_list("pk", flat=True)
            qs = VerificationRequest.objects.filter(hr_user=request.user) | VerificationRequest.objects.filter(hr_business__in=business_pks)
            qs = qs.order_by("-created_at")

    # update pending -> expired if needed
    for v in qs:
        if v.status == VerificationRequest.STATUS_PENDING and v.is_expired():
            v.status = VerificationRequest.STATUS_EXPIRED
            v.save()

    return render(request, "core/hr_request_list.html", {"requests": qs, "now": timezone.now()})


@login_required
def hr_request_status(request, uuid):
    vr = get_object_or_404(VerificationRequest, uuid=uuid)
    if vr.status == VerificationRequest.STATUS_PENDING and vr.is_expired():
        vr.status = VerificationRequest.STATUS_EXPIRED
        vr.save()
    return render(request, "core/hr_request_status.html", {"vr": vr})


@login_required
def hr_view_request(request, uuid):
    """
    HR views the details of a verification request; allow the requesting HR, superusers,
    or staff users from the same business to view.
    If confirmed, show certificates.
    """
    vr = get_object_or_404(VerificationRequest, uuid=uuid)

    allowed = False
    if request.user.is_superuser:
        allowed = True
    if vr.hr_user and vr.hr_user.pk == request.user.pk:
        allowed = True
    if Business is not None and vr.hr_business is not None:
        if vr.hr_business.staff.filter(pk=request.user.pk).exists():
            allowed = True

    if not allowed:
        return HttpResponseForbidden("You are not authorized to view this verification request.")

    can_view = (vr.status == VerificationRequest.STATUS_CONFIRMED) and (not vr.is_expired())
    certificates = []
    if can_view:
        certificates = Certificate.objects.filter(owner_id_no=vr.id_no)
        vr.viewed_at = timezone.now()
        vr.save()
        AuditLog.objects.create(user=request.user, action="hr_viewed", details=f"HR viewed records for {vr.id_no} (request {vr.uuid})")

    # render institution HR view template (keeps institution templates grouped)
    return render(request, "institution/hr_view_owner.html", {"vr": vr, "can_view": can_view, "certificates": certificates})


# -------------------------
# Institution certificate management
# -------------------------
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
    certs = inst.certificates.order_by("-created_at")
    return render(request, "institution/institution_cert_list.html", {"institution": inst, "certificates": certs})


@login_required
def institution_cert_create(request, inst_id):
    inst = get_object_or_404(Institution, pk=inst_id)
    if not _user_is_institution_staff(request.user, inst):
        return HttpResponseForbidden("You are not authorized to manage this institution.")
    if request.method == "POST":
        form = CertificateForm(request.POST)
        if form.is_valid():
            cert = form.save(commit=False)
            cert.institution = inst
            try:
                owner = OwnerProfile.objects.get(id_no=cert.owner_id_no)
                cert.owner = owner
            except OwnerProfile.DoesNotExist:
                cert.owner = None
            cert.save()
            AuditLog.objects.create(user=request.user, action="certificate_added", details=f"Added certificate {cert.pk} for institution {inst.pk}")
            messages.success(request, "Certificate added.")
            return redirect("core:institution_cert_list", inst_id=inst.pk)
    else:
        form = CertificateForm()
    return render(request, "institution/institution_cert_form.html", {"form": form, "institution": inst, "creating": True})


@login_required
def institution_cert_edit(request, inst_id, pk):
    inst = get_object_or_404(Institution, pk=inst_id)
    if not _user_is_institution_staff(request.user, inst):
        return HttpResponseForbidden("You are not authorized to manage this institution.")
    cert = get_object_or_404(Certificate, pk=pk, institution=inst)
    if request.method == "POST":
        form = CertificateForm(request.POST, instance=cert)
        if form.is_valid():
            cert = form.save(commit=False)
            try:
                owner = OwnerProfile.objects.get(id_no=cert.owner_id_no)
                cert.owner = owner
            except OwnerProfile.DoesNotExist:
                cert.owner = None
            cert.save()
            AuditLog.objects.create(user=request.user, action="certificate_edited", details=f"Edited certificate {cert.pk} for institution {inst.pk}")
            messages.success(request, "Certificate updated.")
            return redirect("core:institution_cert_list", inst_id=inst.pk)
    else:
        form = CertificateForm(instance=cert)
    return render(request, "institution/institution_cert_form.html", {"form": form, "institution": inst, "creating": False, "cert": cert})


@login_required
def institution_cert_delete(request, inst_id, pk):
    inst = get_object_or_404(Institution, pk=inst_id)
    if not _user_is_institution_staff(request.user, inst):
        return HttpResponseForbidden("You are not authorized to manage this institution.")
    cert = get_object_or_404(Certificate, pk=pk, institution=inst)
    if request.method == "POST":
        cert_pk = cert.pk
        cert.delete()
        AuditLog.objects.create(user=request.user, action="certificate_deleted", details=f"Deleted certificate {cert_pk} for institution {inst.pk}")
        messages.success(request, "Certificate deleted.")
        return redirect("core:institution_cert_list", inst_id=inst.pk)
    return render(request, "institution/institution_cert_confirm_delete.html", {"cert": cert, "institution": inst})