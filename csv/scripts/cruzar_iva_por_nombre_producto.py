#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script: cruzar_iva_por_nombre_producto.py
Propósito: Asigna tasas de IVA a un archivo de productos sin IVA, cruzando por nombre
           con un archivo de referencia que contiene productos con IVA conocido.

Entrada:
    - Archivo SIN IVA (data/input/tus_productos_nuevos.csv): contiene al menos columnas 'Código' y 'Producto'.
    - Archivo CON IVA (data/input/productos_originales_con_iva.csv): contiene al menos columnas 'Ref', 'Label' y 'VATRate'.

Proceso:
    1. Normaliza los nombres de ambos archivos (minúsculas, sin acentos, sin espacios extra).
    2. Construye un diccionario de nombres normalizados a IVA desde el archivo CON IVA.
    3. Para cada producto en el archivo SIN IVA:
        - Busca coincidencia exacta por nombre normalizado.
        - Si no hay exacta, busca la coincidencia más cercana (similitud >= umbral configurable).
        - Si no encuentra, asigna un IVA por defecto.
    4. Añade la columna 'IVA_Asignado' al archivo SIN IVA.
    5. Guarda el resultado en un nuevo CSV con timestamp.

Salida: Archivo CSV en 'data/output/productos_con_iva_nombre_<timestamp>.csv'.

Uso:
    1. Ajustar las rutas de archivo y constantes en la sección CONFIGURACIÓN si es necesario.
    2. Ejecutar el script.
    3. Revisar el resumen y el archivo generado.
