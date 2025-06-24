from django import template

register = template.Library()

@register.simple_tag(takes_context=True)
def i18n_layout(context):
    language_code = context.get('LANGUAGE_CODE', 'en')
    if language_code == 'en':
        return {'dir': 'ltr', 'text_align_cls': 'text-left'}
    else:
        return {'dir': 'rtl', 'text_align_cls': 'text-right'}