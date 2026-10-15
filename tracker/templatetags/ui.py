from django import template

register = template.Library()


@register.simple_tag(takes_context=True)
def page_url(context, page_number):
    """Link to another page while keeping every current GET parameter
    (status, priority, q ...). Usage:  href="{% page_url 3 %}" """
    query = context["request"].GET.copy()
    query["page"] = page_number
    return "?" + query.urlencode()
