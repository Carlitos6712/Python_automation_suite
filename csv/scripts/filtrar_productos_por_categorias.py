#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script: filtrar_productos_por_categorias.py
Propósito: Filtra productos de un archivo CSV basándose en categorías deseadas,
           y añade columnas 'Categoria' e 'Imagen' al resultado.

Entrada:
    - export_producto_finalisimo.csv : Archivo de productos (debe contener al menos 'Ref').
    - export_categorie_product_finalisimo.csv : Archivo de relaciones producto-categoría
      (debe contener 'ParentCategoryID', 'Ref' y 'ParentCategoryLabel').

Proceso:
    1. Lee el archivo de categorías y construye un diccionario que mapea cada
       producto (Ref) al conjunto de etiquetas de las categorías deseadas.
    2. Lee el archivo de productos y escribe en un nuevo archivo solo aquellos
       productos que aparecen en el diccionario, añadiendo:
         - Columna 'Categoria' : etiquetas de categorías (separadas por coma).
         - Columna 'Imagen'    : valor de Ref + ".jpg" (o vacío si Ref no existe).

Salida: Archivo CSV en 'data/output/productos_filtrados_final.csv' con codificación utf-8-sig.

Uso:
    1. Ajustar las rutas de archivo en la sección CONFIGURACIÓN si es necesario.
    2. Asegurar que los archivos de entrada tienen las columnas esperadas.
    3. Ejecutar el script.
