from django.shortcuts import render, redirect
from django.urls import reverse
from django.core.mail import send_mail
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.conf import settings

from django.contrib.auth.decorators import user_passes_test
from django.core.exceptions import PermissionDenied

import json
import random
from datetime import date, timedelta

from . import utils as utils
from . import forms as fms
from . import fhir as fhir
from . import questionnaires as questionnaires
from . import platform_plans


# ==============================================================================
# Views Access Management
# use with user_passes_test deocrator to limit accessing views to specific roles
# ==============================================================================

def is_admin(user):
    return user.groups.filter(name='admin').exists()

def is_professional(user):
    return user.groups.filter(name='professional').exists()

def is_admin_or_professional(user):
    return is_admin(user) or is_professional(user)

def is_client(user):
    return user.groups.filter(name='client').exists()

def is_admin_or_client(user):
    return is_admin(user) or is_client(user)

def is_professional_or_client(user): # This can be professional or client in thread
    return is_professional(user) or is_client(user)

def is_dashboard_owner(user):
    return is_admin(user) or is_professional(user) or is_client(user)

# ==============================================================================

def home_view(request):

    practitioners = [] # practitioners info to list on homepage. Empty list if try/except leads to no initiation.

    try:

        # Get all active practitioners
        practitioners = fhir.list_practitioners(only_active=True)
        # For each practitioner, add their Client's plan to their data
        
        practitioner_idxs_to_remove = [] # Remove practitioners with mising info
        for i in range(len(practitioners)):
            practitioner = practitioners[i]

            practitioner_id = practitioner["practitioner_id"]
            try:
                clients_plan_id = utils.get_professional_clients_plan_id(practitioner_id)
                clients_plan = fhir.get_plan_definition(clients_plan_id)

                # Only show practitioners with clients plan data.
                if clients_plan is None:
                    practitioner_idxs_to_remove.append(i)
                    
            except Exception as e:
                practitioner_idxs_to_remove.append(i)

            
            practitioners[i]["clients_plan"] = utils.get_professional_to_clients_plan_details_as_dict(clients_plan) # Convert FHIR format to easy to render dict

            # Add rating and n_reviews
            # TODO: replace this with real data. ! Important: for simulated data, we can't use random to avoid generating new values on refresh. instead we use (i) to set values
            rating = 5 # Give all 5 till reviews are added
            n_reviews = (i+1) * int(str(i+1)[-1]) # Example i = 24 -> n_reviews = (24 + 1) * (4) = 100
            practitioners[i]["rating"] = utils.render_rating_stars(score=rating)
            practitioners[i]["n_reviews"] = n_reviews

        # Keep only professionals (practitioners) with full info
        practitioners = [practitioner for i, practitioner in enumerate(practitioners) if i not in practitioner_idxs_to_remove]
    
    except Exception as e:
        messages.error(request, _("Error: Unable to get skincare professionals' list."))
        print(f"! Error while fetching homepage practitioners list: ", str(e))

    return render(request, 'pages/home.html', context={"professionals":practitioners})

@user_passes_test(is_dashboard_owner, login_url='/auth')
def dashboard_router_view(request):
    user = request.user
        
    if user.groups.filter(name='admin').exists():
        return redirect('admin_view')
    elif user.groups.filter(name='professional').exists():
        return redirect('professional_dashboard')
    elif user.groups.filter(name='client').exists():
        return redirect('client_dashboard')
    
def contact_us_view(request):
    if request.method == "POST":
        form = fms.ContactUsForm(request.POST)
        if form.is_valid():
            subject = form.cleaned_data['subject']
            body = form.cleaned_data['body']

            try:
                send_mail(
                    subject=subject,
                    message=body,
                    from_email=settings.CONTACT_US_FROM_EMAIL,
                    recipient_list=[settings.CONTACT_US_TO_EMAIL],
                    fail_silently=False,
                )
            except Exception as e:
                messages.error(request, _("Sorry, your message could not be sent. Please contact support. ") + str(e))
                return redirect("homepage")

            messages.success(request, _("Your message has been sent successfully."))
            return redirect("homepage")
    else:
        form = fms.ContactUsForm()

    return render(request, "pages/contact_us.html", {"form": form, "requires_crispy": True})

