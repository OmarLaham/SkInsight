from enum import Enum

from django.conf import settings
from django.shortcuts import redirect

import json
from decimal import Decimal

from datetime import datetime, timezone
import uuid
import requests
from urllib.parse import urlencode

from typing import Optional, Dict, List

from .utils import create_fhir_resource_user, email_exists, get_fhir_resource_extension_value

from azure.identity import ClientSecretCredential
from django.core.cache import cache


# TODO: remove old version [no - cache]
# def get_access_token() -> str:
#     """
#     Acquire Azure AD OAuth2 access token for Azure Healthcare FHIR API.
    
#     Returns:
#         str: Bearer access token.
#     """
#     credential = ClientSecretCredential(
#         tenant_id=settings.AZURE_TENANT_ID,
#         client_id=settings.AZURE_CLIENT_ID,
#         client_secret=settings.AZURE_CLIENT_SECRET
#     )
#     token = credential.get_token(settings.AZURE_FHIR_SERVICE_SCOPE)
#     return token.token

def get_access_token() -> str:
    """
    Acquire and cache Azure AD OAuth2 access token for Azure Healthcare FHIR API.
    This leads to Performance Improvement, Reduced API Calls, and Lower Resource Utilization.
    
    Returns:
        str: Bearer access token.
    """
    token_cache_key = "azure_access_token"

    # Check if token is already cached
    cached_token = cache.get(token_cache_key)
    if cached_token:
        return cached_token

    # Get a new token
    credential = ClientSecretCredential(
        tenant_id=settings.AZURE_TENANT_ID,
        client_id=settings.AZURE_CLIENT_ID,
        client_secret=settings.AZURE_CLIENT_SECRET
    )
    token = credential.get_token(settings.AZURE_FHIR_SERVICE_SCOPE)

    # Compute how long until the token expires
    now = datetime.now(timezone.utc).timestamp()
    expires_in = int(token.expires_on - now)

    # Subtract buffer (e.g., 60 seconds) to avoid using token near expiration
    timeout = max(expires_in - 1800, 0) # 30 (minute) * 60 (second)

    # Cache the token
    cache.set(token_cache_key, token.token, timeout=timeout)

    return token.token

# ============================================================================
# FHIR Practitioner
# ============================================================================

def list_practitioners(only_active: bool = True) -> list:
    """
    Retrieve a list of Practitioner resources from Azure Healthcare FHIR service,
    optionally filtered by active status.

    Args:
        only_active (bool): If True, only return active practitioners.

    Returns:
        list: A list of dictionaries, each representing a Practitioner.
    """
    access_token = get_access_token()
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/fhir+json",
        "Accept": "application/fhir+json",
    }

    # GET all Practitioner resources
    response = requests.get(
        f"{settings.AZURE_FHIR_SERVICE_URL}/Practitioner",
        headers=headers,
    )
    response.raise_for_status()
    practitioner_entries = response.json().get("entry", [])

    # Filter and transform practitioners
    practitioners = []
    for entry in practitioner_entries:
        resource = entry.get("resource", {})
        if only_active and not resource.get("active", True):
            continue

        # Extract required fields

        telecom = resource.get("telecom", [])
        phone_number = ""
        if len(telecom) > 0:
            phone_number = telecom[0].get("value", "")
            
        whatsapp_link, whatsapp_number = "", ""
        if len(telecom) > 1:
            whatsapp_link = telecom[1].get("value", "")
            if not whatsapp_link == "":
                whatsapp_number = whatsapp_link.split("https://wa.me/")[-1]  # Extract number from WhatsApp link

        practitioner_data = {
            "practitioner_id": resource.get("id"),
            "title": resource.get("name", [{}])[0].get("prefix", [None])[0],
            "first_name": resource.get("name", [{}])[0].get("given", [None])[0],
            "last_name": resource.get("name", [{}])[0].get("family"),
            "full_name": resource.get("name", [{}])[0].get("prefix", [None])[0] + " " + resource.get("name", [{}])[0].get("given", [None])[0] + " " + resource.get("name", [{}])[0].get("family"),
            "gender": resource.get("gender"),
            "organization_name": resource.get("address", [{}])[0].get("text"),
            "organization_city": resource.get("address", [{}])[0].get("city"),
            "organization_country": resource.get("address", [{}])[0].get("country"),
            "phone_number": phone_number,
            "whatsapp_number": whatsapp_number,
            "photo_url": resource.get("photo", [{}])[0].get("url"),
            "active": resource.get("active"),
        }
        practitioners.append(practitioner_data)

    return practitioners

def get_practitioner(practitioner_id: str) -> Dict:
    """
    Retrieve a Practitioner resource from Azure Healthcare FHIR service by its ID.

    Args:
        practitioner_id (str): The FHIR resource ID of the Practitioner to retrieve.

    Returns:
        Dict: JSON response from FHIR server (Practitioner resource).
    """
    access_token = get_access_token()
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/fhir+json",
        "Accept": "application/fhir+json",
    }

    # GET Practitioner resource by ID
    response = requests.get(
        f"{settings.AZURE_FHIR_SERVICE_URL}/Practitioner/{practitioner_id}",
        headers=headers,
    )
    response.raise_for_status()  # Raises HTTPError if status >= 400

    return response.json()


