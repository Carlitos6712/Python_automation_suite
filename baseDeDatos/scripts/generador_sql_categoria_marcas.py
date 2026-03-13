#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script: generador_sql_categoria_marcas.py
Propósito: Genera un archivo SQL para crear una categoría principal "Marcas"
           con subcategorías (las marcas) y asociar los productos a su marca
           respectiva, a partir de un archivo CSV.

Entrada: Archivo CSV separado por ';' con las columnas:
         - Código : referencia del producto.
         - Marca  : nombre de la marca a la que pertenece el producto.

Salida: Archivo SQL con nombre dinámico (fecha y hora) en la carpeta 'data/output/'.
        El SQL realiza tres pasos:
        1. Crea la categoría principal "Marcas" si no existe.
        2. Inserta cada marca como subcategoría de "Marcas".
        3. Asocia cada producto con su respectiva marca.

Uso:
    1. Colocar el archivo CSV en la ruta especificada en ARCHIVO_ENTRADA.
    2. Ajustar los nombres de columna en las constantes COL_CODIGO y COL_MARCA.
    3. Ejecutar el script.
    4. Revisar el archivo SQL generado y ejecutarlo en phpMyAdmin o herramienta similar.
"""

import pandas as pd
import os
from datetime import datetime

# =============================================================================
# CONFIGURACIÓN DEL USUARIO (modificar según necesidades)
# =============================================================================
ARCHIVO_ENTRADA = "data/input/archivo.csv"   # Ruta al CSV de entrada
ARCHIVO_SALIDA = f"data/output/insert_marcas_categoria_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"

SEP = ';'                     # Separador de columnas en el CSV
ENCODING = 'utf-8'            # Codificación del archivo CSV

# Nombres exactos de las columnas en el CSV (deben coincidir)
COL_CODIGO = 'Código'         # Columna con la referencia del producto
COL_MARCA = 'Marca'           # Columna con el nombre de la marca

# Nombre de la categoría principal que agrupará todas las marcas
CATEGORIA_MARCAS = 'Marcas'

# Valores por defecto para las categorías en Dolibarr
ENTITY = 1                    # Entidad (por defecto 1)
TYPE = 0                      # 0 = categoría de productos
VISIBLE = 1                   # Visible en la web
POSITION = 0                  # Posición (orden)

# =============================================================================
# FUNCIONES AUXILIARES
# =============================================================================
def escape_sql(valor):
    """
    Escapa comillas simples para su uso seguro en sentencias SQL.
    Si el valor es nulo o vacío retorna 'NULL', de lo contrario retorna
    el valor entre comillas simples con las comillas internas escapadas.
    """
    if pd.isna(valor) or str(valor).strip() == '':
        return "NULL"
    s = str(valor).replace("'", "''")
    return f"'{s}'"

# =============================================================================
# INICIO DEL PROCESO
# =============================================================================
def main():
    """Función principal que orquesta la lectura, validación y generación del SQL."""
    print("=" * 70)
    print(" 🏷️  GENERADOR SQL: CATEGORÍA 'MARCAS' Y SUBCATEGORÍAS")
    print("=" * 70)

    # Verificar existencia del archivo de entrada
    if not os.path.exists(ARCHIVO_ENTRADA):
        print(f" ❌ ERROR: No se encuentra el archivo '{ARCHIVO_ENTRADA}'.")
        print("   Por favor, verifica la ruta y el nombre del archivo.")
        return

    print(f" 📄 Leyendo archivo: {ARCHIVO_ENTRADA}")

    # Leer CSV con pandas, manejando posibles errores de formato
    try:
        df = pd.read_csv(
            ARCHIVO_ENTRADA,
            sep=SEP,
            encoding=ENCODING,
            engine='python',
            quotechar='"',
            skipinitialspace=True,
            on_bad_lines='warn'      # Emite advertencia para líneas problemáticas
        )
    except Exception as e:
        print(f" ❌ Error al leer el CSV: {e}")
        print("   Revisa que el archivo no esté corrupto y que el separador sea correcto.")
        return

    # Limpiar nombres de columna (eliminar espacios al inicio/fin)
    df.columns = [col.strip() for col in df.columns]

    # Mostrar columnas detectadas para depuración
    print("\n 📋 Columnas detectadas en el CSV:")
    for col in df.columns:
        print(f"    - '{col}'")

    # Validar que las columnas requeridas existan
    if COL_CODIGO not in df.columns or COL_MARCA not in df.columns:
        print(f" ❌ El CSV debe contener las columnas '{COL_CODIGO}' y '{COL_MARCA}'.")
        print("   Verifica los nombres (incluyendo mayúsculas, acentos y espacios).")
        return

    # Eliminar filas con valores nulos o vacíos en las columnas clave
    # Esto evita procesar registros incompletos.
    df = df.dropna(subset=[COL_CODIGO, COL_MARCA])
    df = df[df[COL_CODIGO].astype(str).str.strip() != '']
    df = df[df[COL_MARCA].astype(str).str.strip() != '']

    # Extraer marcas únicas, limpiando espacios
    marcas_unicas = df[COL_MARCA].astype(str).str.strip().unique()
    marcas_unicas = [m for m in marcas_unicas if m != '']

    print(f"\n 📊 Marcas únicas encontradas: {len(marcas_unicas)}")
    if len(marcas_unicas) > 0:
        print("    Primeras 10 marcas:", marcas_unicas[:10])

    total_productos = len(df)
    print(f" 📦 Total productos con marca válida: {total_productos}")

    if total_productos == 0:
        print("\n ⚠️  No hay productos para procesar. Saliendo.")
        return

    # =========================================================================
    # GENERACIÓN DEL ARCHIVO SQL
    # =========================================================================
    try:
        with open(ARCHIVO_SALIDA, 'w', encoding='utf-8') as f:
            # Cabecera del archivo SQL
            f.write("-- =========================================================\n")
            f.write("-- CREACIÓN DE CATEGORÍA 'MARCAS' Y SUBCATEGORÍAS\n")
            f.write(f"-- Generado el {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("-- =========================================================\n\n")
            f.write("START TRANSACTION;\n\n")

            # ---- 1. Insertar categoría principal "Marcas" (si no existe) ----
            cat_princ_esc = escape_sql(CATEGORIA_MARCAS)
            f.write("-- 1. Insertar categoría principal 'Marcas' (si no existe)\n")
            f.write("INSERT IGNORE INTO llx_categorie\n")
            f.write("    (label, type, entity, visible, position, fk_parent, description, color)\n")
            f.write(f"VALUES ({cat_princ_esc}, {TYPE}, {ENTITY}, {VISIBLE}, {POSITION}, 0, NULL, NULL);\n\n")

            # ---- 2. Insertar cada marca como subcategoría de "Marcas" ----
            f.write("-- 2. Insertar marcas como subcategorías de 'Marcas'\n")
            for marca in marcas_unicas:
                marca_esc = escape_sql(marca)
                # Usamos INSERT IGNORE para evitar duplicados
                f.write("INSERT IGNORE INTO llx_categorie\n")
                f.write("    (label, type, entity, visible, position, fk_parent, description, color)\n")
                f.write(f"SELECT {marca_esc}, {TYPE}, {ENTITY}, {VISIBLE}, {POSITION}, c.rowid, NULL, NULL\n")
                f.write(f"FROM llx_categorie c\n")
                f.write(f"WHERE c.label = {cat_princ_esc} AND c.type = {TYPE} AND c.fk_parent = 0;\n")
            f.write("\n")

            # ---- 3. Asociar cada producto a su marca ----
            f.write("-- 3. Asociar productos a su marca (subcategoría)\n")
            for idx, row in df.iterrows():
                codigo = str(row[COL_CODIGO]).strip()
                marca = str(row[COL_MARCA]).strip()

                if not codigo or not marca:
                    continue

                codigo_esc = escape_sql(codigo)
                marca_esc = escape_sql(marca)

                # Obtenemos el ID de la categoría (marca) que es subcategoría de 'Marcas'
                f.write(f"-- Producto {codigo} -> Marca {marca}\n")
                f.write("INSERT IGNORE INTO llx_categorie_product (fk_categorie, fk_product)\n")
                f.write("SELECT cat.rowid, p.rowid\n")
                f.write("FROM llx_categorie cat, llx_product p\n")
                f.write(f"WHERE cat.label = {marca_esc} AND cat.type = {TYPE}\n")
                f.write("  AND cat.fk_parent = (\n")
                f.write("      SELECT c2.rowid FROM llx_categorie c2\n")
                f.write(f"      WHERE c2.label = {cat_princ_esc} AND c2.type = {TYPE} AND c2.fk_parent = 0\n")
                f.write("  )\n")
                f.write(f"  AND p.ref = {codigo_esc};\n")

                # Mostrar progreso cada 100 productos
                if (idx + 1) % 100 == 0:
                    f.write("\n")   # Separador visual en el SQL
                    print(f"    Procesados {idx + 1} de {total_productos} productos...")

            f.write("\nCOMMIT;\n")

        print(f"\n ✅ Archivo SQL generado exitosamente:")
        print(f"    {ARCHIVO_SALIDA}")
        print(f"    Total productos procesados: {total_productos}")
        print(f"    Total marcas únicas: {len(marcas_unicas)}")

    except Exception as e:
        print(f" ❌ Error al escribir el archivo SQL: {e}")
        return

    print("=" * 70)
    print(" ✨ Proceso completado. Revisa el archivo SQL y ejecútalo en phpMyAdmin.")
    print("=" * 70)

if __name__ == "__main__":
    main()