def auth_view(request):

    user = request.user

    if user.is_authenticated:
        return redirect('home')  # Redirect to home page if user is already authenticated

    return redirect("account_login") # Show allauth authentication

@user_passes_test(is_admin, login_url='/auth')
def admin_dashboard_view(request):
    
    clients_table_data = fhir.list_patients(practitioner_fhir_id=None, only_active=False)  # Fetch all clients (of all professionals), including deactivated ones
    practitioners_table_data = fhir.list_practitioners(only_active=False)  # Fetch all practitioners, including deactivated ones
    
    context = {
        "clients_table_data": clients_table_data,
        "practitioners_table_data": practitioners_table_data
    }
    return render(request, 'pages/admin/dashboard.html', context=context)

@user_passes_test(is_professional, login_url='/auth')
def professional_dashboard_view(request):
    professional_fhir_id = request.user.fhir_resource_id  # Get the FHIR-ID associated to logged in professional account
    
    # get professional info (e.g. name, title, etc.) to display on dashboard
    professional = fhir.get_practitioner(professional_fhir_id)

    clients_table_data = fhir.list_patients(practitioner_fhir_id=professional_fhir_id, only_active=False)  # Fetch all clients, including deactivated ones
    context = {
        "professional": professional,
        "clients_table_data": clients_table_data
    }
    return render(request, 'pages/professional/dashboard.html', context=context)


@user_passes_test(is_professional, login_url='/auth')
def quiz_start_view(request, client_fhir_id):

    # TODO: Check if there is an active PlatformToProfessionalPlan for authenticated professional , and that it has at least 1 unused checkup

    try:
        # Get the FHIR-ID associated to logged in professional account
        practitioner_fhir_id = request.user.fhir_resource_id 
        # Load professional FHIR data to render name, image, center name ..
        practitioner = fhir.get_practitioner(practitioner_fhir_id)
        patient_fhir_id = client_fhir_id

        # Load client FHIR data
        patient = fhir.get_patient(patient_fhir_id)
        if not patient:
            messages.error(request, _("Client not found."))
            raise Exception(_("Client not found."))

        # !Important: Check ownership for GET and POST. This is to ensure that the professional can only edit their own clients.
        general_practitioner_refs = [
            ref.get("reference", "") for ref in patient.get("generalPractitioner", [])
        ]
        if not any(practitioner_fhir_id in ref for ref in general_practitioner_refs):
            raise PermissionDenied("You are not authorized to edit this client.")
    except Exception as e:
            messages.error(request, f"Can't load page: {e}")
            return redirect('professional_dashboard')

    if request.method == "POST":
        
        try:
            questionnaire_title = settings.ACTIVE_QUESTIONNAIRE_TITLE
            questions = fhir.get_questionnaire(title=questionnaire_title)

            n_questions = len(questions)

            question_answers = []

            # Re-shape submitted form questoin_answers key-values to fit FHIR QuestionnaireResponse resource creation
            for i in range(n_questions):
                field_index = i
                field_name = f"q{field_index}"
                answer = request.POST.get(field_name)

                value_type = "integer" #parsed.get("value_type", "string")
                value = int(answer) #parsed.get("value")

                # Map to FHIR's valueX format
                fhir_value_key = f"value{value_type.capitalize()}"
                answer_entry = {
                    "linkId": str(field_index + 1),
                    #"text": question["q"],
                    "answer": [{fhir_value_key: value}]
                }

                question_answers.append(answer_entry)

            response = fhir.create_questionnaire_response(
                practitioner_id=practitioner_fhir_id,
                patient_id=patient_fhir_id,
                question_answers=question_answers
            )
            messages.success(request, _("Your quiz was successfully submitted."))
            return redirect(reverse("care_chart", args=[patient_fhir_id])) # Redirect to care_chart of the client to display progress
        except Exception as e:
            messages.error(request, f"Submission failed: {e}")
            return redirect('professional_dashboard') # TODO: change to better redirect. e.g. Professional -> client file page


    else: # GET
        # Fetch active quiz quesions and options to return in context for rendering
        try:
            questionnaire_title = settings.ACTIVE_QUESTIONNAIRE_TITLE

            # Get questions and choices from questionnaires.py. Although quiz is populated as Qestionnaire FHIR resource, we load this from 
            # questionnaires.py file (from which we populate initially) to minimize calls to FHIR.
            questionnaire_json = fhir.get_questionnaire(questionnaire_title)

            # Convrert questions to JS list for front-end rendering
            quiz_questions = fhir.get_questionnaire_questions_as_js_list(questionnaire_json)
 
        except Exception as e:
            messages.error(request, _("Failed to load quiz: Please contact support. ") + str(e))


        context = {
            "professional": practitioner,
            "client": patient,
            "quiz_questions_json": json.dumps(quiz_questions, ensure_ascii=False)
        }

        return render(request, 'pages/quiz_start.html', context=context)

