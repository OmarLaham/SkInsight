from django.apps import AppConfig
from django.conf import settings

class CoreAppConfig(AppConfig):
    name = 'core'

    def ready(self):

        from . import startup

        # TODO: uncomment for production
        #startup.init_quiz_questionnaire_fhir_resource()
        
        # TODO uncomment for production
        # startup.init_platform_plans()