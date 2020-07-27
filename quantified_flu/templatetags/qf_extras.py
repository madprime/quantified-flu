from django import template

from quantified_flu.helpers import identify_missing_sources

register = template.Library()


@register.filter
def missing_sources(member):
    # try/except to fail gracefully on edge case when user has deauthorized
    # on open humans, but is still logged in locally.
    try:
        return identify_missing_sources(member)
    except Exception:
        return []


@register.tag(name="get_formfield_value")
def get_formfield_value(parser, token):
    """
    Sets context variable "field_value" from the form for the field provided.

    This enables programmatically handling HTML for form fields in the template.
    """
    return FormFieldValueNode()


class FormFieldValueNode(template.Node):
    def render(self, context):
        # get from template context the value of the "form_field" variable
        field_name = context["form_field"]

        # get the form from template context, look up this value
        form = context["form"]
        field_value = form[field_name].value()

        # set the template context "field_value" to this
        context["form_field_value"] = field_value
        return ""