"""

import csv
import os

# =============================================================================
# CONFIGURACIÓN (modificar según necesidades)
# =============================================================================
# Archivos de entrada y salida
ARCHIVO_PRODUCTOS = "archivo_productos.csv"
ARCHIVO_CATEGORIAS = "archivos_categorias.csv"
ARCHIVO_SALIDA = "data/output/productos_filtrados_final.csv"

# IDs de las categorías que nos interesan
# 1: Pájaros, 3: Gatos, 5: Perros, 7: Reptiles, 8: Roedores, Peces:1135
CATEGORIAS_DESEADAS = {1, 3, 5, 7, 8, 1135}

# Nombres de columnas en el archivo de categorías
COLUMNA_FILTRO = "ParentCategoryID"      # Columna con el ID de categoría
COL_PROD_ID = "Ref"                 # Columna que enlaza con el producto
COL_CAT_LABEL = "ParentCategoryLabel"     # Columna con la etiqueta de la categoría

# Nombres de columnas en el archivo de productos
COL_ID_PRODUCTO = "Ref"                    # Identificador del producto
COL_REF = "Ref"                            # Columna que contiene la referencia para la imagen

# Codificación de los archivos
ENCODING_ENTRADA = "utf-8"                # Prueba con 'latin-1' si hay problemas
ENCODING_SALIDA = "utf-8-sig"              # utf-8-sig para que Excel reconozca tildes

# =============================================================================
# FUNCIONES AUXILIARES
# =============================================================================
def obtener_categorias_por_producto():
    """
    Recorre el archivo de categorías y devuelve un diccionario:
        clave = ProductId (str)
        valor = conjunto de etiquetas (ParentCategoryLabel) de las categorías deseadas.

    Retorna:
        dict o None: Diccionario con productos y sus etiquetas, o None si hay error.
    """
    prod_to_labels = {}
    try:
        with open(ARCHIVO_CATEGORIAS, mode='r', newline='', encoding=ENCODING_ENTRADA) as f:
            reader = csv.DictReader(f)
            # Verificar que las columnas necesarias existen
            required_cols = [COLUMNA_FILTRO, COL_PROD_ID, COL_CAT_LABEL]
            for col in required_cols:
                if col not in reader.fieldnames:
                    raise ValueError(f"Columna '{col}' no encontrada en {ARCHIVO_CATEGORIAS}")

            for fila in reader:
                try:
                    cat_id = int(fila[COLUMNA_FILTRO])   # Convertir a entero
                except (ValueError, TypeError):
                    continue   # Ignorar filas con ID no numérico
                if cat_id in CATEGORIAS_DESEADAS:
                    prod_id = fila[COL_PROD_ID]
                    label = fila.get(COL_CAT_LABEL, '').strip()
                    if prod_id not in prod_to_labels:
                        prod_to_labels[prod_id] = set()
                    if label:   # Solo añadir si la etiqueta no está vacía
                        prod_to_labels[prod_id].add(label)
    except FileNotFoundError:
        print(f" ❌ ERROR: No se encuentra el archivo '{ARCHIVO_CATEGORIAS}'")
        return None
    except UnicodeDecodeError:
        print(f" ❌ ERROR: No se pudo leer '{ARCHIVO_CATEGORIAS}' con codificación {ENCODING_ENTRADA}.")
        print("   Prueba a cambiar ENCODING_ENTRADA a 'latin-1' o 'cp1252' en la configuración.")
        return None
    except Exception as e:
        print(f" ❌ Error al leer categorías: {e}")
        return None

    return prod_to_labels

def filtrar_productos(prod_to_labels):
    """
    Lee el archivo de productos y escribe en ARCHIVO_SALIDA solo aquellos
    cuyo 'Id' esté en prod_to_labels, añadiendo las columnas 'Categoria' e 'Imagen'.

    Parámetros:
        prod_to_labels (dict): Diccionario devuelto por obtener_categorias_por_producto.

    Retorna:
        bool: True si el proceso fue exitoso, False en caso contrario.
    """
    if prod_to_labels is None:
        return False

    # Crear carpeta de salida si no existe
    try:
        os.makedirs(os.path.dirname(ARCHIVO_SALIDA) or '.', exist_ok=True)
    except Exception as e:
        print(f" ❌ Error al crear la carpeta de salida: {e}")
        return False

    try:
        with open(ARCHIVO_PRODUCTOS, mode='r', newline='', encoding=ENCODING_ENTRADA) as f_in, \
             open(ARCHIVO_SALIDA, mode='w', newline='', encoding=ENCODING_SALIDA) as f_out:

            reader = csv.DictReader(f_in)
            if COL_ID_PRODUCTO not in reader.fieldnames:
                raise ValueError(f"Columna '{COL_ID_PRODUCTO}' no encontrada en {ARCHIVO_PRODUCTOS}")

            # Comprobar si existe la columna 'ref' para la imagen
            if COL_REF not in reader.fieldnames:
                print(f" ⚠️  ADVERTENCIA: Columna '{COL_REF}' no encontrada. La columna 'Imagen' quedará vacía.")

            # Nuevos campos de salida: los originales + Categoria + Imagen
            fieldnames = reader.fieldnames + ['Categoria', 'Imagen']
            writer = csv.DictWriter(f_out, fieldnames=fieldnames)
            writer.writeheader()

            contador = 0
            for fila in reader:
                prod_id = fila[COL_ID_PRODUCTO]
                if prod_id in prod_to_labels:
                    # Construir nueva fila con los campos extra
                    nueva_fila = dict(fila)   # copia de los campos originales

                    # Columna Categoria: unir las etiquetas (ordenadas)
                    etiquetas = prod_to_labels[prod_id]
                    nueva_fila['Categoria'] = ', '.join(sorted(etiquetas))

                    # Columna Imagen: ref + ".jpg"
                    ref = fila.get(COL_REF, '')
                    if ref:
                        nueva_fila['Imagen'] = ref + '.jpg'
                    else:
                        nueva_fila['Imagen'] = ''

                    writer.writerow(nueva_fila)
                    contador += 1

        print(f" ✅ Proceso completado. Se han guardado {contador} productos en '{ARCHIVO_SALIDA}'.")
        return True

    except FileNotFoundError:
        print(f" ❌ ERROR: No se encuentra el archivo '{ARCHIVO_PRODUCTOS}'")
        return False
    except UnicodeDecodeError:
        print(f" ❌ ERROR: No se pudo leer '{ARCHIVO_PRODUCTOS}' con codificación {ENCODING_ENTRADA}.")
        print("   Prueba a cambiar ENCODING_ENTRADA a 'latin-1' o 'cp1252' en la configuración.")
        return False
    except Exception as e:
        print(f" ❌ Error al filtrar productos: {e}")
        return False

# =============================================================================
# FUNCIÓN PRINCIPAL
# =============================================================================
def main():
    """Orquesta el proceso de filtrado y muestra resumen."""
    print("=" * 70)
    print(" 🧹 FILTRADO DE PRODUCTOS POR CATEGORÍAS")
    print("=" * 70)

    print(" 🔍 Obteniendo categorías de productos...")
    prod_to_labels = obtener_categorias_por_producto()
    if prod_to_labels is None:
        return

    print(f"    Se encontraron {len(prod_to_labels)} productos con las categorías deseadas.")

    print(" 📝 Filtrando archivo de productos y añadiendo columnas...")
    filtrar_productos(prod_to_labels)

    print("=" * 70)
    print(" ✨ Proceso completado.")
    print("=" * 70)

if __name__ == "__main__":
    main()