def create_practitioner(
    title: str,
    first_name: str,
    last_name: str,
    gender: str,
    email: str,
    organization_name: str,
    organization_city: str,
    organization_country: str,
    phone_number: str,
    whatsapp_number: str,
    photo_url: Optional[str] = None,
) -> Dict:
    """
    Create a new Practitioner resource in Azure Healthcare FHIR service.

    Args:
        title (str): Professional title, e.g., "Dr."
        first_name (str): First name.
        last_name (str): Last name / family name.
        gender (str): "male" or "female" (FHIR compliant).
        email (str): Email address of the practitioner (used by Django User).
        organization_name (str): Name of the organization (e.g., CarePlus).
        organization_city (str): City of the organization.
        organization_country (str): Country of the organization.
        phone_number (str): Contact phone number
        whatsapp_number (str): Contact WhatsApp number - This will be used for Practitioner <-> Patient communication
        photo_url (Optional[str]): URL to practitioner's photo.

    Returns:
        Dict: JSON response from FHIR server (Practitioner resource created).
    """

    # First, check if emails is not used by another Django account
    if email_exists(email):
        raise ValueError(f"Email {email} is already registered for another user.")

    # Get access token and prepare headers to connect to Azure FHIR
    access_token = get_access_token()
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/fhir+json",
        "Accept": "application/fhir+json",
    }

    # Prepare FHIR Practitioner resource JSON body
    practitioner_payload = {
        "resourceType": "Practitioner",
        "name": [
            {
                "prefix": [title],
                "given": [first_name],
                "family": last_name,
            }
        ],
        "gender": gender,
        "photo": [{"url": photo_url}] if photo_url else [],
        "qualification": [
            {
                "code": {
                    "text": "Skincare Professional"
                }
            }
        ],
        "address": [
            {
                "city": organization_city,
                "country": organization_country,
                "text": organization_name
            }
        ],
        "telecom": [
            {
                "system": "phone",
                "value": str(phone_number),
                "use": "mobile",
                "rank": 1
            },
            {
                "system": "url",
                "value": f"https://wa.me/{str(whatsapp_number)}",
                "use": "mobile",
                "rank": 2
            }
        ],
        "active": True,  # active by default
    }


    # POST to FHIR server
    response = requests.post(
        f"{settings.AZURE_FHIR_SERVICE_URL}/Practitioner",
        json=practitioner_payload,
        headers=headers,
    )
    response.raise_for_status()  # Raises HTTPError if status >= 400
    response_json = response.json()

    # if successful status, create a Django User for this practitioner. This is for roles management purpose
    create_fhir_resource_user(
        username=f"{first_name.lower()}_{last_name.lower()}",
        email=email,
        is_professional=True,
        fhir_resource_id=response_json["id"]
    )

    return response_json


def edit_practitioner(
    practitioner_fhir_id: str,
    updates: Dict,
) -> Dict:
    """
    Edit an existing Practitioner resource by its FHIR resource ID.

    Args:
        practitioner_id (str): The FHIR resource ID of the Practitioner to update.
        updates (Dict): Partial JSON with fields to update (FHIR-compliant).

    Returns:
        Dict: Updated Practitioner resource JSON.
    """

    access_token = get_access_token()
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/fhir+json",
        "Accept": "application/fhir+json",
    }

    # First, GET the current Practitioner resource to merge updates
    practitioner = get_practitioner(practitioner_fhir_id)

    # Update practioner using form values
    updated_practitioner = practitioner.copy()
    updated_practitioner['name'] = [{
        'prefix': [updates['title']],
        'given': [updates['first_name']],
        'family': updates['last_name']
    }]

    updated_practitioner['gender'] = updates['gender']

    updated_practitioner['address'] = [{
        'text': updates['organization_name'],
        'city': updates['organization_city'],
        'country': updates['organization_country']
    }]

    updated_practitioner["telecom"] = [
        {
            "system": "phone",
            "value": str(updates["phone_number"]),
            "use": "mobile",
            "rank": 1
        },
        {
            "system": "url",
            "value": f"https://wa.me/{str(updates['whatsapp_number'])}",
            "use": "mobile",
            "rank": 2
        }
    ]

    updated_practitioner['photo'] = [{
        'url': updates['photo_url']
    }]

    # PUT updated resource back
    put_response = requests.put(
        f"{settings.AZURE_FHIR_SERVICE_URL}/Practitioner/{practitioner_fhir_id}",
        json=updated_practitioner,
        headers=headers,
    )
    put_response.raise_for_status()


    return put_response.json()


def deactivate_practitioner(practitioner_id: str, redirect_to_admin_view=True) -> Dict:
    """
    Deactivate a Practitioner resource by setting 'active' to False.

    Args:
        practitioner_id (str): The FHIR resource ID of the Practitioner to activate.
        redirect_to_admin_view (bool): If True, redirect to admin dashboard after activation.

    Returns:
        Dict: Updated Practitioner resource JSON with 'active': False (OR) Redirect to admin dashboard [ depending on the redirect_to_admin_view arg ]
    """
    access_token = get_access_token()
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/fhir+json",
        "Accept": "application/fhir+json",
    }

    # Fetch current practitioner resource
    practitioner = get_practitioner(practitioner_id)

    # Set 'active' to False
    practitioner["active"] = False

    # Update the resource on the FHIR server
    update_response = requests.put(
        f"{settings.AZURE_FHIR_SERVICE_URL}/Practitioner/{practitioner_id}",
        json=practitioner,
        headers=headers,
    )
    update_response.raise_for_status()

    # Keep the function flexible to be called by different hooks
    if redirect_to_admin_view:
        return redirect("/admin/dashboard")  # Redirect to admin dashboard after deactivation
    else:
        return update_response.json()

def activate_practitioner(practitioner_id: str, redirect_to_admin_view=True) -> Dict:
    """
    Activate a Practitioner resource by setting 'active' to True.

    Args:
        practitioner_id (str): The FHIR resource ID of the Practitioner to activate.
        redirect_to_admin_view (bool): If True, redirect to admin dashboard after activation.

    Returns:
        Dict: Updated Practitioner resource JSON with 'active': True (OR) Redirect to admin dashboard [ depending on the redirect_to_admin_view arg ]
    """
    access_token = get_access_token()
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/fhir+json",
        "Accept": "application/fhir+json",
    }

    # Fetch current practitioner resource
    practitioner = get_practitioner(practitioner_id)

    # Set 'active' to False
    practitioner["active"] = True

    # Update the resource on the FHIR server
    update_response = requests.put(
        f"{settings.AZURE_FHIR_SERVICE_URL}/Practitioner/{practitioner_id}",
        json=practitioner,
        headers=headers,
    )
    update_response.raise_for_status()

    # Keep the function flexible to be called by different hooks
    if redirect_to_admin_view:
        return redirect("/admin/dashboard")  # Redirect to admin dashboard after deactivation
    else:
        return update_response.json()


