# config/departments.py
"""
Configuración de departamentos para TIENDA DE ANIMALES
"""

DEPARTMENTS = {
    'PERROS': [
        'perro', 'perros', 'canino', 'can', 'dog', 'puppy', 'cachorro',
        'alimento para perro', 'croquetas perro', 'snack perro', 'hueso',
        'correa perro', 'collar perro', 'juguete perro', 'cama perro',
        'shampoo perro', 'cepillo perro', 'plato perro', 'transportadora'
    ],
    
    'GATOS': [
        'gato', 'gatos', 'felino', 'cat', 'kitten', 'gatito',
        'alimento para gato', 'croquetas gato', 'snack gato', 'pescado',
        'arena gato', 'rascador', 'juguete gato', 'cama gato',
        'shampoo gato', 'cepillo gato', 'transportadora gato'
    ],
    
    'PAJAROS': [
        'pajaro', 'pajaros', 'ave', 'aves', 'bird', 'canario', 'perico',
        'loro', 'cotorra', 'agapornis', 'ninfa', 'cacatua',
        'alimento para aves', 'semillas', 'alpiste', 'mixtura',
        'jaula', 'percha', 'juguete pajaro', 'bebedero', 'comedero',
        'nido', 'calcio', 'hueso jibia'
    ],
    
    'REPTILES': [
        'reptil', 'reptiles', 'reptile', 'tortuga', 'serpiente', 'lagarto',
        'iguana', 'gecko', 'camaleon', 'python', 'boa', 'culebra',
        'terrario', 'luz uv', 'calefaccion', 'termometro', 'higrometro',
        'sustrato', 'tronco', 'cueva', 'comedero reptiles',
        'alimento reptiles', 'grillos', 'tenebrios', 'vitaminas'
    ],
    
    'PECES': [
        'pez', 'peces', 'fish', 'goldfish', 'beta', 'guppy', 'molinesia',
        'acuario', 'pecera', 'filtro', 'calentador', 'termostato',
        'alimento peces', 'escamas', 'granulado', 'comida viva',
        'plantas acuaticas', 'decoracion', 'grava', 'arena acuario',
        'acondicionador agua', 'test acuario'
    ],
    
    'ROEDORES': [
        'roedor', 'roedores', 'hamster', 'cuyo', 'cobayo', 'conejo',
        'raton', 'rata', 'chinchilla', 'gerbo', 'ardilla',
        'jaula roedores', 'rueda', 'tubo', 'cama', 'viruta', 'heno',
        'alimento roedores', 'pellets', 'snack roedores', 'bebedero',
        'nido', 'juguete roedores'
    ],
    
    'ALIMENTOS': [
        'alimento', 'croqueta', 'comida', 'snack', 'premio', 'golosina',
        'pellets', 'heno', 'semilla', 'alpiste', 'mixtura', 'balanceado',
        'concentrado', 'pienso', 'menu'
    ],
    
    'ACCESORIOS': [
        'accesorio', 'juguete', 'cama', 'transportadora', 'correa',
        'collar', 'plato', 'comedero', 'bebedero', 'jaula', 'pecera',
        'acuario', 'terrario', 'rueda', 'rascador', 'cueva', 'nido'
    ],
    
    'HIGIENE': [
        'shampoo', 'jabon', 'cepillo', 'peine', 'cortaunas', 'toallitas',
        'limpiador', 'desinfectante', 'arena', 'viruta', 'papel',
        'bolsas', 'recolector', 'perfume', 'desodorante'
    ],
    
    'SALUD': [
        'vitamina', 'suplemento', 'medicina', 'antiparasitario',
        'desparasitante', 'antibiotico', 'probiotico', 'calcio',
        'primera comida', 'leche maternizada', 'gasas', 'vendas',
        'termometro', 'gotero', 'jeringa'
    ]
}

# Departamento por defecto
DEFAULT_DEPARTMENT = 'GENERAL'

# Mapeo de palabras clave específicas por especie
SPECIE_KEYWORDS = {
    'PERROS': ['perro', 'canino', 'dog'],
    'GATOS': ['gato', 'felino', 'cat'],
    'PAJAROS': ['pajaro', 'ave', 'bird', 'canario', 'perico', 'loro'],
    'REPTILES': ['reptil', 'tortuga', 'serpiente', 'iguana'],
    'PECES': ['pez', 'fish', 'acuario'],
    'ROEDORES': ['roedor', 'hamster', 'conejo', 'cuyo']
}

def detectar_especie(texto: str) -> str:
    """
    Detecta la especie específica del producto
    """
    if not texto:
        return None
    
    texto_lower = texto.lower()
    
    for especie, keywords in SPECIE_KEYWORDS.items():
        if any(keyword in texto_lower for keyword in keywords):
            return especie
    
    return None