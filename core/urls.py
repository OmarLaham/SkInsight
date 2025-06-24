"""
URL configuration for core project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.conf.urls.i18n import i18n_patterns
from django.urls import path, include
from django.views.generic.base import RedirectView
from . import views

from allauth.account.views import LoginView




urlpatterns = [

    path('', views.home_view, name='home'),  # this makes '/' point to your homepage
    
    path('accounts/login', LoginView.as_view(template_name="account/login.html"), name="account_login"), # Overriding default template from allauth
    path('auth', views.auth_view, name='auth'),  # this makes '/auth' point to your auth view

    path('dashboard', views.dashboard_router_view, name='dashboard_router'),  # redirects user to their respective dashboard based on their group (role)

    # Admin URLs
    path('admin/', RedirectView.as_view(url='/admin/dashboard'), name="admin_view"),  # this redirects '/admin' to your admin dashboard
    path('admin/dashboard', views.admin_dashboard_view, name='admin_dashboard'),  # this makes '/admin/dashboard' point to your admin dashboard view
    path('admin/quiz_populate/', views.quiz_populate_view, name='quiz_populate'),
    path('admin/quiz_deactivate/<str:questionnaire_title>/', views.quiz_deactivate_view, name='quiz_deactivate'),

    # Professional URLs
    path('professional/dashboard', views.professional_dashboard_view, name='professional_dashboard'),  # this makes '/professional/dashboard' point to your professional dashboard view
    path('professional/create/', views.create_professional_view, name='create_professional'),
    path('professional/edit/<str:practitioner_id>/', views.edit_professional_view, name='edit_professional'),
    path('professional/subscribe/<str:practitioner_id>/', views.professional_subscription_view, name="professional_subscription"),
    path('professional/clients-plan/<str:practitioner_id>/', views.professional_plan_to_clients_view, name="professional_clients_plan"),
    
    path('professional/activate/<str:practitioner_id>/', views.activate_professional_view, name='activate_professional'),
    path('professional/deactivate/<str:practitioner_id>/', views.deactivate_professional_view, name='deactivate_professional'),

    # Client URLs
    path('client/dashboard', views.client_dashboard_view, name='client_dashboard'),  # this makes '/client/dashboard' point to your client dashboard view
    path('client/create/', views.create_client_view, name='create_client'),
    path('client/edit/<str:client_id>/', views.edit_client_view, name='edit_client'),
    path('client/activate/<str:client_id>/', views.activate_client_view, name='activate_client'),
    path('client/deactivate/<str:client_id>/', views.deactivate_client_view, name='deactivate_client'),

    path('client/quiz-start/<str:client_fhir_id>/', views.quiz_start_view, name='quiz_start'),  # this makes '/quizz_start' point to your quizz start view
    path('client/care-chart/<str:client_id>/', views.care_chart_view, name='care_chart'), 
    

    # General URLs
    path('messages/<str:receiver_whatsapp_number>/', views.messages_view, name='messages'),

    path('accounts/', include('allauth.urls')),  # This includes allauth URLs for user authentication

    path('countact-us', views.contact_us_view, name="contact_us"),


    path('switch_language/', include('django.conf.urls.i18n')),  # language switcher

    # Admin URL. CP refers to Control panel
    path('cp/', admin.site.urls)
    

]