@user_passes_test(is_professional_or_client, login_url='/auth')
def care_chart_view(request, client_id):

    try:
        # Get the FHIR-ID associated to logged in professional account
        practitioner_fhir_id = request.user.fhir_resource_id 
        # Load professional FHIR data to render name, image, center name ..
        practitioner = fhir.get_practitioner(practitioner_fhir_id)
        patient_fhir_id = client_id

        # Load client FHIR data
        patient = fhir.get_patient(patient_fhir_id)
        if not patient:
            messages.error(request, _("Client not found."))
            raise Exception(_("Client not found."))

        # !Important: Check ownership for GET and POST. This is to ensure that the professional can only edit their own clients.
        general_practitioner_refs = [
            ref.get("reference", "") for ref in patient.get("generalPractitioner", [])
        ]
        if not any(practitioner_fhir_id in ref for ref in general_practitioner_refs):
            raise PermissionDenied("You are not authorized to edit this client.")
    
    except Exception as e:
            messages.error(request, f"Can't load page: {e}")
            return redirect('professional_dashboard')

    try:
        # Get quiz submissions
        questionnaire_title = settings.ACTIVE_QUESTIONNAIRE_TITLE
        sorted_submissions = fhir.get_questionnaire_responses(
            practitioner_id=practitioner_fhir_id,
            patient_id=client_id,
            questionnaire_title=questionnaire_title
        )

        if sorted_submissions is None:
            raise Exception(_("No submissions found for specified professional, client, and quiz."))
        
        # Create JS Data needed to render chart
        questionnaire_questions = questionnaires.get_questionnaire(questionnaire_title=questionnaire_title)
        care_chart_js_data = utils.create_care_chart_js_data(sorted_submissions=sorted_submissions, questionnaire_questions=questionnaire_questions)

        context = {
            "professional": practitioner,
            "client": patient,
            "care_chart_js_data": care_chart_js_data
        }
    
    except Exception as e:
        messages.error(request, _("Failed to load page: Please contact support. ") + str(e))
        return redirect('professional_dashboard')

    return render(request, 'pages/client/care_chart.html', context=context)

@user_passes_test(is_admin, login_url='/auth')
def client_dashboard_view(request):

    try:
        # Get authenticated client FHIR ID
        client_fhir_id = request.user.fhir_resource_id  # Get the FHIR-ID associated to logged in client
        
        # Get client info (e.g. name, title, etc.) to display on dashboard
        client = fhir.get_patient(client_fhir_id).get("resource")
        client_fhir_id = client.id
        
        # Get linked professional info (e.g. name, Whatsapp number for messaging)
        linked_professional_fhir_id = client["general_practitioner"][0]["reference"].split("/")[-1]  # Extract FHIR ID from reference
        professional = fhir.get_practitioner(linked_professional_fhir_id).get("resource")

        # Get care chart data
        # Get quiz submissions for this client that are subimtted by curreent linked professional
        questionnaire_title = settings.ACTIVE_QUESTIONNAIRE_TITLE
        sorted_submissions = fhir.get_questionnaire_responses(
            practitioner_id=linked_professional_fhir_id,
            patient_id=client_fhir_id,
            questionnaire_title=questionnaire_title
        )

        if sorted_submissions is None:
            raise Exception(_("No submissions found for specified professional, client, and quiz."))
        
        # Create JS Data needed to render chart
        questionnaire_questions = questionnaires.get_questionnaire(questionnaire_title=questionnaire_title)
        care_chart_js_data = utils.create_care_chart_js_data(sorted_submissions=sorted_submissions, questionnaire_questions=questionnaire_questions)


        context = {
            "client_fhir_id": client_fhir_id,
            "client": client,
            "professional_fhir_id": linked_professional_fhir_id,
            "professional": professional,
            "care_chart_js_data": care_chart_js_data
        }

        return render(request, 'pages/client/dashboard.html', context=context)
    except Exception as e:
        messages.error(request, _("Failed to load page: Please contact support. ") + str(e))
        return redirect("home_view")

