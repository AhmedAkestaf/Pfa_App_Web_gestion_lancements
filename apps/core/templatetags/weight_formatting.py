from django import template
from decimal import Decimal, InvalidOperation
import locale

register = template.Library()

@register.filter
def format_weight(value, unit="kg"):
    """
    Filtre pour formater les poids avec format français :
    - 3 chiffres après la virgule
    - Espaces comme séparateurs de milliers
    - Virgule comme séparateur décimal
    - Ajout de l'unité (kg par défaut)
    
    Exemples :
    - 1000.231 -> "1 000,231 kg"
    - 21012.145 -> "21 012,145 kg"
    - 0.5 -> "0,500 kg"
    """
    if value is None:
        return "0,000 kg"
    
    try:
        # Convertir en Decimal pour éviter les problèmes de précision
        if isinstance(value, str):
            decimal_value = Decimal(value.replace(',', '.'))
        else:
            decimal_value = Decimal(str(value))
        
        # Si la valeur est 0, retourner directement
        if decimal_value == 0:
            return f"0,000 {unit}"
        
        # Formatter avec 3 décimales
        formatted = f"{decimal_value:.3f}"
        
        # Séparer la partie entière et décimale
        if '.' in formatted:
            integer_part, decimal_part = formatted.split('.')
        else:
            integer_part = formatted
            decimal_part = "000"
        
        # Ajouter les espaces comme séparateurs de milliers
        # Traiter la partie entière de droite à gauche
        integer_formatted = ""
        for i, digit in enumerate(reversed(integer_part)):
            if i > 0 and i % 3 == 0:
                integer_formatted = " " + integer_formatted
            integer_formatted = digit + integer_formatted
        
        # Retourner le résultat formaté avec virgule comme séparateur décimal
        return f"{integer_formatted},{decimal_part} {unit}"
        
    except (InvalidOperation, ValueError, TypeError):
        return f"0,000 {unit}"

@register.filter
def format_weight_short(value):
    """
    Version courte sans unité pour les calculs JavaScript
    """
    return format_weight(value, "").strip()

@register.simple_tag
def format_total_weight(poids_debitage, poids_assemblage, unit="kg"):
    """
    Tag pour calculer et formater le poids total
    """
    try:
        debitage = Decimal(str(poids_debitage or 0))
        assemblage = Decimal(str(poids_assemblage or 0))
        total = debitage + assemblage
        return format_weight(total, unit)
    except (InvalidOperation, ValueError, TypeError):
        return f"0,000 {unit}"

@register.filter
def weight_percentage(part_weight, total_weight):
    """
    Calcule le pourcentage d'un poids par rapport au total
    """
    try:
        part = Decimal(str(part_weight or 0))
        total = Decimal(str(total_weight or 0))
        
        if total == 0:
            return "0"
        
        percentage = (part / total) * 100
        return f"{percentage:.1f}"
        
    except (InvalidOperation, ValueError, TypeError):
        return "0"
