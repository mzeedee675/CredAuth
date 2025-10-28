from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.contrib.auth.decorators import login_required, user_passes_test
from .models import Business
from .forms import BusinessForm, InstitutionCreateForm
from core.models import Institution, AuditLog

def is_government_user(user):
    """
    Government users are either superusers or belong to the 'government' group.
    """
    if user.is_superuser:
        return True
    return user.groups.filter(name='government').exists()

gov_required = user_passes_test(is_government_user)


@login_required
@gov_required
def gov_dashboard(request):
    inst_count = Institution.objects.count()
    pending_insts = Institution.objects.filter(verified=False).count()
    businesses = Business.objects.count()
    pending_businesses = Business.objects.filter(verified=False).count()
    return render(request, 'government/dashboard.html', {
        'inst_count': inst_count,
        'pending_insts': pending_insts,
        'businesses': businesses,
        'pending_businesses': pending_businesses,
    })


@login_required
@gov_required
def institution_list(request):
    insts = Institution.objects.order_by('-id')
    return render(request, 'government/institution_list.html', {'institutions': insts})


@login_required
@gov_required
def institution_create(request):
    if request.method == 'POST':
        form = InstitutionCreateForm(request.POST)
        if form.is_valid():
            inst = form.save(commit=False)
            inst.verified = False
            inst.save()
            AuditLog.objects.create(user=request.user, action='institution_added', details=f'Added institution {inst.pk}')
            messages.success(request, 'Institution created and pending verification.')
            return redirect('government:institution_list')
    else:
        form = InstitutionCreateForm()
    return render(request, 'government/institution_form.html', {'form': form})


@login_required
@gov_required
def institution_verify(request, pk):
    inst = get_object_or_404(Institution, pk=pk)
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'verify':
            inst.verified = True
            inst.save()
            AuditLog.objects.create(user=request.user, action='institution_verified', details=f'Verified institution {inst.pk}')
            messages.success(request, 'Institution verified.')
        elif action == 'unverify':
            inst.verified = False
            inst.save()
            AuditLog.objects.create(user=request.user, action='institution_unverified', details=f'Unverified institution {inst.pk}')
            messages.success(request, 'Institution set to not verified.')
        return redirect('government:institution_list')
    return render(request, 'government/institution_verify.html', {'institution': inst})


@login_required
@gov_required
def business_list(request):
    bs = Business.objects.order_by('-registered_at')
    return render(request, 'government/business_list.html', {'businesses': bs})


@login_required
@gov_required
def business_create(request):
    if request.method == 'POST':
        form = BusinessForm(request.POST)
        if form.is_valid():
            b = form.save(commit=False)
            b.registered_by = request.user
            b.save()
            AuditLog.objects.create(user=request.user, action='business_registered', details=f'Registered business {b.pk}')
            messages.success(request, 'Business registered and pending verification.')
            return redirect('government:business_list')
    else:
        form = BusinessForm()
    return render(request, 'government/business_form.html', {'form': form})


@login_required
@gov_required
def business_verify(request, pk):
    b = get_object_or_404(Business, pk=pk)
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'verify':
            b.verified = True
            b.verified_by = request.user
            b.verified_at = timezone.now()
            b.save()
            AuditLog.objects.create(user=request.user, action='business_verified', details=f'Verified business {b.pk}')
            messages.success(request, 'Business verified.')
        elif action == 'unverify':
            b.verified = False
            b.verified_by = None
            b.verified_at = None
            b.save()
            AuditLog.objects.create(user=request.user, action='business_unverified', details=f'Unverified business {b.pk}')
            messages.success(request, 'Business unverified.')
        return redirect('government:business_list')
    return render(request, 'government/business_verify.html', {'business': b})