# ============================================================================
# FHIR Patient (client)
# ============================================================================

def list_patients(practitioner_fhir_id: str, only_active: bool = True) -> list:
    """
    Retrieve a list of Patient resources from Azure Healthcare FHIR service,
    filtered by linked Practitioner (generalPractitioner) if passed and not equal to None

    Args:
        practitioner_fhir_id (str) or None: The FHIR ID of the Practitioner to filter patients by. If None, clients of all practitioners will be retrieved
        only_active (bool): If True, only return active patients.

    Returns:
        list: A list of dictionaries, each representing a Patient.
    """
    access_token = get_access_token()
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/fhir+json",
        "Accept": "application/fhir+json",
    }

    # Filter patients by generalPractitioner reference using FHIR search parameter if practitioner_fhir_id not None
    response = requests.get(
        f"{settings.AZURE_FHIR_SERVICE_URL}/Patient",
        params={ "general-practitioner": f"Practitioner/{practitioner_fhir_id}" } if not practitioner_fhir_id is None else {},
        headers=headers,
    )
    response.raise_for_status()
    patient_entries = response.json().get("entry", [])

    patients = []
    for entry in patient_entries:
        resource = entry.get("resource", {})
        if only_active and not resource.get("active", True):
            continue

        telecom = resource.get("telecom", [])
        phone_number = ""
        if len(telecom) > 0:
            phone_number = telecom[0].get("value", "")

        whatsapp_link, whatsapp_number = "", ""
        if len(telecom) > 1:
            whatsapp_link = telecom[1].get("value", "")
            if not whatsapp_link == "":
                whatsapp_number = whatsapp_link.split("https://wa.me/")[-1]  # Extract number from WhatsApp link

        patient_data = {
            "patient_id": resource.get("id"),
            "title": resource.get("name", [{}])[0].get("prefix", [None])[0],
            "first_name": resource.get("name", [{}])[0].get("given", [None])[0],
            "last_name": resource.get("name", [{}])[0].get("family"),
            "full_name": resource.get("name", [{}])[0].get("prefix", [None])[0] + " " + resource.get("name", [{}])[0].get("given", [None])[0] + " " + resource.get("name", [{}])[0].get("family"),
            "gender": resource.get("gender"),
            "birth_date": resource.get("birthDate"),
            "phone_number": phone_number,
            "whatsapp_number": whatsapp_number,
            "practitioner_fhir_id": practitioner_fhir_id,
            "active": resource.get("active"),
        }
        patients.append(patient_data)

    return patients


def get_patient(patient_id: str) -> Dict:
    """
    Retrieve a Patient resource from Azure Healthcare FHIR service by its ID.

    Args:
        patient_id (str): The FHIR resource ID of the Patient to retrieve.

    Returns:
        Dict: JSON response from FHIR server (Patient resource).
    """
    access_token = get_access_token()
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/fhir+json",
        "Accept": "application/fhir+json",
    }

    # GET Patient resource by ID
    response = requests.get(
        f"{settings.AZURE_FHIR_SERVICE_URL}/Patient/{patient_id}",
        headers=headers,
    )
    response.raise_for_status()  # Raises HTTPError if status >= 400

    return response.json()


def create_patient(
    title: str,
    first_name: str,
    last_name: str,
    gender: str,
    birth_date: str,
    email: str,
    phone_number: str,
    whatsapp_number: str,
    practitioner_fhir_id: str,
) -> Dict:
    
    """
    Create a new Patient resource in Azure Healthcare FHIR service.

    Args:
        title (str): Patient's title, e.g., "Mr.", "Ms.", "Dr.".
        first_name (str): Patient's first name.
        last_name (str): Patient's last name.
        gender (str): "male", "female", "other", or "unknown" (FHIR compliant).
        birth_date (str): Patient's date of birth in YYYY-MM-DD format.
        email (str): Email address of the patient (used by Django User).
        phone_number (str): Contact phone number.
        whatsapp_number (str): Contact WhatsApp number - This will be used for Practitioner <-> Patient communication
        practitioner_fhir_id (str): FHIR ID of linked Practitioner.

    Returns:
        Dict: JSON response from FHIR server (Patient resource created).
    """

    if email_exists(email):
        raise ValueError(f"Email {email} is already registered for another user.")

    access_token = get_access_token()
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/fhir+json",
        "Accept": "application/fhir+json",
    }

    patient_payload = {
        "resourceType": "Patient",
        "name": [
            {
                "prefix": [title],
                "given": [first_name],
                "family": last_name,
            }
        ],
        "gender": gender,
        "birthDate": birth_date.isoformat(), # .isoformat() is important to make date serializable by JSON
        "generalPractitioner": [
            {
                "reference": f"Practitioner/{practitioner_fhir_id}"
            }
        ],
        "telecom": [{
            {
                "system": "phone",
                "value": phone_number,
                "use": "mobile",
                "rank": 1
            },
            {
                "system": "url",
                "value": f"https://wa.me/{str(whatsapp_number)}",
                "use": "mobile",
                "rank": 2
            }
        }],
        "active": True,
    }

    response = requests.post(
        f"{settings.AZURE_FHIR_SERVICE_URL}/Patient",
        json=patient_payload,
        headers=headers,
    )

    response.raise_for_status()
    response_json = response.json()

    # If successful status, create Django user linked to this patient
    create_fhir_resource_user(
        username=f"{first_name.lower()}_{last_name.lower()}",
        email=email,
        is_professional=False,
        fhir_resource_id=response_json["id"]
    )

    return response_json


