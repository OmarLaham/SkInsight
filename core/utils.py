from django.conf import settings
from django.contrib.auth.models import Group
from django.shortcuts import redirect
from django.core.exceptions import PermissionDenied

from datetime import datetime
from typing import List, Dict
from django.utils.translation import gettext_lazy as _

from .models import User



def create_fhir_resource_user(username, email, is_professional, fhir_resource_id:str):
    role = "professional" if is_professional else "client"
    
    # Create the user
    user = User.objects.create_user(
        username=username,
        email=email,
        password= settings.USER_DEFAULT_PASSWORD,
        fhir_resource_id=fhir_resource_id,
        is_verified=False
    )

    # Assign to role group
    group, _ = Group.objects.get_or_create(name=role)
    user.groups.add(group)

    print(f"✅ Created {role.capitalize()} User: {username} (FHIR ID: {user.fhir_resource_id})")
    return user

def get_fhir_resource_extension_value(extensions: list, target_url: str):
    for ext in extensions:
        if ext.get("url") == target_url:
            return ext.get("valueInteger")  # or valueString, valueBoolean, etc.
    return None


def email_exists(email):
    return User.objects.filter(email=email).exists()

def get_user_fhir_id(request):
    """
    Get the FHIR resource ID for the logged-in user if they belong to 'professional' or 'client' group.

    Args:
        request: Django HttpRequest object

    Returns:
        str: FHIR resource ID of the user

    Raises:
        PermissionDenied: If user doesn't belong to 'professional' or 'client' group
    """
    if not request.user.is_authenticated:
        return redirect("auth")

    user = request.user

    if user.groups.filter(name="professional").exists() or user.groups.filter(name="client").exists():
        return user.fhir_resource_id

    else:
        raise PermissionDenied(
            f"The logged-in user (group: {user.groups.first().name if user.groups.exists() else 'none'}) "
            f"doesn't have an associated FHIR resource ID."
        )


def create_care_chart_js_data(sorted_submissions: List[dict], questionnaire_questions: List[dict]) -> dict:
    """
    Generates data for a CARE chart visualization in JavaScript format.

    This function processes a list of sorted submissions and questionnaire questions
    to compute progression values for each question over time. The progression values
    are clamped within specified bounds and are used to build datasets for chart rendering.

    Args:
        sorted_submissions (List[dict]): A list of submission dictionaries, sorted by date.
            Each submission contains an "authored" timestamp and a list of "item" dictionaries
            with question IDs and answers.
        questionnaire_questions (List[dict]): A list of dictionaries representing questionnaire
            questions. Each dictionary contains a "q" key for the question text.

    Returns:
        dict: A dictionary containing:
            - "labels" (List[str]): A list of formatted dates corresponding to submission timestamps.
            - "datasets" (List[dict]): A list of dataset dictionaries for chart rendering. Each dataset
              includes:
                - "label" (str): The question text.
                - "data" (List[int]): Progression values for the question over time.
                - "borderColor" (str): The color of the line in the chart.
                - "backgroundColor" (str): The background color of the chart (transparent).
                - "borderWidth" (int): The width of the line in the chart.
                - "tension" (float): The tension of the line (smoothness).
                - "pointRadius" (int): The radius of data points on the chart.
                - "pointHoverRadius" (int): The radius of data points when hovered.

    Notes:
        - The progression values are calculated based on the difference (delta) between
          current and previous answers, with adjustments for recovery, worsening, or improvement.
        - Values are clamped within the bounds defined by settings.CARE_CHART_ANSWER_MIN_VAL
          and settings.CARE_CHART_ANSWER_MAX_VAL.
        - The initial value for each question is defined by settings.CARE_CHART_ANSWER_INITIAL_VAL.
    """


    labels = [
        datetime.fromisoformat(sub["authored"]).strftime("%d/%m/%Y")
        for sub in sorted_submissions
    ]

    # Initialize progressions
    n_questions = len(questionnaire_questions)

    INIT_VAL = settings.CARE_CHART_ANSWER_INITIAL_VAL # represents the "middle" on the scale
    MIN_VAL = settings.CARE_CHART_ANSWER_MIN_VAL # Answers can't be larget than this value
    MAX_VAL = settings.CARE_CHART_ANSWER_MAX_VAL # Answers can't be smaller than this value

    progression_per_question = [[] for _ in range(n_questions)]
    current_values = [INIT_VAL] * n_questions
    previous_deltas = [0] * n_questions  # Used to track direction from last step

    for submission in sorted_submissions:
        # Parse answers from submission
        answers = {
            int(item["linkId"]): item["answer"][0].get("valueInteger", 0)
            for item in submission.get("item", [])
            if "answer" in item and item["answer"]
        }

        for i in range(n_questions):
            qid = i + 1
            delta = answers.get(qid, 0)
            prev_delta = previous_deltas[i]
            current_value = current_values[i]

            if not progression_per_question[i]:  # first entry
                new_value = current_value + delta
            else:
                if prev_delta >= 0:
                    # If previous was positive or zero, just add
                    new_value = current_value + delta
                else:
                    if delta >= 0:
                        # Moving toward positive: recovery
                        new_value = current_value + delta
                    elif abs(delta) > abs(prev_delta):
                        # More negative: worsen by delta - prev
                        worsen = abs(delta) - abs(prev_delta)
                        new_value = current_value - worsen
                    elif abs(delta) < abs(prev_delta):
                        # Less negative: improve by prev - delta
                        improve = abs(prev_delta) - abs(delta)
                        new_value = current_value + improve
                    else:
                        # Same negative: no change
                        new_value = current_value

            # Clamp to reasonable bounds
            if new_value > MAX_VAL:
                new_value = MAX_VAL
            elif new_value < MIN_VAL:
                new_value = MIN_VAL

            new_value = max(0, new_value)
            progression_per_question[i].append(new_value)

            # Update trackers
            current_values[i] = new_value
            previous_deltas[i] = delta

    # Build datasets
    datasets = [
        {
            "label": questionnaire_questions[i]["q"],
            "data": progression_per_question[i],
            "borderColor": f"hsl({i * 24}, 70%, 50%)",
            "backgroundColor": "transparent",
            "borderWidth": 2,
            "tension": 0.4,
            "pointRadius": 3,
            "pointHoverRadius": 5
        }
        for i in range(n_questions)
    ]

    # If we have only one submission, add "Default" timepoint, with INIT_val for all questions
    if len(sorted_submissions) < 2:
        labels = [_("Default")] + labels
        for i in range(len(datasets)):
            datasets[i]["data"] = [INIT_VAL] + datasets[i]["data"]


    return {
        "labels": labels,
        "datasets": datasets
    }


