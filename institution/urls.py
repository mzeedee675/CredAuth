from django.urls import path
from . import views

app_name = 'institution'

urlpatterns = [
    # Certificate management for an institution
    path('institution/<int:inst_id>/certificates/', views.institution_cert_list, name='cert_list'),
    path('institution/<int:inst_id>/certificates/add/', views.institution_cert_create, name='cert_create'),
    path('institution/<int:inst_id>/certificates/<int:pk>/edit/', views.institution_cert_edit, name='cert_edit'),
    path('institution/<int:inst_id>/certificates/<int:pk>/delete/', views.institution_cert_delete, name='cert_delete'),

    # HR view of owner details after OTP confirmation (uses the VerificationRequest uuid)
    path('hr/request/<uuid:uuid>/view/', views.hr_view_owner, name='hr_view_owner'),
]