@user_passes_test(is_professional_or_client, login_url='/auth')
def messages_view(request, receiver_whatsapp_number):
    return render(request, 'pages/messages.html', context={"receiver_whatsapp_number": receiver_whatsapp_number})


# =========================================
# Admin-Related Views
# =========================================
@user_passes_test(is_admin, login_url='/auth')
def quiz_populate_view(request):
    """
    This view is used to populate the quiz with initial / new data.
    It should only be accessible by admin users.
    """
    if request.method == "POST":
        # Here you would handle the form submission and populate the quiz data
        new_questionnaire_title = settings.ACTIVE_QUESTIONNAIRE_TITLE
        try:
            questions = questionnaires.get_questionnaire(new_questionnaire_title)
            qestionnaire_fhir_id = fhir.create_questionnaire(
                title = settings.ACTIVE_QUESTIONNAIRE_ID,
                questions = questions         
            )
            # For now, we'll just simulate a success message
            messages.success(request, _(f"Quiz {new_questionnaire_title} successfully populate with Questionnaire FHIR ID: {qestionnaire_fhir_id}"))
        except Exception as e:
            messages.error(request, _("Failed to populate quiz: Please contact support. " + str(e)))

        # Redirect to the admin dashboard or another appropriate page
        return redirect('admin_view')
    
    else:
        # If the request is GET, we return the new_questionnaire_title in context to display for confirmation.
        
        pass
    
    # Render the form for populating the quiz
    return render(request, 'pages/admin/quiz_populate_to_fhir.html', {"new_questionnaire_title": new_questionnaire_title, "requires_crispy": True})


@user_passes_test(is_admin, login_url='/auth')
def quiz_deactivate_view(request, questionnaire_title):
    """
    This view is used to populate the quiz with initial / new data.
    It should only be accessible by admin users.
    """
    if request.method == "POST":
        
        try:
            fhir.deactivate_questionnaire(questionnaire_title)
            # For now, we'll just simulate a success message
            messages.success(request, _(f"Quiz {questionnaire_title} successfully deactivated."))
        except Exception as e:
            messages.error(request, _("Failed to populate quiz: Please contact support. " + str(e)))

        # Redirect to the admin dashboard or another appropriate page
        return redirect('admin_view')
    
    else:
        # If the request is GET, we return the settings.ACTIVE_QUESTIONNAIRE_ID for confirmation.
        
        pass
    
    # Render the form for populating the quiz
    return render(request, 'pages/admin/quiz_populate_to_fhir.html', {"qestionnaire_title": questionnaire_title, "requires_crispy": True})

# =========================================
# Professional-Related Views
# =========================================

@user_passes_test(is_admin, login_url='/auth')
def create_professional_view(request):
    if request.method == "POST":
        form = fms.SkincareProfessionalForm(request.POST, is_edit=False)  # is_edit=False -> add Email field
        if form.is_valid():
            try:
                fhir.create_practitioner(**form.cleaned_data)
                messages.success(request, _("Professional successfully created."))
                return redirect('admin_view')
            except Exception as e:
                messages.error(request, _("Failed to create professional: Please contact support" + str(e)))
    else:
        form = fms.SkincareProfessionalForm(is_edit=False)  # is_edit=False -> add Email field
    return render(request, "pages/professional/create_professional.html", {"form": form, "requires_crispy": True})


