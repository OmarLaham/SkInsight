from django.conf import settings

from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit

from phonenumber_field.formfields import PhoneNumberField


from django.utils.translation import gettext_lazy as _

from . import platform_plans

# Add this form to force Outh login in settings.py
class SignInDummyForm(forms.Form):
    pass


UNLIMITED_REPRESENTAION = settings.UNLIMITED_NUMBER_REPRESENTAION  # You can handle this as a special case in your logic

class SkincareProfessionalForm(forms.Form):
    title = forms.CharField(label=_("Title"), max_length=10)
    first_name = forms.CharField(label=_("First Name"), max_length=50)
    last_name = forms.CharField(label=_("Last Name"), max_length=50)
    gender = forms.ChoiceField(label=_("Gender"), choices=[('male', _('Male')), ('female', _('Female'))])
    organization_name = forms.CharField(label=_("Organization Name"), max_length=100)
    organization_city = forms.CharField(label=_("Organization City"), max_length=100)
    organization_country = forms.CharField(label=_("Organization Country"), max_length=100)
    phone_number = PhoneNumberField(label=_("Phone number"), required=True)
    whatsapp_number = PhoneNumberField(label=_("Whatsapp number"), required=True)
    photo_url = forms.URLField(label=_("Photo URL"), required=False)
    # practitioner_id = forms.CharField(widget=forms.HiddenInput(), required=False)  # for edit/deactivate


    def __init__(self, *args, is_edit, **kwargs): # Use is_edit to determine if this is for for creating or editing, the adding the "email" field or not
        super().__init__(*args, **kwargs)

        if not is_edit:
            self.fields['email'] = forms.EmailField(label=_("Email"), max_length=100)

        # Crispy Forms settings
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.add_input(Submit('submit', _('Submit')))


class SkincareClientForm(forms.Form):
    title = forms.CharField(label=_("Title"), max_length=10)
    first_name = forms.CharField(label=_("First Name"), max_length=100)
    last_name = forms.CharField(label=_("Last Name"), max_length=100)
    gender = forms.ChoiceField(label=_("Gender"), choices=[('male', _('Male')), ('female', _('Female'))])
    birth_date = forms.DateField(label=_("Birth Date"), widget=forms.DateInput(attrs={'type': 'date'}))
    #address = forms.CharField(label=_("Address"), max_length=200, required=False)
    #city = forms.CharField(label=_("City"), max_length=100, required=False)
    #country = forms.CharField(label=_("Country"), max_length=100, required=False)
    phone_number = PhoneNumberField(label=_("Phone number"), required=True)
    whatsapp_number = PhoneNumberField(label=_("Whatsapp number"), required=True)

    def __init__(self, *args, is_edit, **kwargs):
        super().__init__(*args, **kwargs)

        if not is_edit:
            self.fields['email'] = forms.EmailField(label=_("Email"), max_length=100, required=True)

        # Crispy Forms settings
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.add_input(Submit('submit', _('Submit')))


class ProfessionalPlanForm(forms.Form):

    # Disabled for MVP
    # n_monthly_questions = forms.IntegerField(
    #     label=_("Monthly Questions"),
    #     required=True,
    #     help_text=_(f"Use {UNLIMITED_REPRESENTAION} to indicate unlimited."),
    # )

    # n_monthly_flagged_questions = forms.IntegerField(
    #     label=_("Monthly Flagged Questions"),
    #     required=True,
    #     help_text=_("Use -1 to indicate unlimited."),
    # )

    usually_replies_in = forms.ChoiceField(
        label=_("Usually Replies In"),
        choices=[
            ('', _("Please Select")),  # placeholder
            ('Less than 24 hours', _("Less than 24 hours")),
            ('Less than 48 hours', _("Less than 48 hours")),
            ('Less than 3 days', _("Less than 3 days")),
            ('Less than a week', _("Less than a week")),
        ],
        required=True
    )
    checkup_frequency = forms.ChoiceField(
        label=_("Checkup Frequency"),
        choices=[
            ('', _("Please Select")),  # placeholder
            ('Twice per month', _("Twice per month")),
            ('Once per month', _("Once per month")),
            ('Once every 2 months', _("Once every 2 months")),
            ('Once every 3 months', _("Once every 3 months")),
        ],
        required=True
    )
    monthly_price = forms.DecimalField(
        label=_("Monthly Price"),
        max_digits=15,
        decimal_places=2,
        min_value=0.00,
        required=True
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Crispy Forms helper
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.add_input(Submit('submit', _('Submit')))

class ProfessionalSubscriptionForm(forms.Form):

    platform_plan_fhir_ids = platform_plans.platform_plans.keys()
    plan_choices = []
    for platform_plan_fhir_id in platform_plan_fhir_ids:
        choice_value = platform_plan_fhir_id
        choice_text = _(platform_plan_fhir_id.split("-")[1]) # Exapmle: PlatformToProfessionalPlan-Basic-v-1-0 -> Basic
        plan_choices.append(
            (choice_value, choice_text.capitalize())
        )

    plan_title = forms.ChoiceField(
        label=_("Plan Title"),
        choices=plan_choices,
        required=True
    )

    voucher = forms.CharField(
        label=_("Applied Voucher"),
        max_length=100,
        required=False
    )

    paid_amount = forms.DecimalField(
        label=_("Paid Amount"),
        max_digits=15,
        decimal_places=2,
        min_value=0.00,
        required=True
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Crispy Forms helper
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.add_input(Submit('submit', _('Activate')))


class ContactUsForm(forms.Form):
    subject = forms.CharField(
        label=_("Subject"),
        max_length=255,
        required=True,
        widget=forms.TextInput(attrs={"class": "form-input", "placeholder": _("Subject")})
    )
    body = forms.CharField(
        label=_("Message"),
        required=True,
        widget=forms.Textarea(attrs={"class": "form-textarea", "placeholder": _("Your message...")})
    )