def edit_patient(
    patient_fhir_id: str,
    updates: Dict,
) -> Dict:
    """
    Edit an existing Patient resource by its FHIR resource ID.

    Args:
        patient_id (str): The FHIR resource ID of the Patient to update.
        updates (Dict): Partial JSON with fields to update (FHIR-compliant).

    Returns:
        Dict: Updated Patient resource JSON.
    """

    access_token = get_access_token()
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/fhir+json",
        "Accept": "application/fhir+json",
    }

    # First, GET the current Patient resource to merge updates
    patient = get_patient(patient_fhir_id)

    # Update patient using form values
    updated_patient = patient.copy()

    updated_patient['name'] = [{
        'prefix': [updates['title']],
        'given': [updates['first_name']],
        'family': updates['last_name']
    }]

    updated_patient['gender'] = updates['gender']
    updated_patient['birthDate'] = updates['birth_date'].isoformat()  # Ensure date is in ISO format to make JSON Serialization possible

    phone_number = str(updates["phone_number"]) # Update phone_number
    whatsapp_number = str(updates["whatsapp_number"]) # Update Whatsapp number
    updated_patient["telecom"] = [
        {
            "system": "phone",
            "value": phone_number,
            "use": "mobile",
            "rank": 1
        },
        {
            "system": "url",
            "value": f"https://wa.me/{str(whatsapp_number)}",
            "use": "mobile",
            "rank": 2
        }
    ]


    # PUT updated resource back
    put_response = requests.put(
        f"{settings.AZURE_FHIR_SERVICE_URL}/Patient/{patient_fhir_id}",
        json=updated_patient,
        headers=headers,
    )
    put_response.raise_for_status()

    return put_response.json()

from django.shortcuts import redirect

def deactivate_patient(patient_id: str, redirect_to_admin_view=True) -> Dict:
    """
    Deactivate a Patient resource by setting 'active' to False.

    Args:
        patient_id (str): The FHIR resource ID of the Patient to deactivate.
        redirect_to_admin_view (bool): If True, redirect to admin dashboard after deactivation.

    Returns:
        Dict: Updated Patient resource JSON with 'active': False (OR) Redirect to admin dashboard [depending on redirect_to_admin_view].
    """
    access_token = get_access_token()
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/fhir+json",
        "Accept": "application/fhir+json",
    }

    # Fetch current patient resource
    patient = get_patient(patient_id)

    # Set 'active' to False
    patient["active"] = False

    # Update the resource on the FHIR server
    update_response = requests.put(
        f"{settings.AZURE_FHIR_SERVICE_URL}/Patient/{patient_id}",
        json=patient,
        headers=headers,
    )
    update_response.raise_for_status()

    # Keep the function flexible to be called by different hooks
    if redirect_to_admin_view:
        return redirect("/admin/dashboard")  # Redirect to admin dashboard after deactivation
    else:
        return update_response.json()


def activate_patient(patient_id: str, redirect_to_admin_view=True) -> Dict:
    """
    Activate a Patient resource by setting 'active' to True.

    Args:
        patient_id (str): The FHIR resource ID of the Patient to activate.
        redirect_to_admin_view (bool): If True, redirect to admin dashboard after activation.

    Returns:
        Dict: Updated Patient resource JSON with 'active': True (OR) Redirect to admin dashboard [depending on redirect_to_admin_view].
    """
    access_token = get_access_token()
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/fhir+json",
        "Accept": "application/fhir+json",
    }

    # Fetch current patient resource
    patient = get_patient(patient_id)

    # Set 'active' to True
    patient["active"] = True

    # Update the resource on the FHIR server
    update_response = requests.put(
        f"{settings.AZURE_FHIR_SERVICE_URL}/Patient/{patient_id}",
        json=patient,
        headers=headers,
    )
    update_response.raise_for_status()

    # Keep the function flexible to be called by different hooks
    if redirect_to_admin_view:
        return redirect("/admin/dashboard")  # Redirect to admin dashboard after activation
    else:
        return update_response.json()



# Patient Change Practioner 
# TODO: implement this function

    
# ============================================================================
# FHIR Plans and subscriptions
# ============================================================================

class PlanDefinitionType(str, Enum):
    PLATFORM_TO_PROFESSIONALS_PLAN = "PlatformToProfessionalsPlan"
    PROFESSIONAL_TO_CLIENTS_PLAN = "ProfessionalToClientsPlan"

def get_plan_definition(plan_definition_fhir_id: str, only_latest: bool = False) -> Optional[Dict]:
    """
    Retrieve a specific PlanDefinition resource by its FHIR ID.

    Args:
        plan_definition_fhir_id (str): The FHIR ID of the PlanDefinition.
        only_latest (bool): Indicates wether to return only latest plan definitins if multiple found. Default (False)

    Returns:
        Optional[Dict]: The PlanDefinition resource if found, otherwise None.
    """
    access_token = get_access_token()
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/fhir+json",
    }

    url = f"{settings.AZURE_FHIR_SERVICE_URL}/PlanDefinition/{plan_definition_fhir_id}"
    response = requests.get(url, headers=headers)

    if response.status_code == 404:
        return None
    
    response.raise_for_status()
    
    response_json = response.json()

    if 'resourceType' in response_json and response_json["resourceType"] == 'Bundle':
        if only_latest:
            return response.json()["entry"][-1]

    return response.json()