@user_passes_test(is_admin_or_professional, login_url='/auth')
def edit_professional_view(request, practitioner_id):

    # Deny professional from editiing another professional profile data
    user = request.user
    if user.groups.filter(name='admin').exists():
        pass # allow to edit profile with any passed practitioner_id

    # Check if user is in 'professional' group
    elif user.groups.filter(name='professional').exists():
        if user.fhir_resource_id != practitioner_id:
            raise PermissionDenied
        
    if request.method == "POST":
        form = fms.SkincareProfessionalForm(request.POST, is_edit=True)
        if form.is_valid():
            try:
                fhir.edit_practitioner(practitioner_fhir_id=practitioner_id, updates=form.cleaned_data)
                messages.success(request, _("Professional successfully updated."))
                return redirect(reverse('edit_professional', args=[practitioner_id]))
            except Exception as e:
                messages.error(request, _("Failed to update professional: Please contact support" + str(e)))
    else:
        # You’d load existing data here
        try:
            practitioner = fhir.get_practitioner(practitioner_id)
            if not practitioner:
                messages.error(request, _("Professional not found."))
                return redirect('admin_view')
            # Initialize form with existing data

            telecom = practitioner.get("telecom", [])
            phone_number = ""
            if len(telecom) > 0:
                phone_number = telecom[0].get("value", "")
            whatsapp_link, whatsapp_number = "", ""
            if len(telecom) > 1:
                whatsapp_link = telecom[1].get("value", "")
                if not whatsapp_link == "":
                    whatsapp_number = whatsapp_link.split("https://wa.me/")[-1]  # Extract number from WhatsApp link
                
            initial_fields = {
                'title': practitioner.get('name', [{}])[0].get('prefix', [''])[0],
                'first_name': practitioner.get('name', [{}])[0].get('given', [''])[0],
                'last_name': practitioner.get('name', [{}])[0].get('family', ''),
                'gender': practitioner.get('male', ''),
                'organization_name': practitioner.get('address', [{}])[0].get('text', ''),
                'organization_city': practitioner.get('address', [{}])[0].get('city', ''),
                'organization_country': practitioner.get('address', [{}])[0].get('country', ''),
                'phone_number': phone_number,
                'whatsapp_number': whatsapp_number,
                'photo_url': practitioner.get('photo', [{}])[0].get('url', ''),
            }
            form = fms.SkincareProfessionalForm(initial=initial_fields, is_edit=True) # is_edit=True -> remove Email field
        except Exception as e:
            messages.error(request, _("Failed to load professional data: Please contact support" + str(e)))
        
    return render(request, "pages/professional/edit_professional.html", {"form": form, "requires_crispy": True})


@user_passes_test(is_admin, login_url='/auth')
def deactivate_professional_view(request, practitioner_id):
    if request.method == "POST":
        try:
            fhir.deactivate_practitioner(practitioner_id)
            messages.success(request, _("Professional successfully deactivated."))
        except Exception as e:
            messages.error(request, _("Failed to deactivate professional: Please contact support" + str(e)))
        return redirect('admin_view')
    return render(request, "pages/professional/confirm_deactivation.html", {"practitioner_id": practitioner_id, "requires_crispy": True})


@user_passes_test(is_admin, login_url='/auth')
def activate_professional_view(request, practitioner_id):
    if request.method == "POST":
        try:
            fhir.activate_practitioner(practitioner_id)
            messages.success(request, _("Professional successfully activated."))
        except Exception as e:
            messages.error(request, _("Failed to activate professional: Please contact support" + str(e)))
        return redirect('admin_view')
    return render(request, "pages/professional/confirm_activation.html", {"practitioner_id": practitioner_id, "requires_crispy": True})

