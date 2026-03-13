#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script: dividir_csv.py
Propósito: Divide un archivo CSV grande en varias partes más pequeñas.
           La cabecera se incluye en todos los archivos de salida.

Entrada: Archivo CSV con cualquier delimitador (por defecto coma).

Salida: Archivos CSV con nombres como '<prefijo>_1.csv', '<prefijo>_2.csv', etc.
        Cada archivo contiene la cabecera original y un subconjunto de filas.

Uso:
    python dividir_csv.py --input productos.csv --output data/parte --num-partes 3
"""

import argparse
import csv
import os
import math

# =============================================================================
# FUNCIÓN PRINCIPAL DE DIVISIÓN
# =============================================================================
def dividir_csv(archivo_entrada, num_partes=2, prefijo_salida="parte", delimitador=',', encoding='utf-8'):
    """
    Divide un archivo CSV en 'num_partes' archivos más pequeños.
    Cada archivo contiene la cabecera y un subconjunto de filas.

    Parámetros:
        archivo_entrada (str): Ruta al archivo CSV de entrada.
        num_partes (int): Número de partes a generar.
        prefijo_salida (str): Prefijo para los nombres de archivo de salida.
                              Puede incluir una ruta (ej. "data/salida/parte").
        delimitador (str): Carácter separador de columnas en el CSV.
        encoding (str): Codificación del archivo.

    Retorna:
        None. Crea los archivos en el sistema de archivos.
    """
    # Leer todas las filas del CSV
    try:
        with open(archivo_entrada, mode='r', encoding=encoding) as f:
            lector = csv.reader(f, delimiter=delimitador)
            filas = list(lector)
    except FileNotFoundError:
        print(f" ❌ Error: No se encuentra el archivo '{archivo_entrada}'.")
        return
    except Exception as e:
        print(f" ❌ Error al leer el archivo: {e}")
        return

    if not filas:
        print(" ⚠️  El archivo está vacío.")
        return

    cabecera = filas[0]
    datos = filas[1:]  # Filas de datos (sin cabecera)
    total_filas = len(datos)

    if total_filas == 0:
        print(" ⚠️  El archivo solo tiene cabecera, no hay datos para dividir.")
        return

    # Calcular filas por parte (aproximadamente, redondeando hacia arriba)
    filas_por_parte = math.ceil(total_filas / num_partes)

    # Asegurar que el directorio de salida exista (si el prefijo contiene una ruta)
    directorio_salida = os.path.dirname(prefijo_salida)
    if directorio_salida and not os.path.exists(directorio_salida):
        try:
            os.makedirs(directorio_salida)
            print(f" 📁 Directorio creado: {directorio_salida}")
        except Exception as e:
            print(f" ❌ Error al crear el directorio '{directorio_salida}': {e}")
            return

    print(f"\n 📊 Total de filas de datos: {total_filas}")
    print(f" 🔪 Dividiendo en {num_partes} partes...\n")

    # Generar archivos de salida
    archivos_generados = 0
    for i in range(num_partes):
        inicio = i * filas_por_parte
        fin = min((i + 1) * filas_por_parte, total_filas)
        if inicio >= total_filas:
            break  # No más filas

        nombre_salida = f"{prefijo_salida}_{i+1}.csv"
        try:
            with open(nombre_salida, mode='w', encoding=encoding, newline='') as f_out:
                escritor = csv.writer(f_out, delimiter=delimitador)
                # Escribir cabecera
                escritor.writerow(cabecera)
                # Escribir bloque de datos
                for fila in datos[inicio:fin]:
                    escritor.writerow(fila)
            archivos_generados += 1
            print(f"   ✅ {nombre_salida} : {fin - inicio} filas de datos")
        except Exception as e:
            print(f"   ❌ Error al escribir {nombre_salida}: {e}")

    print(f"\n ✅ Proceso completado. {archivos_generados} archivo(s) generado(s).")


# =============================================================================
# PUNTO DE ENTRADA PRINCIPAL
# =============================================================================
def main():
    """Procesa argumentos de línea de comandos y ejecuta la división."""
    parser = argparse.ArgumentParser(
        description="Divide un archivo CSV en varias partes, manteniendo la cabecera en cada una."
    )
    parser.add_argument('--input', '-i', required=True,
                        help='Ruta del archivo CSV de entrada')
    parser.add_argument('--output', '-o', default='parte',
                        help='Prefijo para los archivos de salida (puede incluir ruta, ej. "data/salida/parte"). Por defecto: "parte"')
    parser.add_argument('--num-partes', '-n', type=int, default=2,
                        help='Número de partes en las que dividir (por defecto: 2)')
    parser.add_argument('--delimiter', '-d', default=',',
                        help='Delimitador del CSV (por defecto: coma)')
    parser.add_argument('--encoding', '-e', default='utf-8',
                        help='Codificación del archivo (por defecto: utf-8)')
    args = parser.parse_args()

    print("=" * 70)
    print(" ✂️  DIVISOR DE ARCHIVOS CSV")
    print("=" * 70)

    print(f" 📄 Archivo de entrada: {args.input}")
    print(f" 📁 Prefijo de salida: {args.output}")
    print(f" 🔢 Número de partes: {args.num_partes}")
    print(f" 🔤 Delimitador: '{args.delimiter}'")
    print(f" 🔤 Codificación: {args.encoding}")

    dividir_csv(
        archivo_entrada=args.input,
        num_partes=args.num_partes,
        prefijo_salida=args.output,
        delimitador=args.delimiter,
        encoding=args.encoding
    )

    print("=" * 70)


if __name__ == "__main__":
    main()