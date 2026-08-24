from django import template


register = template.Library()


@register.filter
def image_fit(image, target_ratio=1.6):
    if not image:
        return "object-cover"

    try:
        width = image.width
        height = image.height
    except Exception:
        return "object-cover"

    if not width or not height:
        return "object-cover"

    ratio = width / height
    target_ratio = float(target_ratio)

    if ratio < target_ratio * 0.9:
        return "object-contain"

    if ratio > target_ratio * 1.35:
        return "object-contain"

    return "object-cover"


@register.filter
def image_frame(image, target_ratio=1.6):
    if not image:
        return ""

    try:
        width = image.width
        height = image.height
    except Exception:
        return ""

    if not width or not height:
        return ""

    ratio = width / height
    target_ratio = float(target_ratio)

    if ratio < target_ratio * 0.9 or ratio > target_ratio * 1.35:
        return "bg-transparent"

    return ""
