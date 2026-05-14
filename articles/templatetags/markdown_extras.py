import markdown
from django import template
from django.utils.safestring import mark_safe


register = template.Library()


@register.filter(name="markdown")
def markdown_format(text):
    if not text:
        return ""

    html = markdown.markdown(
        text,
        extensions=[
            "markdown.extensions.extra",
            "markdown.extensions.nl2br",
            "markdown.extensions.sane_lists",
        ],
        output_format="html5",
    )

    return mark_safe(html)