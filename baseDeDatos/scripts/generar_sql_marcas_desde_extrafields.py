#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script: generar_sql_marcas_desde_extrafields.py
Propósito: Genera un archivo SQL para asociar productos con categorías de marca
           en Dolibarr, a partir de un archivo CSV exportado de llx_product_extrafields.

Entrada: Archivo CSV que debe contener al menos las columnas:
         - fk_object (ID del producto)
         - marca    (nombre de la marca)

Proceso:
         - Lee el CSV y extrae pares (fk_object, marca).
         - Genera un script SQL que:
              * Inserta en llx_categorie las marcas que aún no existen.
              * Inserta en llx_categorie_product las relaciones producto-marca.
         - Utiliza subconsultas con UNION ALL para incluir los datos del CSV.

Salida: Archivo SQL con las instrucciones (por defecto 'marcas_a_categorias.sql').

Uso:
    python generar_sql_marcas_desde_extrafields.py --csv extrafields.csv [--output marcas.sql] [--delimiter ',']
"""

import argparse
import csv
import sys
import os

# =============================================================================
# FUNCIONES AUXILIARES
# =============================================================================

def escapar_sql(valor):
    """
    Escapa comillas simples para su uso seguro en sentencias SQL.
    Si el valor es None retorna 'NULL', de lo contrario lo envuelve entre comillas.
    """
    if valor is None:
        return "NULL"
    return "'" + str(valor).replace("'", "''") + "'"

def leer_csv(archivo, delimitador=','):
    """
    Lee el archivo CSV y devuelve una lista de tuplas (fk_object, marca)
    donde la marca no está vacía.
    
    Parámetros:
        archivo (str): Ruta al archivo CSV.
        delimitador (str): Carácter separador de columnas.
    
    Retorna:
        list: Lista de tuplas (fk_object (int), marca (str)).
    
    Si las columnas no se encuentran o hay errores, termina el programa.
    """
    productos_marcas = []
    try:
        with open(archivo, mode='r', encoding='utf-8') as f:
            # Leer CSV y normalizar nombres de columna (minúsculas, sin espacios)
            lector = csv.DictReader(f, delimiter=delimitador)
            # Identificar las columnas 'fk_object' y 'marca' de forma flexible
            campo_fk = None
            campo_marca = None
            for col in lector.fieldnames:
                col_lower = col.lower().strip()
                if 'fk_object' in col_lower or 'fkobject' in col_lower:
                    campo_fk = col
                if 'marca' in col_lower:
                    campo_marca = col
            if not campo_fk or not campo_marca:
                print(f" ❌ Error: No se encontraron las columnas 'fk_object' y 'marca' en el CSV.")
                print(f"    Columnas disponibles: {lector.fieldnames}")
                sys.exit(1)

            # Procesar cada fila
            for fila in lector:
                fk_object = fila.get(campo_fk)
                marca = fila.get(campo_marca, '').strip()
                if fk_object and marca:  # Solo si ambos tienen valor
                    try:
                        fk_object = int(fk_object)  # Asegurar que sea entero
                        productos_marcas.append((fk_object, marca))
                    except ValueError:
                        print(f" ⚠️  Advertencia: fk_object no es un número válido: '{fk_object}'. Se omite.")
    except FileNotFoundError:
        print(f" ❌ Error: No se encuentra el archivo '{archivo}'.")
        sys.exit(1)
    except Exception as e:
        print(f" ❌ Error al leer el CSV: {e}")
        sys.exit(1)

    return productos_marcas

def generar_script_sql(productos_marcas, output_file):
    """
    Genera un archivo SQL con las instrucciones para:
        - Insertar en llx_categorie las marcas que aún no existen.
        - Insertar en llx_categorie_product las relaciones.
    
    Utiliza subconsultas con UNION ALL para incluir los datos del CSV.
    
    Parámetros:
        productos_marcas (list): Lista de tuplas (fk_object, marca).
        output_file (str): Ruta del archivo SQL de salida.
    """
    if not productos_marcas:
        print(" ⚠️  No se encontraron productos con marca definida. No se generará archivo.")
        return

    # Extraer marcas únicas y ordenarlas
    marcas_unicas = sorted(set(marca for _, marca in productos_marcas))

    # Crear carpeta de salida si no existe
    try:
        os.makedirs(os.path.dirname(output_file) or '.', exist_ok=True)
    except Exception as e:
        print(f" ❌ Error al crear la carpeta de salida: {e}")
        return

    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            # Cabecera del archivo SQL
            f.write("-- =========================================================\n")
            f.write("-- ASOCIACIÓN DE PRODUCTOS CON CATEGORÍAS DE MARCA\n")
            f.write("-- Script generado automáticamente a partir de CSV\n")
            f.write(f"-- Total productos con marca: {len(productos_marcas)}\n")
            f.write(f"-- Total marcas únicas: {len(marcas_unicas)}\n")
            f.write("-- =========================================================\n\n")
            f.write("START TRANSACTION;\n\n")

            # --- 1. Insertar categorías de marca (si no existen) ---
            f.write("-- 1. Insertar categorías de marca faltantes\n")
            f.write("INSERT INTO llx_categorie (label, type, description, fk_parent, visible, import_key)\n")
            f.write("SELECT DISTINCT v.marca, 'product', '', 0, 1, NULL\n")
            f.write("FROM (\n")
            # Escribir cada marca como una fila SELECT
            for i, marca in enumerate(marcas_unicas):
                linea = f"    SELECT {escapar_sql(marca)} AS marca"
                if i < len(marcas_unicas) - 1:
                    linea += " UNION ALL"
                f.write(linea + "\n")
            f.write(") v\n")
            f.write("WHERE NOT EXISTS (\n")
            f.write("    SELECT 1 FROM llx_categorie c\n")
            f.write("    WHERE c.label = v.marca AND c.type = 'product'\n")
            f.write(");\n\n")

            # --- 2. Insertar relaciones producto-categoría (si no existen) ---
            f.write("-- 2. Insertar relaciones producto-categoría\n")
            f.write("INSERT IGNORE INTO llx_categorie_product (fk_categorie, fk_product)\n")
            f.write("SELECT c.rowid, v.fk_object\n")
            f.write("FROM (\n")
            # Escribir cada par (fk_object, marca) como fila
            for i, (fk_obj, marca) in enumerate(productos_marcas):
                linea = f"    SELECT {fk_obj} AS fk_object, {escapar_sql(marca)} AS marca"
                if i < len(productos_marcas) - 1:
                    linea += " UNION ALL"
                f.write(linea + "\n")
            f.write(") v\n")
            f.write("JOIN llx_categorie c ON c.label = v.marca AND c.type = 'product'\n")
            f.write("WHERE NOT EXISTS (\n")
            f.write("    SELECT 1 FROM llx_categorie_product cp\n")
            f.write("    WHERE cp.fk_categorie = c.rowid AND cp.fk_product = v.fk_object\n")
            f.write(");\n\n")

            f.write("COMMIT;\n")

        print(f" ✅ Archivo SQL generado exitosamente:")
        print(f"    {output_file}")
        print(f"    Total productos con marca: {len(productos_marcas)}")
        print(f"    Total marcas únicas: {len(marcas_unicas)}")

    except Exception as e:
        print(f" ❌ Error al escribir el archivo SQL: {e}")
        sys.exit(1)


# =============================================================================
# FUNCIÓN PRINCIPAL
# =============================================================================
def main():
    """Punto de entrada: procesa argumentos y ejecuta la generación del SQL."""
    parser = argparse.ArgumentParser(
        description="Genera un script SQL para asociar marcas con categorías de producto a partir de un CSV."
    )
    parser.add_argument('--csv', required=True,
                        help='Ruta al archivo CSV exportado de llx_product_extrafields')
    parser.add_argument('--output', default='marcas_a_categorias.sql',
                        help='Archivo SQL de salida (por defecto: marcas_a_categorias.sql)')
    parser.add_argument('--delimiter', default=',',
                        help='Delimitador del CSV (por defecto: coma)')
    args = parser.parse_args()

    print("=" * 70)
    print(" 🏷️  GENERADOR SQL: ASOCIAR MARCAS CON CATEGORÍAS DE PRODUCTO")
    print("=" * 70)

    print(f" 📄 Leyendo CSV: {args.csv}")
    print(f" 🔍 Delimitador: '{args.delimiter}'")

    productos_marcas = leer_csv(args.csv, args.delimiter)
    generar_script_sql(productos_marcas, args.output)

    print("=" * 70)
    print(" ✨ Proceso completado. Revisa el archivo SQL y ejecútalo en phpMyAdmin.")
    print("=" * 70)


if __name__ == "__main__":
    main()