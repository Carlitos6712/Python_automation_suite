#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script: normalizar_nombres_productos_con_lote.py
Propósito: Lee un archivo CSV, normaliza una columna específica (primera letra mayúscula,
           resto minúsculas) y añade un prefijo de lote basado en el número de fila.

Entrada: Archivo CSV con al menos la columna especificada (por defecto 'Label').
         Cada fila se procesa secuencialmente; se asigna un número de lote según
         el tamaño de lote configurado (por defecto 50 productos por lote).

Proceso:
    - Lee el CSV con cabecera.
    - Para cada fila, normaliza el valor de la columna indicada.
    - Calcula el número de lote: ((índice_fila - 1) // lote_tamano) + 1.
    - Prefiija el nombre con "lote-".
    - Escribe la fila modificada en un nuevo CSV.

Salida: Archivo CSV con la misma estructura, pero con la columna de nombre modificada.

Uso:
    1. Ajustar las constantes INPUT_CSV y OUTPUT_CSV en la sección de configuración.
    2. Asegurar que el archivo de entrada existe y tiene la columna esperada.
    3. Ejecutar el script.
"""

import csv
import os

# =============================================================================
# FUNCIONES AUXILIARES
# =============================================================================
def normalizar_nombre(nombre):
    """
    Normaliza un nombre:
        - Convierte a string (por si acaso hay valores no string).
        - Elimina espacios al inicio y final.
        - Primera letra en mayúscula, el resto en minúscula.
    """
    if not isinstance(nombre, str):
        nombre = str(nombre)  # por si acaso hay valores no string
    return nombre.strip().capitalize()

def procesar_csv(archivo_entrada, archivo_salida, columna_nombre='Label', lote_tamano=50):
    """
    Lee un CSV, normaliza la columna indicada y añade un prefijo de lote.

    Parámetros:
        archivo_entrada (str): Ruta al archivo CSV original.
        archivo_salida (str): Ruta donde se guardará el nuevo CSV.
        columna_nombre (str): Nombre de la columna que contiene los nombres.
        lote_tamano (int): Cantidad de productos por lote.

    Retorna:
        None. Crea el archivo de salida o muestra errores si ocurren.
    """
    # Verificar que el archivo de entrada existe
    if not os.path.exists(archivo_entrada):
        print(f" ❌ ERROR: No se encuentra el archivo '{archivo_entrada}'.")
        return

    # Crear carpeta de salida si no existe
    try:
        os.makedirs(os.path.dirname(archivo_salida) or '.', exist_ok=True)
    except Exception as e:
        print(f" ❌ Error al crear la carpeta de salida: {e}")
        return

    try:
        with open(archivo_entrada, mode='r', encoding='utf-8') as f_in, \
             open(archivo_salida, mode='w', encoding='utf-8', newline='') as f_out:

            lector = csv.reader(f_in)
            escritor = csv.writer(f_out)

            # Leer cabecera
            try:
                cabecera = next(lector)
            except StopIteration:
                print(" ⚠️  El archivo está vacío.")
                return

            # Buscar índice de la columna de nombres
            if columna_nombre not in cabecera:
                print(f" ❌ Error: No se encontró la columna '{columna_nombre}' en el CSV.")
                print(f"    Cabeceras disponibles: {cabecera}")
                return

            idx_nombre = cabecera.index(columna_nombre)
            escritor.writerow(cabecera)  # escribir cabecera igual

            # Procesar filas
            total_filas = 0
            for i, fila in enumerate(lector, start=1):  # i = número de fila (1-based)
                if len(fila) <= idx_nombre:
                    # Si la fila no tiene suficientes columnas, se omite
                    print(f" ⚠️  Advertencia: fila {i+1} incompleta, se omite.")
                    continue

                # Normalizar nombre
                nombre_original = fila[idx_nombre]
                nombre_normalizado = normalizar_nombre(nombre_original)

                # Calcular número de lote (1-based)
                numero_lote = ((i - 1) // lote_tamano) + 1

                # Añadir prefijo
                fila[idx_nombre] = f"{numero_lote}-{nombre_normalizado}"

                # Escribir fila modificada
                escritor.writerow(fila)
                total_filas += 1

            print(f" ✅ Procesamiento completado. Archivo guardado como: {archivo_salida}")
            print(f"    Total filas procesadas (sin cabecera): {total_filas}")

    except Exception as e:
        print(f" ❌ Error durante el procesamiento: {e}")

# =============================================================================
# PUNTO DE ENTRADA PRINCIPAL
# =============================================================================
def main():
    """Configura los parámetros y ejecuta el procesamiento del CSV."""
    print("=" * 70)
    print(" 🏷️  NORMALIZADOR DE NOMBRES DE PRODUCTOS CON PREFIJO DE LOTE")
    print("=" * 70)

    # ===== CONFIGURACIÓN (modificar según necesidades) =====
    INPUT_CSV = 'data/output/archivo.csv'
    OUTPUT_CSV = 'data/output/productos_normalizados.csv'
    COLUMNA_NOMBRE = 'Label'
    LOTE_TAMANO = 50

    print(f" 📄 Archivo de entrada: {INPUT_CSV}")
    print(f" 📁 Archivo de salida: {OUTPUT_CSV}")
    print(f" 🔤 Columna a normalizar: '{COLUMNA_NOMBRE}'")
    print(f" 📦 Tamaño de lote: {LOTE_TAMANO} productos por lote")

    procesar_csv(INPUT_CSV, OUTPUT_CSV, columna_nombre=COLUMNA_NOMBRE, lote_tamano=LOTE_TAMANO)

    print("=" * 70)
    print(" ✨ Proceso completado.")
    print("=" * 70)

if __name__ == '__main__':
    main()