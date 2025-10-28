from django.urls import path
from . import views

app_name = 'government'

urlpatterns = [
    path('', views.gov_dashboard, name='dashboard'),

    # Institutions management (uses core.Institution model)
    path('institutions/', views.institution_list, name='institution_list'),
    path('institutions/add/', views.institution_create, name='institution_create'),
    path('institutions/<int:pk>/verify/', views.institution_verify, name='institution_verify'),

    # Businesses management (government Business model)
    path('businesses/', views.business_list, name='business_list'),
    path('businesses/add/', views.business_create, name='business_create'),
    path('businesses/<int:pk>/verify/', views.business_verify, name='business_verify'),
]