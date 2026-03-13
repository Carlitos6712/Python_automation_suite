# config/patterns.py
"""
Patrones de detección para medidas
"""
import re

# Patrones para detectar peso
PESO_PATTERNS = {
    'patron': re.compile(
        r'(\d+[\.,]?\d*)\s*(KG|KILOS|KILO|G|GR|GRAMOS|GRAMO|OUNCE|OZ|LB|LIBRAS|'
        r'kg|kilos|kilo|g|gr|gramos|gramo|ounce|oz|lb|libras)', 
        re.IGNORECASE
    ),
    'unidades': {
        'KG': 'kg', 'KILOS': 'kg', 'KILO': 'kg', 'kg': 'kg', 'kilos': 'kg', 'kilo': 'kg',
        'G': 'g', 'GR': 'g', 'GRAMOS': 'g', 'GRAMO': 'g', 'g': 'g', 'gr': 'g', 
        'gramos': 'g', 'gramo': 'g',
        'OUNCE': 'oz', 'OZ': 'oz', 'ounce': 'oz', 'oz': 'oz',
        'LB': 'lb', 'LIBRAS': 'lb', 'lb': 'lb', 'libras': 'lb'
    }
}

# Patrones para detectar volumen
VOLUMEN_PATTERNS = {
    'patron': re.compile(
        r'(\d+[\.,]?\d*)\s*(ML|MILILITRO|MILILITROS|L|LITRO|LITROS|GAL|GALON|GALONES|'
        r'ml|mililitro|mililitros|l|litro|litros|gal|galon|galones)', 
        re.IGNORECASE
    ),
    'unidades': {
        'ML': 'ml', 'MILILITRO': 'ml', 'MILILITROS': 'ml', 'ml': 'ml', 
        'mililitro': 'ml', 'mililitros': 'ml',
        'L': 'l', 'LITRO': 'l', 'LITROS': 'l', 'l': 'l', 'litro': 'l', 'litros': 'l',
        'GAL': 'gal', 'GALON': 'gal', 'GALONES': 'gal', 'gal': 'gal', 
        'galon': 'gal', 'galones': 'gal'
    }
}

# Patrones para detectar tamaño
TAMAÑO_PATTERNS = {
    'patron': re.compile(
        r'(\d+[\.,]?\d*)\s*(CM|CENTIMETRO|CENTIMETROS|M|METRO|METROS|MM|MILIMETRO|'
        r'MILIMETROS|PULG|PULGADA|PULGADAS|cm|centimetro|centimetros|m|metro|metros|'
        r'mm|milimetro|milimetros|pulg|pulgada|pulgadas)', 
        re.IGNORECASE
    ),
    'unidades': {
        'CM': 'cm', 'CENTIMETRO': 'cm', 'CENTIMETROS': 'cm', 'cm': 'cm', 
        'centimetro': 'cm', 'centimetros': 'cm',
        'M': 'm', 'METRO': 'm', 'METROS': 'm', 'm': 'm', 'metro': 'm', 'metros': 'm',
        'MM': 'mm', 'MILIMETRO': 'mm', 'MILIMETROS': 'mm', 'mm': 'mm', 
        'milimetro': 'mm', 'milimetros': 'mm',
        'PULG': 'in', 'PULGADA': 'in', 'PULGADAS': 'in', 'pulg': 'in', 
        'pulgada': 'in', 'pulgadas': 'in'
    }
}

# Todos los patrones juntos
ALL_PATTERNS = {
    'peso': PESO_PATTERNS,
    'volumen': VOLUMEN_PATTERNS,
    'tamaño': TAMAÑO_PATTERNS
}