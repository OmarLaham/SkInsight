# models.py
from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    # Common fields go here
    email = models.EmailField(unique=True)  # override to enforce uniqueness
    fhir_resource_id = models.CharField(max_length=255, null=False, blank=False, default="NON_FHIR_RESOURCE")
    platform_plan_id = models.CharField(max_length=255, null=True, blank=True, default="") # Use to link professional to platform plan subscription (PractitionerRole) -> minimize FHIR queries
    clients_plan_id = models.CharField(max_length=255, null=True, blank=True, default="") # Use to link professional to their clients plan subscription -> minimize FHIR queries
    professional_plan_id  = models.CharField(max_length=255, null=True, blank=True, default="") # Use to link client to professional plan subscription -> minimize FHIR queries
    is_verified = models.BooleanField(default=False)
    
    def __str__(self):
        return self.username