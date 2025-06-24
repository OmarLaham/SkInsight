from django.conf import settings

from . import questionnaires
from . import platform_plans
from . import fhir

# Populate active quiz as Questionnaire FHIR resource on app startup if not populated
# This is to create QuestionnaireResponses FHIR resources (quiz form submits) that are linked to Questionnaire and ensure compliant FHIR.
# However, when loading quiz_page, the questions will be loaded from file questionnaires.py (from which we populate initially) to minimize calls to FHIR
def init_quiz_questionnaire_fhir_resource():
    
    print("> Populate active quiz as Questionnaire FHIR resource on app startup if not populated..")
    new_questoinnaire_title = settings.ACTIVE_QUESTIONNAIRE_TITLE
    if new_questoinnaire_title is None:
        print("\t- No active questionnnaire ID provided to populate. No quiz will be populated.")
    else:
        try:

            # TODO: remove for production
            DELETE_DUPLICATE_QUESTIONNAIRE = False
            if DELETE_DUPLICATE_QUESTIONNAIRE:
                try:
                    print("\t- Delete existing questionnaire with same title..")
                    fhir.delete_questionnaire(new_questoinnaire_title)
                    print("\t- Deleted successfully")
                except Exception as e:
                    print("Failed to delete existing quiz: " + str(e))
            

            # Check if questionnaire with already populated as FHIR resource
            print("\t- Check if quiz with title exists..")
            questionnaire = fhir.get_questionnaire(new_questoinnaire_title)

            if questionnaire is None: # If not populated as FHIR resource -> Create FHIR resource

                print("\t- A Questionnaire with the same title has not been populated to FHIR server. will create FHIR resource..")
                questions = questionnaires.get_questionnaire(new_questoinnaire_title)
                
                print("\t- Create questionnaire FHIR resource..")
                
                questionnaire_fhir_id = fhir.create_questionnaire(title=new_questoinnaire_title, questions=questions)
                print(f"\t- Successfully Created {{new_questionnaire_title}} quiz as Questionnaire FHIR resource with ID: {questionnaire_fhir_id}")

            else: # If questionnnaire is already populated as FHIR resource
                print("\t- A Questionnaire with the same title has already been populated as questionnaire FHIR resource.")
                print("\t- Aborted questtionnaire FHIR resource creation.")

        except Exception as e:
            print("Failed to populate quiz: " + str(e))


# Initialize platform plans (e.g. Basic, Standard, Premium)
def init_platform_plans():

    print("> Populate platform plans as PlanDefinition(s) FHIR resource on app startup if not populated..")

    try:

        # Get existing plans
        platform_plans_fhir_ids = platform_plans.platform_plans.keys()
        existing_plans = fhir.get_platform_plan_definitions(plan_fhir_ids=platform_plans_fhir_ids)
        
        if existing_plans:

            print(f"\t- {len(existing_plans)} existing platform plans with IDs:", [plan["id"] for plan in existing_plans])

            # TODO: remove for production
            DELETE_EXISTING_PLANS = False
            if DELETE_EXISTING_PLANS:
                try:
                    print("\t- Delete existing platform plans..")
                    for plan in existing_plans:
                        plan_id = plan["id"]
                        plan_title = plan["title"]
                        fhir.delete_plan_definition(plan_definition_id=plan_id)
                        print(f"\t- Deleted plan {plan_title} successfully")
                    
                except Exception as e:
                    print("\t ! Failed to delete existing plan: " + str(e))
        
            else: # If plan is already populated as FHIR resource
                print("\t- One of more platform plans have already been populated as PlanDefinition FHIR resource(s).")
                print("\t- Aborted PlanDefinition FHIR resource creation.")
                return

        print("\t- Create platform plan(s) PlanDefinition FHIR resource(s)..")

        author_id = settings.PLATFORM_ADMIN_FHIR_ID # On startup there is no logged in user, so we use platform admin FHIR ID
        creator_django_user_id = 0

        existing_plans = platform_plans.platform_plans
        for plan_title, plan_details in existing_plans.items():
            plan_id = fhir.create_plan_definition(
                plan_definition_type=fhir.PlanDefinitionType.PLATFORM_TO_PROFESSIONALS_PLAN,
                author_id= author_id, 
                creator_django_user_id=creator_django_user_id,
                title=plan_title,
                description=plan_title,
                plan_details=plan_details
            )
            print(f"\t- Successfully Created {plan_title} plan as PlanDefinition FHIR resource with ID: {plan['id']}")
        
        print("\t- Successfully populated all platform plans as PlanDefinition FHIR resources.")


    except Exception as e:
        print("Failed to populate platform plan: " + str(e))