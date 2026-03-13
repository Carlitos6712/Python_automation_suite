# config/settings.py
"""
Configuraciones generales del proyecto
"""

# Carpetas
INPUT_FOLDER = "data/input/"
OUTPUT_FOLDER = "data/output/"
BACKUP_FOLDER = "data/backup/"

# Valores por defecto
DEFAULT_MIN_STOCK = 5
DEFAULT_MAX_STOCK = 50

# Campos para Dolibarr
DOLIBARR_FIELDS = [
    'Código',
    'Producto',
    'P. Costo',
    'P. Venta',
    'P. Mayoreo',
    'Existencia',
    'Inv. Mínimo',
    'Inv. Máximo',
    'Departamento',
    'Peso',
    'Volumen',
    'Tamaño'
]

# Mapeo de columnas para búsqueda flexible
COLUMN_MAPPING = {
    'CODIGO': ['CODIGO', 'COD', 'ID', 'REFERENCIA', 'SKU', 'REF'],
    'PRODUCTO': ['PRODUCTO', 'NOMBRE', 'DESCRIPCION', 'TITULO', 'DESC'],
    'COSTO': ['COSTO', 'P. COSTO', 'PRECIO COSTO', 'P_COSTO', 'COST'],
    'VENTA': ['VENTA', 'P. VENTA', 'PRECIO VENTA', 'P_VENTA', 'PRECIO', 'PRICE'],
    'MAYOREO': ['MAYOREO', 'P. MAYOREO', 'PRECIO MAYOREO', 'P_MAYOREO', 'WHOLESALE'],
    'EXISTENCIA': ['EXISTENCIA', 'STOCK', 'CANTIDAD', 'INVENTARIO', 'QTY'],
    'MINIMO': ['MINIMO', 'INV. MINIMO', 'STOCK MINIMO', 'MIN'],
    'MAXIMO': ['MAXIMO', 'INV. MAXIMO', 'STOCK MAXIMO', 'MAX']
}