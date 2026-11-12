from django import template
from inventory.translations import get_text

register = template.Library()

@register.filter(name='t')
def translate_filter(key, context_lang=None):
    # If context_lang is passed
    if context_lang:
        return get_text(key, context_lang)
    return get_text(key, 'en')

@register.simple_tag(takes_context=True)
def tr(context, key, default=None):
    lang = context.get('current_lang', 'en')
    return get_text(key, lang, default)

@register.filter(name='abs')
def abs_filter(val):
    try:
        return abs(int(val))
    except Exception:
        try:
            return abs(float(val))
        except Exception:
            return val
