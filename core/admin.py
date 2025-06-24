# core/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User  # Import your custom user model

# Register the custom user model with the admin site to be visible in Django control panel
@admin.register(User)
class UserAdmin(BaseUserAdmin):
    # Optional: customize the admin display
    fieldsets = BaseUserAdmin.fieldsets
    list_display = ('username', 'email', 'is_staff', 'is_active')
    search_fields = ('username', 'email')