"""

import pandas as pd
import os
from datetime import datetime
import unicodedata
import difflib

# =============================================================================
# CONFIGURACIÓN (modificar según necesidades)
# =============================================================================
ARCHIVO_SIN_IVA = "data/input/archivo.csv"
ARCHIVO_CON_IVA = "data/input/archivo.csv"
ARCHIVO_SALIDA = "data/output/productos_con_iva_final.csv"

# Nombres de columnas en los archivos
COL_CODIGO_SIN = 'Código'
COL_NOMBRE_SIN = 'Producto'
COL_CODIGO_CON = 'Ref'
COL_NOMBRE_CON = 'Label'
COL_IVA = 'VATRate'

# Tasa de IVA por defecto para productos sin coincidencia
IVA_DEFECTO = 21.0

# Umbral de similitud para coincidencias aproximadas (0.0 a 1.0)
UMBRAL_SIMILITUD = 0.85

# =============================================================================
# FUNCIONES AUXILIARES
# =============================================================================
def normalizar_texto(texto):
    """
    Normaliza un texto:
        - Convierte a minúsculas.
        - Elimina tildes y caracteres especiales (normalización Unicode).
        - Elimina espacios múltiples y recorta.
    Si no es una cadena, retorna cadena vacía.
    """
    if not isinstance(texto, str):
        return ""
    texto = texto.lower()
    texto = unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('utf-8')
    texto = ' '.join(texto.split())  # eliminar espacios múltiples
    return texto.strip()

def buscar_iva_por_nombre(nombre_norm, diccionario, umbral=UMBRAL_SIMILITUD):
    """
    Busca el IVA asociado a un nombre normalizado:
        - Coincidencia exacta: devuelve el valor.
        - Coincidencia aproximada (difflib): devuelve el valor si supera el umbral.
        - Sin coincidencia: devuelve None.
    """
    if not nombre_norm:
        return None
    # Coincidencia exacta
    if nombre_norm in diccionario:
        return diccionario[nombre_norm]
    # Coincidencia aproximada (si no hay exacta)
    mejores = difflib.get_close_matches(nombre_norm, diccionario.keys(), n=1, cutoff=umbral)
    if mejores:
        return diccionario[mejores[0]]
    return None

# =============================================================================
# FUNCIÓN PRINCIPAL
# =============================================================================
def main():
    """Orquesta todo el proceso de cruce de IVA por nombre."""
    print("=" * 70)
    print(" 🔄 CRUZADO DE IVA POR NOMBRE DE PRODUCTO")
    print("=" * 70)

    # --- Verificar existencia de archivos ---
    for archivo, nombre in [(ARCHIVO_SIN_IVA, "SIN IVA"), (ARCHIVO_CON_IVA, "CON IVA")]:
        if not os.path.exists(archivo):
            print(f" ❌ ERROR: No se encuentra el archivo {nombre}: '{archivo}'.")
            return
        print(f" ✅ Archivo {nombre} encontrado: {archivo}")

    # --- Cargar archivos ---
    print("\n 📂 Cargando archivos...")
    try:
        df_sin_iva = pd.read_csv(ARCHIVO_SIN_IVA)
        df_con_iva = pd.read_csv(ARCHIVO_CON_IVA)
    except Exception as e:
        print(f" ❌ Error al leer archivos: {e}")
        return

    print(f"    Archivo SIN IVA: {len(df_sin_iva)} productos")
    print(f"    Archivo CON IVA: {len(df_con_iva)} productos")

    # --- Verificar columnas requeridas ---
    columnas_sin = [COL_CODIGO_SIN, COL_NOMBRE_SIN]
    columnas_con = [COL_CODIGO_CON, COL_NOMBRE_CON, COL_IVA]

    for col in columnas_sin:
        if col not in df_sin_iva.columns:
            print(f" ❌ ERROR: El archivo SIN IVA no contiene la columna '{col}'.")
            print(f"    Columnas disponibles: {list(df_sin_iva.columns)}")
            return

    for col in columnas_con:
        if col not in df_con_iva.columns:
            print(f" ❌ ERROR: El archivo CON IVA no contiene la columna '{col}'.")
            print(f"    Columnas disponibles: {list(df_con_iva.columns)}")
            return

    print("\n 🔧 Columnas utilizadas:")
    print(f"    Archivo SIN IVA: Código='{COL_CODIGO_SIN}', Nombre='{COL_NOMBRE_SIN}'")
    print(f"    Archivo CON IVA: Código='{COL_CODIGO_CON}', Nombre='{COL_NOMBRE_CON}', IVA='{COL_IVA}'")

    # --- Normalizar nombres ---
    print("\n 🔍 Normalizando nombres de productos...")
    df_sin_iva['nombre_norm'] = df_sin_iva[COL_NOMBRE_SIN].apply(normalizar_texto)
    df_con_iva['nombre_norm'] = df_con_iva[COL_NOMBRE_CON].apply(normalizar_texto)

    # --- Crear diccionario de nombres normalizados a IVA (del archivo CON IVA) ---
    print("\n 📚 Creando diccionario de nombres normalizados a IVA...")
    diccionario_nombre_iva = {}
    for _, row in df_con_iva.iterrows():
        nombre_norm = row['nombre_norm']
        if pd.notna(nombre_norm) and nombre_norm:
            iva = row[COL_IVA]
            try:
                if pd.notna(iva):
                    # Limpiar posibles símbolos % y comas
                    iva_valor = float(str(iva).replace('%', '').replace(',', '.'))
                    if nombre_norm not in diccionario_nombre_iva:
                        diccionario_nombre_iva[nombre_norm] = iva_valor
            except (ValueError, TypeError):
                # Ignorar valores de IVA no convertibles
                pass

    print(f"    ✅ {len(diccionario_nombre_iva)} nombres únicos normalizados en archivo CON IVA")

    # --- Aplicar búsqueda de IVA ---
    print("\n 🔎 Buscando coincidencias por nombre...")
    resultados = {
        'exactas': 0,
        'aproximadas': 0,
        'nuevos': 0
    }

    def asignar_iva(row):
        nombre_norm = row['nombre_norm']
        # Coincidencia exacta
        if nombre_norm in diccionario_nombre_iva:
            resultados['exactas'] += 1
            return diccionario_nombre_iva[nombre_norm]
        # Coincidencia aproximada
        aproximada = buscar_iva_por_nombre(nombre_norm, diccionario_nombre_iva, UMBRAL_SIMILITUD)
        if aproximada is not None:
            resultados['aproximadas'] += 1
            return aproximada
        # No encontrado
        resultados['nuevos'] += 1
        return IVA_DEFECTO

    df_sin_iva['IVA_Asignado'] = df_sin_iva.apply(asignar_iva, axis=1)

    # --- Mostrar resultados globales ---
    print("\n" + "=" * 70)
    print(" 📊 RESULTADOS DE BÚSQUEDA POR NOMBRE")
    print("=" * 70)
    print(f" 📦 Total productos procesados: {len(df_sin_iva)}")
    print(f" ✅ Coincidencias exactas: {resultados['exactas']}")
    print(f" 🔄 Coincidencias aproximadas: {resultados['aproximadas']}")
    print(f" ➕ Productos nuevos (IVA {IVA_DEFECTO}%): {resultados['nuevos']}")

    # --- Verificación de primeros 20 productos ---
    print("\n 🔍 VERIFICANDO PRIMEROS 20 PRODUCTOS:")
    print("-" * 80)
    for i, row in df_sin_iva.head(20).iterrows():
        codigo = row[COL_CODIGO_SIN]
        nombre = row[COL_NOMBRE_SIN]
        iva = row['IVA_Asignado']
        nombre_norm = row['nombre_norm']

        if nombre_norm in diccionario_nombre_iva:
            print(f"    ✓ {codigo} - {nombre[:30]:<30} → IVA: {iva}% (exacta)")
        elif buscar_iva_por_nombre(nombre_norm, diccionario_nombre_iva) is not None:
            print(f"    ~ {codigo} - {nombre[:30]:<30} → IVA: {iva}% (aproximada)")
        else:
            print(f"    ✗ {codigo} - {nombre[:30]:<30} → IVA: {iva}% (nuevo)")

    # --- Distribución de IVA en el resultado ---
    print("\n 📈 Distribución de IVA en archivo final:")
    distribucion = df_sin_iva['IVA_Asignado'].value_counts().sort_index()
    for iva, count in distribucion.items():
        porcentaje = (count / len(df_sin_iva)) * 100
        print(f"    • {iva}%: {count} productos ({porcentaje:.1f}%)")

    # --- Guardar archivo final ---
    print("\n 💾 Guardando archivo final...")
    # Crear carpeta de salida si no existe
    try:
        os.makedirs(os.path.dirname(ARCHIVO_SALIDA) or '.', exist_ok=True)
    except Exception as e:
        print(f" ❌ Error al crear la carpeta de salida: {e}")
        return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    nombre_salida = f"data/output/productos_con_iva_nombre_{timestamp}.csv"
    try:
        df_sin_iva.to_csv(nombre_salida, index=False, encoding='utf-8-sig')
        print(f"    ✅ Archivo guardado: {nombre_salida}")
    except Exception as e:
        print(f" ❌ Error al guardar el archivo: {e}")
        return

    print("\n" + "=" * 70)
    print(" ✨ ¡PROCESO COMPLETADO!")
    print("=" * 70)


if __name__ == "__main__":
    main()