@user_passes_test(is_admin, login_url='/auth')
def professional_subscription_view(request, practitioner_id):

    user = request.user

    if request.method == 'POST':
        form = fms.ProfessionalSubscriptionForm(request.POST)

        if form.is_valid():
            submitted_data = form.cleaned_data.copy()


            try:
                plan_title = submitted_data["plan_title"]
                plan_id = plan_title # plan title carries the plan ID in value

                voucher_code = submitted_data["voucher"]
                if not voucher_code == "" and not voucher_code is None:
                    voucher = {
                        "code": platform_plans.vouchers[voucher_code]["code"],
                        "display": platform_plans.vouchers[voucher_code]["display"]
                    }
                else:
                    voucher = None

                plan_dict = platform_plans.platform_plans[plan_id] 

                period_start_date = date.today().strftime("%Y-%m-%d")
                period_length_in_days = plan_dict["length_in_days"]
                period_end_date = date.today() + timedelta(days=period_length_in_days)
                period_end_date = period_end_date.strftime("%Y-%m-%d")

                paid_amount = submitted_data["paid_amount"] # becareful not to get default payment value (VOUCHER could be applied)
                
                # Create subscription
                practitioner_role = fhir.subscribe_professional_to_platform_plan(
                    deactivate_existing_subscription=True, # Always deactivate previous ones. No extend logic for MVP
                    plan_definition_id=plan_title, # For the PlatformToProfessional PlanDefinition, id and title are set identical
                    assigner_django_user_id=user.id,
                    practitioner_id=practitioner_id,
                    start_date=period_start_date,
                    end_date=period_end_date,
                    paid_amount=paid_amount,
                    voucher=voucher
                )
                
                practitioner_role_id = practitioner_role["id"]

                # Save assignment ID (PractitionerRole ID) to professional Django user to minimize FHIR queries
                utils.set_professional_platform_plan_id(professional_fhir_id=practitioner_id, plan_fhir_id=practitioner_role_id)

                messages.success(request, _("Subscription created successfully."))
                return redirect('admin_view')
            except Exception as e:
                messages.error(request, _("Failed to subscripe professional to plan: ") + str(e))
    else:
            
        form = fms.ProfessionalSubscriptionForm()

    context = {
        'form': form,
        "requires_crispy": True,
        'practitioner_id': practitioner_id,
    }

    return render(request, 'pages/professional/subscription_management.html', context)




@user_passes_test(is_admin_or_professional, login_url='/auth')
def professional_plan_to_clients_view(request, practitioner_id: str):
    user = request.user
    resource_fhir_id = getattr(user, 'resource_fhir_id', None)

    # Authorization check
    if not is_admin(user) and resource_fhir_id != practitioner_id:
        raise PermissionDenied(_("You are not allowed to edit another professional’s plan."))

    # Load current plan if any
    current_plan_id = utils.get_professional_clients_plan_id(practitioner_id)
    if current_plan_id == "":
        current_plan = None

    current_plan = fhir.get_plan_definition(plan_definition_fhir_id=current_plan_id, only_latest=True)

    current_plan_dict = utils.get_professional_to_clients_plan_details_as_dict(current_plan)
    

    if request.method == 'POST':
        form = fms.ProfessionalPlanForm(request.POST)

        if form.is_valid():
            submitted_data = form.cleaned_data.copy()
            current_plan_dict = {
                "n_monthly_questions": fms.UNLIMITED_REPRESENTAION, # For MVP it's always unlimited, later: submitted_data["n_monthly_questions"],
                "n_monthly_flagged_questions": fms.UNLIMITED_REPRESENTAION, # For MVP it's always unlimited, later: submitted_data["n_monthly_flagged_questions"],
                "usually_replies_in": submitted_data["usually_replies_in"],
                "checkup_frequency": submitted_data["checkup_frequency"],
                "monthly_price": submitted_data["monthly_price"]
            }

            try:
                # Only create, No edit for plan definitions. This is to protect clietns by keeping them assigned to the previously created plan definition (if exists) 
                new_plan = fhir.create_plan_definition(
                    plan_definition_type=fhir.PlanDefinitionType.PROFESSIONAL_TO_CLIENTS_PLAN,
                    author_id=practitioner_id,
                    creator_django_user_id=user.id,
                    title="ProfessionalToClientPlan",
                    plan_details=current_plan_dict,
                    description="",
                    version="1.0"
                )

                # Add Django user field to minimize FHIR queries
                new_plan_id = new_plan["id"]
                utils.set_professional_clients_plan_id(practitioner_id, new_plan_id)

                messages.success(request, _("Plan created successfully."))
                return redirect('professional_clients_plan', practitioner_id=practitioner_id)
            except Exception as e:
                messages.error(request, _("Failed to create plan: ") + str(e))
    else:
        # Pre-fill form with existing title if available
        if current_plan:
            form = fms.ProfessionalPlanForm(initial=current_plan_dict)
        else:
            form = fms.ProfessionalPlanForm()

    context = {
        'form': form,
        "requires_crispy": True,
        'active_plan': current_plan,  # Placeholder to render plan details later
        'practitioner_id': practitioner_id,
    }

    return render(request, 'pages/professional/clients_plan.html', context)

# =========================================
# Client-Related Views
# =========================================

