import os
from django.conf import settings
from django.core.exceptions import DisallowedHost
from django.utils.deprecation import MiddlewareMixin

class FlexibleAllowedHostsMiddleware(MiddlewareMixin):
    
    def process_request(self, request):

        host = request.get_host().split(":")[0]  # Remove port if any

        if settings.IS_PRODUCTION:

            aca_env_base_domain = os.environ.get("AZURE_ACA_ENV_BASE_DOMAIN", "") # GET Azure ACA Env base domain e.g. "gentlepebble-a32f39d6.eastus2.azurecontainerapps.io"
            if aca_env_base_domain == "":
                raise Exception("Cannot run on production with empty AZURE_ACA_ENV_BASE_DOMAIN env var")

            if host == aca_env_base_domain or host.endswith("." + aca_env_base_domain): # Allow all subdomains of AZURE_ACA_ENV_BASE_DOMAIN
                return  # Allow

            if host in os.environ.get("PRODUCTION_ALLOWED_HOSTS", "").split(","): # Allow all ALLOWED HOSTS passed by env var
                return  # Allow others you want

            raise DisallowedHost(f"Host '{host}' not allowed.")
        
        else: # DEV

            if host in settings.ALLOWED_HOSTS:
                return  # Allow DEV allowed hosts

            raise DisallowedHost(f"Host '{host}' not allowed.")