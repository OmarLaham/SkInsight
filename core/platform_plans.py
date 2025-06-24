from enum import Enum
from django.conf import settings

class CONSULTATION_VOICE_MESSAGE_SUPPORT(str, Enum):
    NOT_SUPPORTED = "not_supported"
    ONLY_Professional = "only_professional"
    ONLY_CLINET = "only_client"
    PROFESSIONAL_AND_CLIENT = "professional_and_client"

platform_plans = {
    "platformtoprofessionalplan-basic-v-1-0": { # "PlatformToProfessionalPlan-" is the standard prefix for platform plan title
        "length_in_days": 30,
        "n_checkups_per_month": 45,
        "checkup_archive_capacity": 45 * 12 * 2,# n_checkups_per_month * 12 months * 2 years -> checkups submitted during the period of this plan must be saved for this time
        "consultation_text": True,
        "consultation_image_upload": True,
        "consultation_voice_message_support": CONSULTATION_VOICE_MESSAGE_SUPPORT.NOT_SUPPORTED,
        "care_chart": True,
        "product_suggestion": "COMING_SOON",
        "payment": 45.00,
    },
    "platformtoprofessionalplan-standard-v-1-0": {
        "length_in_days": 30,
        "n_checkups_per_month": 150,
        "checkup_archive_capacity": 150 * 12 * 2,# n_checkups_per_month * 12 months * 2 years -> checkups submitted during the period of this plan must be saved for this time
        "consultation_text": True,
        "consultation_image_upload": True,
        "consultation_voice_message_support": CONSULTATION_VOICE_MESSAGE_SUPPORT.NOT_SUPPORTED,
        "care_chart": True,
        "product_suggestion": "COMING_SOON",
        "payment": 125.00,
    },
    "platformtoprofessionalplan-premium-v-1-0": {
        "length_in_days": 30,
        "n_checkups_per_month": 300,
        "checkup_archive_capacity": 300 * 12 * 2,# n_checkups_per_month * 12 months * 2 years -> checkups submitted during the period of this plan must be saved for this time
        "consultation_text": True,
        "consultation_image_upload": True,
        "consultation_voice_message_support": CONSULTATION_VOICE_MESSAGE_SUPPORT.NOT_SUPPORTED,
        "care_chart": True,
        "product_suggestion": "COMING_SOON",
        "payment": 225.00,
    }
}

vouchers = {
    "SUMMER2025": {
        "code": "SUMMER2025",
        "display": "25% discount for summer sign-ups"
    }
}