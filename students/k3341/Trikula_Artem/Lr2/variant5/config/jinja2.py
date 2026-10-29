from django.contrib.messages import get_messages
from django.templatetags.static import static
from django.urls import reverse
from jinja2 import Environment


def page_url(request, number: int) -> str:
    parameters = request.GET.copy()
    parameters["page"] = number
    return "?" + parameters.urlencode()


def environment(**options):
    env = Environment(**options)
    env.globals.update(
        url=reverse, static=static, messages=get_messages, page_url=page_url
    )
    env.filters["date"] = lambda value: value.strftime("%d.%m.%Y") if value else "—"
    return env