def create_plan_definition(
    plan_definition_type: PlanDefinitionType,
    author_id: str,
    creator_django_user_id: int,
    title: str,
    plan_details: Dict,
    description: str = "",
    version: str = "1.0"
) -> Dict:
    """
    Create a PlanDefinition resource for a practitioner with given plan details.

    Args:
        plan_definition_type (Enum): Type of the plan definition (e.g., PlatformToProfessionalsPlan).
        practitioner_id (str): FHIR Practitioner ID.
        django_user_id (integer): Django user id for the user who created the resource. This is very important to check if plan is created by professional or admin role (e.g. customer supppor)
        title (str): Title of the plan.
        plan_details (Dict): Plan specifics (e.g. limits, response times).
        description (str): Description of the plan.
        version (str): Version of the plan.

    Returns:
        Dict: Created PlanDefinition resource JSON.
    """
    access_token = get_access_token()
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/fhir+json",
        "Accept": "application/fhir+json",
    }

    if plan_definition_type == PlanDefinitionType.PLATFORM_TO_PROFESSIONALS_PLAN:
        author = [ { "name": settings.PLATFORM_ADMIN_FHIR_ID } ]
    elif plan_definition_type == PlanDefinitionType.PROFESSIONAL_TO_CLIENTS_PLAN:
        author = [ { "name": author_id } ] # for ease of query, always link it to the practionioner even if created by admin user (e.g. customer support)
    else:
        raise Exception(_("Provided plan definition type is not supported."))


    plan_definition = {
        "resourceType": "PlanDefinition",
        "status": "active",
        "title": title,
        "author": author,
        #"useContext": [],
        #"action": [],  # You can extend with detailed actions if needed
        "extension": [
            {
                "url": f"http://{settings.APP_DOMAIN_NAME}/fhir/StructureDefinition/django_user_id",
                "valueInteger": creator_django_user_id
            } 
        ],
    }

    # if PLATFORM_TO_PROFESSIONALS_Plan, Add title manually to avoid iterating over all PlanDefinitions when searching for platform ones since search by 'author' is not supported
    if plan_definition_type == PlanDefinitionType.PLATFORM_TO_PROFESSIONALS_PLAN:
        plan_name = f"{'-'.join(title.split('-')[:2]).lower()}"
        plan_version = ".".join(title.split("-")[-3:])
        plan_id = f"{plan_name}-{plan_version}".replace('.', '-')
        plan_definition["id"] = plan_id

    # Serialize plan_details into extensions or other appropriate fields
    # Here, we assume plan_details is a dict of key-values describing plan features
    extensions = plan_definition["extension"] # init with existing extensions
    for key, value in plan_details.items():
        if key == "payment": # payment has specific FHIR schema
            extensions.append(
                {
                    "url": f"http://{settings.APP_DOMAIN_NAME}/fhir/StructureDefinition/payment",
                    "valueMoney": {
                        "value": value,
                        "currency": settings.PLATFORM_CURRENCY
                    }
                }
            )
        else:
            extension_url = f"http://{settings.APP_DOMAIN_NAME}/fhir/StructureDefinition/{key}"

            if isinstance(value, bool): # Important: check bool before int to avoid (e.g.) True being converted to 1
                value_type = "valueBoolean"
                value = bool(value)
            elif isinstance(value, int):
                value_type = "valueInteger"
                value = int(value)
            else:
                value_type = "valueString" # String for all other types
                value = str(value)
            extensions.append({
                "url": extension_url,
                value_type: value
            })
            
    plan_definition["extension"] = extensions

    # To set a custom PlanDefinition ID we must use PUT with convenient URL instead of POST, otherwise a random ID will be generated even if ID is passed
    if plan_definition_type == PlanDefinitionType.PLATFORM_TO_PROFESSIONALS_PLAN:
        response = requests.put(
            f"{settings.AZURE_FHIR_SERVICE_URL}/PlanDefinition{('/' + plan_id)}",
            headers=headers,
            json=plan_definition,
        )
    elif plan_definition_type == PlanDefinitionType.PROFESSIONAL_TO_CLIENTS_PLAN:
        response = requests.post(
            f"{settings.AZURE_FHIR_SERVICE_URL}/PlanDefinition",
            headers=headers,
            json=plan_definition,
        )

    response.raise_for_status()
    return response.json()


def delete_plan_definition(plan_definition_id: str) -> str:
    """
    Deletes a specific PlanDefinition by ID, ensuring it belongs to the given Practitioner.

    Args:
        plan_id (str): FHIR PlanDefinition ID to be deleted.

    Returns:
        int: Status_code of the delete request.

    Raises:
        ValueError: If the plan does not belong to the practitioner or is not found.
        RuntimeError: If deletion fails.
    """
    
    access_token = get_access_token()
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/fhir+json",
    }

    # Get the plan by ID
    response = requests.get(
        f"{settings.AZURE_FHIR_SERVICE_URL}/PlanDefinition/{plan_definition_id}",
        headers=headers,
    )

    if response.status_code != 200:
        raise ValueError(f"PlanDefinition/{plan_definition_id} not found: {response.text}")

    
    # Proceed to delete
    delete_response = requests.delete(
        f"{settings.AZURE_FHIR_SERVICE_URL}/PlanDefinition/{plan_definition_id}",
        headers=headers,
    )

    if delete_response.status_code not in [200, 204]:
        raise RuntimeError(f"Failed to delete PlanDefinition/{plan_definition_id}: {delete_response.text}")

    return delete_response.status_code


def get_platform_plan_definitions(plan_fhir_ids) -> List[Dict]:
    """
    Retrieve all PlanDefinition resources authored by a given practitioner.

    Returns:
        List[Dict]: List of PlanDefinition resources.
    """
    access_token = get_access_token()
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/fhir+json",
    }

    plans = []

    for plan_fhir_id in plan_fhir_ids:

        url = f"{settings.AZURE_FHIR_SERVICE_URL}/PlanDefinition/{plan_fhir_id}"
        response = requests.get(url, headers=headers)

        if response.status_code == 404:
            continue

        response.raise_for_status()

        plan_json = response.json()
        plans.append(plan_json)


    if not plans:
        return None

    return plans



