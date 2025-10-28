from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.home, name='home'),

    # Owner
    path('owner/profile/', views.owner_profile, name='owner_profile'),
    path('owner/confirm-otp/', views.owner_confirm_otp, name='owner_confirm_otp'),

    # HR: create verification
    path('hr/verify/', views.hr_verify, name='hr_verify'),

    # HR: list of requests (new) - matches /hr/request/
    path('hr/request/', views.hr_request_list, name='hr_request_list'),

    # HR: status/detail for a specific request by UUID
    path('hr/request/<uuid:uuid>/', views.hr_request_status, name='hr_request_status'),
    path('hr/request/<uuid:uuid>/view/', views.hr_view_request, name='hr_view_request'),

    # Institution certificate management (if present)
    path('institution/<int:inst_id>/certificates/', views.institution_cert_list, name='institution_cert_list'),
    path('institution/<int:inst_id>/certificates/add/', views.institution_cert_create, name='institution_cert_create'),
    path('institution/<int:inst_id>/certificates/<int:pk>/edit/', views.institution_cert_edit, name='institution_cert_edit'),
    path('institution/<int:inst_id>/certificates/<int:pk>/delete/', views.institution_cert_delete, name='institution_cert_delete'),
]