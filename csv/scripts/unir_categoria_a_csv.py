#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script: unir_categoria_a_csv.py
Propósito: Añade una columna de categoría a un archivo CSV base (B) a partir de
           otro archivo CSV (A) que contiene la correspondencia entre una clave
           (por defecto 'Código') y la categoría.

Entrada:
    - Archivo A: CSV que contiene al menos las columnas 'clave' y 'categoría'.
    - Archivo B: CSV base al que se le añadirá la columna de categoría.

Proceso:
    - Lee ambos archivos con codificación utf-8-sig (maneja BOM).
    - Limpia los nombres de columna eliminando caracteres de control y espacios.
    - Construye un diccionario desde el archivo A: clave -> categoría.
    - Lee el archivo B y, para cada fila, busca la categoría correspondiente
      usando la clave; si no existe, deja vacío.
    - Escribe el archivo de salida con la nueva columna añadida al final.

Salida: Archivo CSV con la misma estructura que B, más la columna de categoría.

Uso:
    python unir_categoria_a_csv.py -a categorias.csv -b productos.csv -o productos_con_cat.csv
"""

import csv
import argparse
import sys
import re

# =============================================================================
# FUNCIONES AUXILIARES
# =============================================================================
def clean_column_name(name):
    """
    Elimina caracteres de control (como BOM) y espacios al inicio/final.
    Útil para normalizar nombres de columna que pueden contener caracteres
    no imprimibles en archivos con BOM.
    """
    # Eliminar caracteres no imprimibles (incluyendo BOM)
    name = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', name)
    return name.strip()

# =============================================================================
# FUNCIÓN PRINCIPAL
# =============================================================================
def main():
    """Procesa los argumentos, lee los CSVs, realiza el cruce y escribe el resultado."""
    parser = argparse.ArgumentParser(
        description='Añade campo categoría desde un CSV a otro (UTF-8 con BOM)'
    )
    parser.add_argument('-a', '--archivo_a', required=True,
                        help='CSV A (con categoría)')
    parser.add_argument('-b', '--archivo_b', required=True,
                        help='CSV B (base)')
    parser.add_argument('-o', '--output', required=True,
                        help='Archivo de salida')
    parser.add_argument('--clave', default='Código',
                        help='Columna clave en ambos CSVs (por defecto: Código)')
    parser.add_argument('--clave_b',
                        help='Columna clave en CSV B (si es distinta a clave)')
    parser.add_argument('--col_categoria', default='Categoria',
                        help='Nombre de la columna de categoría en CSV A')
    parser.add_argument('--delimitador_a', default=',',
                        help='Delimitador para archivo A (por defecto: ;)')
    parser.add_argument('--delimitador_b', default=',',
                        help='Delimitador para archivo B (por defecto: ,)')

    args = parser.parse_args()

    # Asignar variables con nombres más claros (aunque mantenemos los originales)
    delim_a = args.delimitador_a
    delim_b = args.delimitador_b
    clave_a = args.clave
    clave_b = args.clave_b if args.clave_b else args.clave
    col_cat = args.col_categoria

    print("=" * 70)
    print(" 🔗 UNIR CATEGORÍA A ARCHIVO CSV")
    print("=" * 70)
    print(f" 📄 Archivo A (categorías): {args.archivo_a}")
    print(f" 📄 Archivo B (base): {args.archivo_b}")
    print(f" 📁 Archivo de salida: {args.output}")
    print(f" 🔑 Clave en A: '{clave_a}'")
    print(f" 🔑 Clave en B: '{clave_b}'")
    print(f" 🏷️  Columna categoría: '{col_cat}'")
    print(f" 🔤 Delimitador A: '{delim_a}'")
    print(f" 🔤 Delimitador B: '{delim_b}'")
    print("=" * 70)

    # --- 1. Leer archivo A (categorías) con limpieza de nombres de columna ---
    categoria_dict = {}
    try:
        with open(args.archivo_a, mode='r', encoding='utf-8-sig') as fa:
            reader = csv.DictReader(fa, delimiter=delim_a)
            # Limpiar nombres de campo
            original_fieldnames = reader.fieldnames
            reader.fieldnames = [clean_column_name(name) for name in reader.fieldnames]
            print("\n 📋 Columnas en A (después de limpiar):", reader.fieldnames)

            if clave_a not in reader.fieldnames:
                print(f" ❌ Error: La columna clave '{clave_a}' no existe en A después de limpiar.")
                print(f"    Columnas disponibles: {reader.fieldnames}")
                sys.exit(1)
            if col_cat not in reader.fieldnames:
                print(f" ❌ Error: La columna categoría '{col_cat}' no existe en A.")
                print(f"    Columnas disponibles: {reader.fieldnames}")
                sys.exit(1)

            for row in reader:
                key = row[clave_a].strip()
                categoria_dict[key] = row[col_cat].strip()

            # Mostrar algunas claves para depuración
            print(f"    Se cargaron {len(categoria_dict)} claves desde A.")
            print("    Primeras 5 claves en A:", list(categoria_dict.keys())[:5])
    except FileNotFoundError:
        print(f" ❌ Error: No se encuentra el archivo '{args.archivo_a}'.")
        sys.exit(1)
    except Exception as e:
        print(f" ❌ Error al leer archivo A: {e}")
        sys.exit(1)

    # --- 2. Leer archivo B y escribir resultado ---
    try:
        with open(args.archivo_b, mode='r', encoding='utf-8-sig') as fb, \
             open(args.output, mode='w', encoding='utf-8-sig', newline='') as fo:

            reader = csv.DictReader(fb, delimiter=delim_b)
            # Limpiar nombres de campo en B por si acaso
            reader.fieldnames = [clean_column_name(name) for name in reader.fieldnames]
            print("\n 📋 Columnas en B (después de limpiar):", reader.fieldnames)

            if clave_b not in reader.fieldnames:
                print(f" ❌ Error: La columna clave '{clave_b}' no existe en B.")
                print(f"    Columnas disponibles: {reader.fieldnames}")
                sys.exit(1)

            # Añadir nueva columna a la cabecera
            fieldnames = reader.fieldnames + [col_cat]
            writer = csv.DictWriter(fo, fieldnames=fieldnames, delimiter=delim_b)
            writer.writeheader()

            contador = 0
            print("\n 🔍 Ejemplos de cruce (primeras 5 filas):")
            for row in reader:
                key = row[clave_b].strip()
                categoria = categoria_dict.get(key, '')
                # Depuración: mostrar algunos ejemplos
                if contador < 5:
                    print(f"    Clave B: '{key}' -> Categoría: '{categoria}'")
                row[col_cat] = categoria
                writer.writerow(row)
                contador += 1

        print(f"\n ✅ Proceso completado. Archivo guardado en: {args.output}")
        print(f"    Total de filas procesadas en B: {contador}")
    except FileNotFoundError:
        print(f" ❌ Error: No se encuentra el archivo '{args.archivo_b}'.")
        sys.exit(1)
    except Exception as e:
        print(f" ❌ Error al procesar archivo B o escribir salida: {e}")
        sys.exit(1)

    print("=" * 70)
    print(" ✨ ¡CRUCE FINALIZADO!")
    print("=" * 70)


if __name__ == '__main__':
    main()