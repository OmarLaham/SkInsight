from allauth.account.adapter import DefaultAccountAdapter
from allauth.exceptions import ImmediateHttpResponse

from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages

from django.contrib.auth import get_user_model

from django.utils.translation import gettext_lazy as _

# Drives the redirect logic on user login based on user's group (admin, professional, client, other)
class MyAccountAdapter(DefaultAccountAdapter):
    def get_login_redirect_url(self, request):
        user = request.user
        if not user.is_authenticated:
            return '/'

        if user.groups.filter(name='admin').exists():
            return reverse('admin_view')
        elif user.groups.filter(name='professional').exists():
            return reverse('professional_dashboard')
        elif user.groups.filter(name='client').exists():
            return reverse('client_dashboard')

        return '/'  # fallback
    
    # Don't Allow sign up using Outh. User will be created manually (admin) using their Gmail, the they use Outh (Google) to authenticate
    def is_open_for_signup(self, request):
        return False 

    # Skip the confirmation page after Outh login
    def is_auto_signup_allowed(self, request, sociallogin):
        return True  # Skip the confirmation page
    
    #  Ensure that only users who already exist in Django DB (with matching email) can log in via Google.
    def pre_social_login(self, request, sociallogin):
        """
        This
        """
        email = sociallogin.account.extra_data.get('email')

        if not email:
            messages.error(request, _("Google account has no email."))
            raise ImmediateHttpResponse(redirect(reverse('homepage')))

        try:

            User = get_user_model()

            user = User.objects.get(email=email)
            sociallogin.connect(request, user)
        except User.DoesNotExist:
            messages.error(request, _("No user account is assigned to your social account email."))
            raise ImmediateHttpResponse(redirect(reverse('homepage')))