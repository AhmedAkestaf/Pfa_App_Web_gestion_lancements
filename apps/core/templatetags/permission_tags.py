from django import template
from django.contrib.auth.models import AnonymousUser

register = template.Library()

@register.simple_tag(takes_context=True)
def has_permission(context, module, action):
    """Vérifie si l'utilisateur a une permission dans le template"""
    request = context['request']
    if isinstance(request.user, AnonymousUser):
        return False
    return request.user.has_permission(module, action)

@register.inclusion_tag('core/components/permission_button.html', takes_context=True)
def permission_button(context, module, action, button_text, button_class="btn btn-primary", url="#"):
    """Génère un bouton conditionnel selon les permissions"""
    request = context['request']
    has_perm = False
    if not isinstance(request.user, AnonymousUser):
        has_perm = request.user.has_permission(module, action)
    
    return {
        'has_permission': has_perm,
        'button_text': button_text,
        'button_class': button_class,
        'url': url
    }