def subscribe_professional_to_platform_plan(
    deactivate_existing_subscription: bool,
    plan_definition_id: str,
    assigner_django_user_id: str,
    practitioner_id: str,
    start_date: str,
    end_date: str,
    paid_amount: int,
    voucher: Optional[dict] = None,
) -> Dict:
    """
    Subscribe a patient to a practitioner's care plan (CarePlan resource).

    Args:
        deactivate_existing_subscription: indicates wether must deactivate any existing PractionerRole FHIR resource for this practiontioner if exists
        assigner_django_user_id (str): the Django user ID of the admin assigning plan to the professional.
        practitioner_id (str): FHIR Practitioner resource ID.
        start_date (str): ISO start date (e.g. '2025-06-01').
        end_date (str): ISO end date (e.g. '2025-12-01').
        total_amount (int): Total amount paid
        plan_definition_id (str): PlanDefinition ID.
        billing_metadata (Optional[Dict]): Extra billing-related info to store as extensions.

    Returns:
        Dict: The created CarePlan resource as JSON.
    """
    access_token = get_access_token()
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/fhir+json",
        "Accept": "application/fhir+json",
    }

    plan = get_plan_definition(plan_definition_fhir_id=plan_definition_id)
    if not plan:
        raise ValueError(f"Cannot find a plan associated with ID: {plan_definition_id}.")
    
    if deactivate_existing_subscription:
        # Deactivate existing subscription so there is only one active. Also avoid deletion by only deactivating
        deactivate_practiotioner_subscription(practitioner_id=practitioner_id)

    # Build PractionerRole - Represents relationship between organization (app platform) and professional.
    practitioner_role = {
        "resourceType": "PractitionerRole",
        "active": True,
        "practitioner": {"reference": f"Practitioner/{practitioner_id}"},
        "organization": {"reference": "Organization/platform-admin"},
        "period": {"start": start_date, "end": end_date},
        "extension": [
            {
                "url": f"http://{settings.APP_DOMAIN_NAME}/fhir/StructureDefinition/assigner_django_user_id",
                "valueInteger": assigner_django_user_id
            },
            {
                "url": f"http://{settings.APP_DOMAIN_NAME}/fhir/StructureDefinition/totalAmount",
                "valueMoney": {
                    "value": float(Decimal(paid_amount)),
                    "currency": "USD"
                }
            }           
        ]
    }

    # Add voucher to extensions if provided
    if voucher:
        voucher_code = voucher["code"] # e.g. "SUMMMER2025"
        voucher_display = voucher["display"] # e.g. "25% discount for summer sign-ups"
        voucher_extension = {
            "url": f"http://{settings.APP_DOMAIN_NAME}/fhir/StructureDefinition/voucher",
            "valueCodeableConcept": {
                "coding": [
                    {
                        "system": f"http://{settings.APP_DOMAIN_NAME}/fhir/vouchers",
                        "code": voucher_code,
                        "display": voucher_display
                    }
                ]
            }
        }

        practitioner_role["extension"]
    
    # Submit PractitionerRole
    response = requests.post(
        f"{settings.AZURE_FHIR_SERVICE_URL}/PractitionerRole",
        headers=headers,
        json=practitioner_role,
    )
    response.raise_for_status()
    return response.json()


def deactivate_practiotioner_subscription(practitioner_id):
    # TODO: set status attribute so it's not "active"
    # TODO: implement this function later
    # raise Exception("Unimplemented function: deactivate_practiotioner_subscription")
    return None

def get_practitioner_to_clients_plan_definitions(
    practitioner_id: str
) -> List[Dict]:
    """
    Retrieve all PlanDefinition resources authored by a given practitioner.

    Args:
        practitioner_id (str): FHIR Practitioner ID.

    Returns:
        List[Dict]: List of PlanDefinition resources.
    """
    access_token = get_access_token()
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/fhir+json",
    }

    url = f"{settings.AZURE_FHIR_SERVICE_URL}/PlanDefinition?author=Practitioner/{practitioner_id}"
    response = requests.get(url, headers=headers)
    response.raise_for_status()

    bundle = response.json()
    plans = []

    for entry in bundle.get("entry", []):
        plans.append(entry["resource"])

    if not plans:
        return None

    return plans

def get_practitioner_to_clients_latest_plan_definition(
    practitioner_id: str
) -> Optional[str]:
    """
    Returns the most recent (latest) plan created by a Practitioner. In other words, a practitioner can have only one active plan to subscribe to but maybe
    has multiple older plans that are still stored simply because some clients (patients) are still subscribed to them.
    
    - If no plans exist: return None.
    - Otherwise: return the latest version of that plan.

    Args:
        practitioner_id (str): FHIR Practitioner ID.

    Returns:
        Optional[str]: Latest version string of the plan, or None if no plans found.

    Raises:
        ValueError: If practitioner has more than one distinct PlanDefinition.
    """
    plans = get_practitioner_to_clients_plan_definitions(practitioner_id)

    if plans is None:
        return None

    # Get the latest plan
    
    latest_plan = plans[-1]

    return latest_plan

def subscribe_patient_to_prfessional_to_clients_plan(
    patient_id: str,
    practitioner_id: str,
    start_date: str,
    end_date: str,
    plan_definition_id: Optional[str] = None,
    plan_version: Optional[str] = None,
    billing_metadata: Optional[Dict] = None,
) -> Dict:
    """
    Subscribe a patient to a practitioner's care plan (CarePlan resource).

    If plan_definition_id is not provided:
        - Search for the practitioner's PlanDefinition(s)
        - Use the only one found
        - Raise an error if none or more than one exist

    Args:
        patient_id (str): FHIR Patient resource ID.
        practitioner_id (str): FHIR Practitioner resource ID.
        start_date (str): ISO start date (e.g. '2025-06-01').
        end_date (str): ISO end date (e.g. '2025-12-01').
        plan_definition_id (Optional[str]): PlanDefinition ID (optional).
        plan_version (Optional[str]): Version of the plan (optional).
        billing_metadata (Optional[Dict]): Extra billing-related info to store as extensions.

    Returns:
        Dict: The created CarePlan resource as JSON.
    """
    access_token = get_access_token()
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/fhir+json",
        "Accept": "application/fhir+json",
    }

    # If plan ID not provided, auto-select the practitioner's latest plan
    if not plan_definition_id:
        plan = get_practitioner_to_clients_latest_plan_definition(practitioner_id=practitioner_id)

        if not plan:
            raise ValueError("Practitioner has no plans.")

        plan_resource = plan["resource"]
        plan_definition_id = plan_resource["id"]
        plan_version = plan_resource.get("version", "1.0")

    # Build CarePlan resource
    careplan = {
        "resourceType": "CarePlan",
        "status": "active",
        "intent": "order",
        "subject": {"reference": f"Patient/{patient_id}"},
        "author": {"reference": f"Practitioner/{practitioner_id}"},
        "period": {"start": start_date, "end": end_date},
        "instantiatesCanonical": [f"PlanDefinition/{plan_definition_id}|{plan_version}"]
    }

    # Add billing extensions
    if billing_metadata:
        careplan["extension"] = [
            {
                "url": f"http://example.com/fhir/StructureDefinition/{key}",
                "valueString": str(value)
            } for key, value in billing_metadata.items()
        ]

    # Submit CarePlan
    response = requests.post(
        f"{settings.AZURE_FHIR_SERVICE_URL}/CarePlan",
        headers=headers,
        json=careplan,
    )
    response.raise_for_status()
    return response.json()

