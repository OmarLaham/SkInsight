from django.utils.translation import gettext_lazy as _
from . import fhir as fhir

# Use this file to populate Questionnaire FHIR resources for first time.

# The ID of the questionnaire to be used as the active questionnaire (e.g. to populate to FHIR if none exists, or if new one (with same ID) is added)

questionnaires = {}

# dict key represent the title of the questionnaire. This title is very important to populate this object as new FHIR Questionnaire resource
questionnaires["skincare-checkup-v.1.0"] = [

    {
        "q": _("How does your skin typically feel a few hours after cleansing?"),
        "options": [
            {"text": _("Oily/Shiny"), "value": -1, "value_type": "integer"},
            {"text": _("Dry/Tight"), "value": -1, "value_type": "integer"},
            {"text": _("Normal/Balanced"), "value": 1, "value_type": "integer"},
        ]
    },
    {
        "q": _("Do you frequently experience acne or skin rashes?"),
        "options": [
            {"text": _("Yes"), "value": -1, "value_type": "integer"},
            {"text": _("No"), "value": 1, "value_type": "integer"},
        ]
    },
    {
        "q": _("How sensitive is your skin to new skincare products?"),
        "options": [
            {"text": _("Highly sensitive"), "value": -2, "value_type": "integer"},
            {"text": _("Moderately sensitive"), "value": -1, "value_type": "integer"},
            {"text": _("Not sensitive"), "value": 0, "value_type": "integer"},
        ]
    },
    {
        "q": _("Does your skin get irritated by environmental factors (wind, cold, pollution)?"),
        "options": [
            {"text": _("Often"), "value": -2, "value_type": "integer"},
            {"text": _("Sometimes"), "value": -1, "value_type": "integer"},
            {"text": _("No"), "value": 0, "value_type": "integer"},
        ]
    },
    {
        "q": _("Have you noticed uneven skin tone or dark spots recently?"),
        "options": [
            {"text": _("Yes"), "value": -1, "value_type": "integer"},
            {"text": _("No"), "value": 1, "value_type": "integer"},
        ]
    },
    {
        "q": _("How does your skin react to sun exposure?"),
        "options": [
            {"text": _("Burns easily"), "value": -2, "value_type": "integer"},
            {"text": _("Tans easily"), "value": -1, "value_type": "integer"},
            {"text": _("Rarely burns or tans"), "value": 0, "value_type": "integer"},
        ]
    },
    {
        "q": _("Have you developed new freckles or age spots in the past month?"),
        "options": [
            {"text": _("Yes"), "value": -1, "value_type": "integer"},
            {"text": _("No"), "value": 1, "value_type": "integer"},
        ]
    },
    {
        "q": _("At what age did you notice your first fine lines or wrinkles?"),
        "options": [
            {"text": _("Under 30"), "value": -3, "value_type": "integer"},
            {"text": _("30-40"), "value": -2, "value_type": "integer"},
            {"text": _("Over 40"), "value": -1, "value_type": "integer"},
            {"text": _("Haven’t noticed yet"), "value": 0, "value_type": "integer"},
        ]
    },
    {
        "q": _("Have you noticed increased sagging or loss of firmness in your skin?"),
        "options": [
            {"text": _("Yes"), "value": -1, "value_type": "integer"},
            {"text": _("No"), "value": 0, "value_type": "integer"},
        ]
    },
    {
        "q": _("How would you describe your skin's elasticity?"),
        "options": [
            {"text": _("Good, bounces back quickly"), "value": 1, "value_type": "integer"},
            {"text": _("Moderate, sometimes feels saggy"), "value": -1, "value_type": "integer"},
            {"text": _("Poor, looks loose or saggy"), "value": -2, "value_type": "integer"},
        ]
    },
    {
        "q": _("Do you regularly experience dry or flaky skin?"),
        "options": [
            {"text": _("Yes"), "value": -1, "value_type": "integer"},
            {"text": _("No"), "value": 0, "value_type": "integer"},
        ]
    },
    {
        "q": _("Do you suffer from redness or frequent flushing of the skin?"),
        "options": [
            {"text": _("Yes"), "value": -1, "value_type": "integer"},
            {"text": _("No"), "value": 0, "value_type": "integer"},
        ]
    },
    {
        "q": _("How often do you notice clogged or enlarged pores?"),
        "options": [
            {"text": _("Often"), "value": -2, "value_type": "integer"},
            {"text": _("Sometimes"), "value": -1, "value_type": "integer"},
            {"text": _("Rarely or never"), "value": 1, "value_type": "integer"},
        ]
    },
    {
        "q": _("Do you feel tightness or discomfort after cleansing your skin?"),
        "options": [
            {"text": _("Yes"), "value": -1, "value_type": "integer"},
            {"text": _("No"), "value": 1, "value_type": "integer"},
        ]
    },
    {
        "q": _("Do you feel tingling or burning when applying skincare products?"),
        "options": [
            {"text": _("Yes"), "value": -1, "value_type": "integer"},
            {"text": _("No"), "value": 0, "value_type": "integer"},
        ]
    }
]



def get_questionnaire(questionnaire_title: str) -> list[dict]:
    """
    Retrieve a questionnaire from the questionnaires dictionary using its title.

    Args:
        questionnaire_title (str): The title of the questionnaire to retrieve.

    Returns:
        list[dict]: The questionnaire corresponding to the given title, or raises error if not found.
    """
    if questionnaire_title not in questionnaires:
        raise KeyError(f"No Questionnaire with queried title found: {questionnaire_title}")
    
    return questionnaires[questionnaire_title]



