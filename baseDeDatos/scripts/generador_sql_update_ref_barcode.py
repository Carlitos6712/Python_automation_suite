#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script: generador_sql_update_ref_barcode.py
Propósito: Genera un archivo SQL con sentencias UPDATE para actualizar
           los campos 'ref' y 'barcode' de la tabla 'llx_product' en Dolibarr.

Entrada: Archivo CSV separado por ';' con las columnas:
         - Código   : Nuevo valor para ref y barcode.
         - Ref      : Valor actual de ref que se usará en la condición WHERE.

Salida: Archivo SQL con nombre dinámico (fecha y hora) en la carpeta 'data/output/'.
        Cada sentencia generada tiene la forma:
            UPDATE llx_product SET ref = 'nuevo_codigo', barcode = 'nuevo_codigo'
            WHERE ref = 'antigua_ref';

Uso:
    1. Colocar el archivo CSV en la ruta especificada en ARCHIVO_ENTRADA.
    2. Ejecutar el script.
    3. Revisar el archivo SQL generado y ejecutarlo en phpMyAdmin o herramienta similar.
"""

import pandas as pd
import os
from datetime import datetime

# =============================================================================
# CONFIGURACIÓN DEL USUARIO (modificar según necesidades)
# =============================================================================
ARCHIVO_ENTRADA = "data/input/archivo.csv"   # Ruta al CSV de entrada
ARCHIVO_SALIDA = f"data/output/update_ref_barcode_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"

SEP = ','                     # Separador de columnas en el CSV
ENCODING = 'utf-8'            # Codificación del archivo CSV

# Nombres exactos de las columnas en el CSV (deben coincidir)
COL_CODIGO = 'Código'         # Columna con el nuevo código
COL_REF_ANTIGUA = 'Ref'        # Columna con la referencia actual

# =============================================================================
# INICIO DEL PROCESO
# =============================================================================
def main():
    """Función principal que orquesta la lectura, validación y generación del SQL."""
    print("=" * 70)
    print(" 🔄 GENERADOR SQL PARA ACTUALIZAR ref Y barcode EN llx_product")
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
    if COL_CODIGO not in df.columns or COL_REF_ANTIGUA not in df.columns:
        print(f" ❌ El CSV debe contener las columnas '{COL_CODIGO}' y '{COL_REF_ANTIGUA}'.")
        print("   Verifica los nombres (incluyendo mayúsculas, acentos y espacios).")
        return

    # Eliminar filas con valores nulos o vacíos en las columnas clave
    # Esto evita generar sentencias SQL inválidas.
    df = df.dropna(subset=[COL_CODIGO, COL_REF_ANTIGUA])
    df = df[df[COL_CODIGO].astype(str).str.strip() != '']
    df = df[df[COL_REF_ANTIGUA].astype(str).str.strip() != '']

    total = len(df)
    print(f"\n ✅ Registros válidos a procesar: {total}")

    # Mostrar una muestra de los primeros registros para confirmar
    if total > 0:
        print("\n 🔍 Primeros 5 registros (antigua_ref -> nuevo_código):")
        for i, row in df.head(5).iterrows():
            antigua = str(row[COL_REF_ANTIGUA]).strip()
            nuevo = str(row[COL_CODIGO]).strip()
            print(f"    {antigua} -> {nuevo}")
    else:
        print("\n ⚠️  No hay registros para procesar después de limpiar vacíos.")
        return

    # =========================================================================
    # GENERACIÓN DEL ARCHIVO SQL
    # =========================================================================
    try:
        with open(ARCHIVO_SALIDA, 'w', encoding='utf-8') as f:
            # Cabecera del archivo SQL
            f.write("-- =========================================================\n")
            f.write("-- ACTUALIZACIÓN DE REF Y BARCODE EN llx_product\n")
            f.write(f"-- Generado el {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("-- =========================================================\n\n")
            f.write("START TRANSACTION;\n\n")

            # Iterar sobre cada fila y escribir sentencia UPDATE
            for idx, row in df.iterrows():
                codigo = str(row[COL_CODIGO]).strip()
                ref_antigua = str(row[COL_REF_ANTIGUA]).strip()

                # Escapar comillas simples para evitar errores de sintaxis SQL
                codigo_esc = codigo.replace("'", "''")
                ref_antigua_esc = ref_antigua.replace("'", "''")

                f.write(f"-- Actualizar producto con ref '{ref_antigua}'\n")
                f.write(f"UPDATE llx_product SET\n")
                f.write(f"    ref = '{codigo_esc}',\n")
                f.write(f"    barcode = '{codigo_esc}'\n")
                f.write(f"WHERE ref = '{ref_antigua_esc}';\n\n")

                # Mostrar progreso cada 100 registros
                if (idx + 1) % 100 == 0:
                    print(f"    Procesados {idx + 1} de {total}...")

            f.write("COMMIT;\n")

        print(f"\n ✅ Archivo SQL generado exitosamente:")
        print(f"    {ARCHIVO_SALIDA}")
        print(f"    Total de sentencias UPDATE: {total}")

    except Exception as e:
        print(f" ❌ Error al escribir el archivo SQL: {e}")
        return

    print("=" * 70)
    print(" ✨ Proceso completado. Revisa el archivo SQL y ejecútalo en phpMyAdmin.")
    print("=" * 70)

if __name__ == "__main__":
    main()