def get_patient_active_subscriptions(
    patient_id: str
) -> List[Dict]:
    """
    Fetch active CarePlan resources for a patient.

    Args:
        patient_id (str): FHIR Patient ID.

    Returns:
        List[Dict]: List of CarePlan resources (active only).
    """
    access_token = get_access_token()
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/fhir+json",
    }

    url = f"{settings.AZURE_FHIR_SERVICE_URL}/CarePlan?subject=Patient/{patient_id}&status=active"
    response = requests.get(url, headers=headers)
    response.raise_for_status()

    bundle = response.json()
    careplans = []

    for entry in bundle.get("entry", []):
        careplans.append(entry["resource"])

    return careplans


    
# ============================================================================
# FHIR Questionnaire & QuestionnaireResponse (for quizes and assessments)
# ============================================================================

def create_questionnaire(title: str, questions: List[Dict]) -> str:
    """
    Creates a FHIR Questionnaire resource on Azure FHIR server.

    Args:
        title (str): Title of the questionnaire (e.g., "Skin Health Quiz").
        questions (List[Dict]): List of question dicts. Each dict has:
            - "q": Question text (str)
            - "options": List[Dict] of answer options, each with:
                - "text" (str)
                - "value" (str, int, bool depending on value_type)
                - "value_type" (str): One of "string", "boolean", "integer", etc.

    Returns:
        str: ID of the created Questionnaire resource.

    Raises:
        Exception: If creation fails or bad data is passed.
    """
    access_token = get_access_token()
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/fhir+json",
        "Accept": "application/fhir+json",
    }

    questionnaire_fhir_id = str(uuid.uuid4())

    items = []
    for idx, q in enumerate(questions, start=1):
        link_id = f"q{idx}"
        question_text = str(q.get("q")) # ensure str for JSON serialization
        options = q.get("options", [])
        
        if not question_text or not isinstance(options, list):
            raise ValueError(f"Invalid question format at index {idx-1}")
        
        item = {
            "linkId": link_id,
            "text": str(question_text), # ensure str for JSON serialization
            "type": "choice",
            "answerOption": []
        }

        for option in options:
            value_type = option.get("value_type")
            value = option.get("value")
            if value_type not in ["string", "boolean", "integer"]:
                raise ValueError(f"Unsupported value_type '{value_type}' in question '{question_text}'")

            fhir_key = f"value{value_type.capitalize()}"
            item["answerOption"].append({
                fhir_key: value,
                "extension": [
                    {
                        "url": "http://hl7.org/fhir/StructureDefinition/label",
                        "valueString": str(option.get("text", str(value)))  # ensure str for JSON serialization
                    }
                ]
            })

        items.append(item)

    questionnaire_resource = {
        "resourceType": "Questionnaire",
        "id": questionnaire_fhir_id,
        "title": str(title), # ensure str for JSON serialization
        "status": "active",
        "subjectType": ["Patient"],
        "item": items
    }

    response = requests.put(
        f"{settings.AZURE_FHIR_SERVICE_URL}/Questionnaire/{questionnaire_fhir_id}",
        json=questionnaire_resource,
        headers=headers
    )
    if response.status_code not in [200, 201]:
        raise Exception(f"Failed to create Questionnaire: {response.status_code} {response.text}")

    return questionnaire_fhir_id

def delete_questionnaire(title: str) -> dict:
    """
    Delete a Questionnaire resource identified by its unique title.

    Args:
        title (str): The unique title of the Questionnaire.

    Returns:
        dict: A dictionary containing the deletion status or confirmation.

    Raises:
        ValueError: If the Questionnaire is not found or multiple are found.
        requests.HTTPError: If the delete operation fails.
    """
    access_token = get_access_token()
    search_url = f"{settings.AZURE_FHIR_SERVICE_URL}/Questionnaire?title={title}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/fhir+json",
        "Content-Type": "application/fhir+json"
    }

    response = requests.get(search_url, headers=headers)
    response.raise_for_status()
    bundle = response.json()

    entries = bundle.get("entry", [])
    if not entries:
        raise ValueError("No Questionnaire found with the given title.")
    if len(entries) > 1:
        raise ValueError("Multiple Questionnaires found with the given title. Titles must be unique.")

    questionnaire_id = entries[0]["resource"]["id"]

    delete_url = f"{settings.AZURE_FHIR_SERVICE_URL}/Questionnaire/{questionnaire_id}"
    delete_response = requests.delete(delete_url, headers=headers)
    delete_response.raise_for_status()

    return "deleted"

def deactivate_questionnaire(title: str) -> dict:
    """
    Deactivate a Questionnaire by setting its status to 'inactive', found via title.

    Args:
        title (str): The unique title of the Questionnaire.

    Returns:
        dict: The updated Questionnaire resource.

    Raises:
        ValueError: If the Questionnaire is not found or multiple are found.
        requests.HTTPError: If the update fails.
    """
    access_token = get_access_token()
    search_url = f"{settings.AZURE_FHIR_SERVICE_URL}/Questionnaire?title={title}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/fhir+json",
        "Content-Type": "application/fhir+json"
    }

    response = requests.get(search_url, headers=headers)
    response.raise_for_status()
    bundle = response.json()

    entries = bundle.get("entry", [])
    if not entries:
        raise ValueError("No Questionnaire found with the given title.")
    if len(entries) > 1:
        raise ValueError("Multiple Questionnaires found with the given title. Titles must be unique.")

    questionnaire = entries[0]["resource"]
    questionnaire_id = questionnaire["id"]
    questionnaire["status"] = "inactive"

    update_url = f"{settings.AZURE_FHIR_SERVICE_URL}/Questionnaire/{questionnaire_id}"
    update_response = requests.put(update_url, json=questionnaire, headers=headers)
    update_response.raise_for_status()

    return update_response.json()