def get_professional_to_clients_plan_details_as_dict(plan_definition: dict):
    plan_extensions = plan_definition.get("extension", [])

    plan_details = dict()
    for extension in plan_extensions:
        if "valueString" in extension:
            plan_details[extension["url"].split("/")[-1]] = extension["valueString"]
        elif "valueInteger" in extension:
            plan_details[extension["url"].split("/")[-1]] = extension["valueInteger"]
        elif "valueBoolean" in extension:
            plan_details[extension["url"].split("/")[-1]] = extension["valueBoolean"]
        elif "valueMoney" in extension:
            plan_details[extension["url"].split("/")[-1]] = extension["valueMoney"]["value"]


    if "n_monthly_questions" in plan_details:
        if plan_details["n_monthly_questions"] == settings.UNLIMITED_NUMBER_REPRESENTAION:
            plan_details["n_monthly_questions"] = _("Unlimited")
    if "n_monthly_flagged_questions" in plan_details:
        if plan_details["n_monthly_flagged_questions"] == settings.UNLIMITED_NUMBER_REPRESENTAION:
            plan_details["n_monthly_flagged_questions"] = _("Unlimited")

    return plan_details


def get_whatsapp_number(fhir_resource_obj):
    """
    Extracts the WhatsApp number from the FHIR resource object.

    Args:
        fhir_resource_obj (dict): The FHIR resource object containing contact information.

    Returns:
        str: The WhatsApp number if available, otherwise an empty string.
    """
    for telecom in fhir_resource_obj.get("telecom", []):
        if telecom.get("system") == "phone" and telecom.get("use") == "mobile":
            if telecom.get("extension"):
                for ext in telecom["extension"]:
                    if ext.get("valueCode") == "whatsapp":
                        return telecom.get("value", "")
    raise Exception(_("Cannot find WhatsApp number for this FHIR resource."))

def get_user_by_fhir_resource_id(fhir_resource_id):
    user = User.objects.filter(fhir_resource_id=fhir_resource_id).exclude(username="admin").first() # TODO: Remove exclude for produciton. This is a temp fix because admin is using exisiting  fhir resource ids to test the app 
    return user

# Plan IDs are stored in Django User to minimize FHIR queries and search

def set_professional_platform_plan_id(professional_fhir_id, plan_fhir_id):
    user = get_user_by_fhir_resource_id(professional_fhir_id)
    if not user:
        raise Exception ("Cannot find user")
    user.platform_plan_id = plan_fhir_id
    user.save()

def get_professional_platform_plan_id(professional_fhir_id):
    user = get_user_by_fhir_resource_id(professional_fhir_id)
    if not user:
        raise Exception ("Cannot find user")

    if not hasattr(user, 'platform_plan_id'):
        return ""
    
    return user.platform_plan_id

def set_professional_clients_plan_id(professional_fhir_id, plan_fhir_id):
    user = get_user_by_fhir_resource_id(professional_fhir_id)
    if not user:
        raise Exception ("Cannot find user")
    
    user.clients_plan_id = plan_fhir_id
    user.save()

def get_professional_clients_plan_id(professional_fhir_id):
    user = get_user_by_fhir_resource_id(professional_fhir_id)
    if not user:
        raise Exception ("Cannot find user")

    if not hasattr(user, 'clients_plan_id'):
        return ""
    
    return user.clients_plan_id

def set_client_professional_plan_id(client_fhir_id, plan_fhir_id):
    user = get_user_by_fhir_resource_id(client_fhir_id)
    if not user:
        raise Exception ("Cannot find user")
    
    user.professional_plan_id = plan_fhir_id
    user.save()

def get_client_professional_plan_id(client_fhir_id):
    user = get_user_by_fhir_resource_id(client_fhir_id)
    if not user:
        raise Exception ("Cannot find user")

    if not hasattr(user, 'professional_plan_id'):
        return ""
    
    return user.professional_plan_id

def render_rating_stars(score: int, max: int = 5):
    if score < 0 or score > max:
        raise ValueError("Rating score cannot be negative or larger than scale max.")
    
    star_on = "★"
    star_off = "☆"

    rating = (score * star_on) + ((max - score) * star_off)
    return rating