@user_passes_test(is_professional, login_url='/auth')
def create_client_view(request):
    if request.method == "POST":
        form = fms.SkincareClientForm(request.POST, is_edit=False)  # Adjust form and params as needed
        if form.is_valid():
            try:
                # Pass practitioner_id explicitly for patient association
                practitioner_id = request.user.fhir_resource_id # Get the FHIR-ID associated to logged in professional account
                fhir.create_patient(practitioner_fhir_id=practitioner_id, **form.cleaned_data)
                messages.success(request, _("Client successfully created."))
                return redirect('professional_dashboard')
            except Exception as e:
                messages.error(request, _("Failed to create client: Please contact support. " + str(e)))
    else:
        form = fms.SkincareClientForm(is_edit=False)  # Adjust form param as needed

    return render(request, "pages/client/create_client.html", {"form": form, "requires_crispy": True})


@user_passes_test(is_professional, login_url='/auth')
def edit_client_view(request, client_id):
    user = request.user
    professional_fhir_id = user.fhir_resource_id

    try:
        patient = fhir.get_patient(client_id)
        if not patient:
            messages.error(request, _("Client not found."))
            return redirect('professional_dashboard')

        # !Important: Check ownership. This is to ensure that the professional can only edit their own clients.
        general_practitioner_refs = [
            ref.get("reference", "") for ref in patient.get("generalPractitioner", [])
        ]
        if not any(professional_fhir_id in ref for ref in general_practitioner_refs):
            raise PermissionDenied("You are not authorized to edit this client.")

    except Exception as e:
        messages.error(request, _("Failed to load client data: Please contact support. " + str(e)))
        return redirect('professional_dashboard')

    if request.method == "POST":
        form = fms.SkincareClientForm(request.POST, is_edit=True)
        if form.is_valid():
            try:
                fhir.edit_patient(patient_fhir_id=client_id, updates=form.cleaned_data)
                messages.success(request, _("Client successfully updated."))
                return redirect('professional_dashboard')
            except Exception as e:
                messages.error(request, _("Failed to update client: Please contact support. " + str(e)))
    else:
        # Pre-fill form with current client data

        telecom = patient.get("telecom", [])
        phone_number = ""
        if len(telecom) > 0:
            phone_number = telecom[0].get("value", "")
        whatsapp_link, whatsapp_number = "", ""
        if len(telecom) > 1:
            whatsapp_link = telecom[1].get("value", "")
            if not whatsapp_link == "":
                whatsapp_number = whatsapp_link.split("https://wa.me/")[-1]  # Extract number from WhatsApp link

        initial_fields = {
            'title': patient.get('name', [{}])[0].get('prefix', [''])[0],
            'first_name': patient.get('name', [{}])[0].get('given', [''])[0],
            'last_name': patient.get('name', [{}])[0].get('family', ''),
            'gender': patient.get('gender', ''),
            'birth_date': patient.get('birthDate', ''),
            'phone_number': phone_number,
            'whatsapp_number': whatsapp_number,
            'phone_number': patient.get('telecom', [{}])[0].get('value', ''),
        }
        form = fms.SkincareClientForm(initial=initial_fields, is_edit=True)

    return render(request, "pages/client/edit_client.html", {"form": form, "requires_crispy": True})


@user_passes_test(is_admin, login_url='/auth') # No need to check Professional-> Client Entry ownership, as only admin can deactivate/activate clients
def deactivate_client_view(request, client_id):
    if request.method == "POST":
        try:
            fhir.deactivate_patient(client_id)
            messages.success(request, _("Client successfully deactivated."))
        except Exception as e:
            messages.error(request, _("Failed to deactivate client: Please contact support. " + str(e)))
        return redirect('professional_dashboard')
    
    return render(request, "pages/client/confirm_deactivation.html", {
        "patient_id": client_id,
        "requires_crispy": True
    })


@user_passes_test(is_admin, login_url='/auth') # No need to check Professional-> Client Entry ownership, as only admin can deactivate/activate clients
def activate_client_view(request, client_id):
    if request.method == "POST":
        try:
            fhir.activate_patient(client_id)
            messages.success(request, _("Client successfully activated."))
        except Exception as e:
            messages.error(request, _("Failed to activate client: Please contact support. " + str(e)))
        return redirect('professional_dashboard')
    
    return render(request, "pages/client/confirm_activation.html", {
        "patient_id": client_id,
        "requires_crispy": True
    })