def get_questionnaire(title: str):
    """
    Check if a FHIR Questionnaire exists by its title.

    Args:
        title (str): The title of the Questionnaire to search for.

    Returns:
        dict | None: The Questionnaire resource as a dictionary if found, otherwise None.

    Raises:
        ValueError: If multiple Questionnaires are found with the same title.
        requests.HTTPError: For other HTTP errors.
    """
    access_token = get_access_token()
    search_url = f"{settings.AZURE_FHIR_SERVICE_URL}/Questionnaire?title={title}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/fhir+json"
    }

    response = requests.get(search_url, headers=headers)
    response.raise_for_status()

    bundle = response.json()
    entries = bundle.get("entry", [])

    if not entries:
        return None
    if len(entries) > 1:
        raise ValueError("Multiple Questionnaires found with the given title. Title must be unique.")

    return entries[0]["resource"]

def get_questionnaire_questions_as_js_list(questionnaire_json: dict) -> list:
    """
    Extract questions and options from the Questionnaire resource JSON.

    Returns a list like:
    [
      {
        "q": question_text,
        "options": [
          {"text": option_text, "value": integer_value},
          ...
        ]
      },
      ...
    ]
    """
    quiz_questions = []

    if not questionnaire_json:
        return quiz_questions

    for item in questionnaire_json.get("item", []):
        question_text = item.get("text") or item.get("linkId") or ""
        options = []

        # Assuming answerOption holds options with 'valueInteger' and 'valueString'
        for answer_option in item.get("answerOption", []):
            text = answer_option.get("extension")[0]["valueString"]
            # Prefer integer if exists, fallback to string converted to int if possible
            if "valueInteger" in answer_option:
                value = answer_option["valueInteger"]
            elif "valueString" in answer_option:
                try:
                    value = int(answer_option["valueString"])
                except ValueError:
                    value = answer_option["valueString"]
            else:
                value = None

            options.append({"text": text, "value": value})

        quiz_questions.append({"q": question_text, "options": options})

    return quiz_questions


def create_questionnaire_response(practitioner_id: str, patient_id: str, question_answers: list[dict]) -> dict:
    """
    Create a FHIR QuestionnaireResponse at Azure FHIR server (raw JSON version).

    Args:
        practitioner_id (str): Practitioner ID (e.g., "practitioner-123")
        patient_id (str): Patient ID (e.g., "patient-456")
        question_answers (List[dict]): List of {"linkId", "text", "answer": [{"valueX": ...}]} items

    Returns:
        dict: Azure FHIR server response
    """

    # Prepare Azure FHIR headers
    access_token = get_access_token()
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/fhir+json",
        "Content-Type": "application/fhir+json"
    }

    # Prepare references and metadata
    questionnaire_title = settings.ACTIVE_QUESTIONNAIRE_TITLE
    questionnaire_ref = f"Questionnaire/{questionnaire_title}"
    authored_time = datetime.utcnow().isoformat()

    # Build the QuestionnaireResponse JSON structure
    questionnaire_response = {
        "resourceType": "QuestionnaireResponse",
        "id": str(uuid.uuid4()),
        "status": "completed",
        "questionnaire": questionnaire_ref,
        "subject": {"reference": f"Patient/{patient_id}"},
        "author": {"reference": f"Practitioner/{practitioner_id}"},
        "authored": authored_time,
        "item": []
    }

    for qa in question_answers:
        item_entry = {
            "linkId": qa["linkId"],
            "answer": qa.get("answer", [])
        }
        questionnaire_response["item"].append(item_entry)

    

    # Send POST request to Azure FHIR
    url = f"{settings.AZURE_FHIR_SERVICE_URL}/QuestionnaireResponse"
    response = requests.post(url, headers=headers, json=questionnaire_response)

    # Raise error on failure, return JSON on success
    response.raise_for_status()
    return response.json()


def get_questionnaire_responses(practitioner_id: str, patient_id: str, questionnaire_title: str) -> list[dict]:
    """
    Retrieve QuestionnaireResponse resources from Azure FHIR server for a specific practitioner,
    patient, and questionnaire.

    Args:
        practitioner_id (str): FHIR ID of the practitioner (e.g., "practitioner-123")
        patient_id (str): FHIR ID of the patient (e.g., "patient-456")
        questionnaire_title (str): Title or identifier of the Questionnaire (e.g., "Depression-Form")

    Returns:
        List[dict]: List of QuestionnaireResponse resources (sorted by authored datetime ascedning)
    """

    access_token = get_access_token()
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/fhir+json"
    }

    # Build query parameters
    query_params = {
        "subject": f"Patient/{patient_id}",
        "author": f"Practitioner/{practitioner_id}",
        "_sort": "authored"
    }

    url = f"{settings.AZURE_FHIR_SERVICE_URL}/QuestionnaireResponse?{urlencode(query_params)}"
    response = requests.get(url, headers=headers)
    response.raise_for_status()

    bundle = response.json()
    entries = bundle.get("entry", [])

    # Client-side filtering by questionnaire identifier
    questionnaire_responses = [
        entry["resource"]
        for entry in entries
        if "resource" in entry and
        entry["resource"].get("questionnaire", "").endswith(f"/{questionnaire_title}")
    ]

    if not questionnaire_responses:
        return None

    # Keep max(CARE_CHART_MAX_N_QUESTIONNAIRES, total_returned)
    max_n = max(settings.CARE_CHART_MAX_N_QUESTIONNAIRES, len(questionnaire_responses))
    return questionnaire_responses[:max_n]