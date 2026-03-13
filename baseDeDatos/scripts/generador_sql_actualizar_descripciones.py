#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script: generador_sql_actualizar_descripciones.py
Propósito: Genera un archivo SQL para actualizar las descripciones (larga y corta)
           de productos en Dolibarr a partir de un archivo CSV.

Entrada: Archivo CSV separado por ';' con las columnas:
         - Código     : referencia del producto.
         - Desc_Corta : nueva descripción corta (para extrafields).
         - Desc_Larga : nueva descripción larga (para tabla llx_product).

Salida: Archivo SQL con nombre dinámico (fecha y hora) en la carpeta 'data/output/'.
        El SQL realiza las siguientes operaciones por producto:
           - Actualiza description en llx_product (si Desc_Larga no está vacía).
           - Inserta o actualiza el extrafield 'descripcion_corta' en llx_product_extrafields
             (si Desc_Corta no está vacía, la establece; si está vacía, la pone a NULL).

Uso:
    1. Colocar el archivo CSV en la ruta especificada en ARCHIVO_ENTRADA.
    2. Ajustar los nombres de columna en las constantes COL_CODIGO, COL_DESC_CORTA, COL_DESC_LARGA.
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
ARCHIVO_SALIDA = f"data/output/update_descripciones_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"

SEP = ';'                     # Separador de columnas en el CSV
ENCODING = 'utf-8'            # Codificación del archivo CSV

# Nombres exactos de las columnas en el CSV (deben coincidir)
COL_CODIGO = 'Código'         # Columna con la referencia del producto
COL_DESC_CORTA = 'Desc_Corta' # Columna con la descripción corta
COL_DESC_LARGA = 'Desc_Larga' # Columna con la descripción larga

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
# FUNCIÓN PRINCIPAL
# =============================================================================
def main():
    """Función principal que orquesta la lectura, validación y generación del SQL."""
    print("=" * 70)
    print(" 📂 GENERADOR SQL: ACTUALIZACIÓN DE DESCRIPCIONES DE PRODUCTOS")
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
    necesarias = [COL_CODIGO, COL_DESC_CORTA, COL_DESC_LARGA]
    faltan = [c for c in necesarias if c not in df.columns]
    if faltan:
        print(f" ❌ El CSV debe contener las columnas: {', '.join(necesarias)}")
        print(f"    Faltan: {', '.join(faltan)}")
        print("   Verifica los nombres (incluyendo mayúsculas, acentos y espacios).")
        return

    total = len(df)
    print(f"\n ✅ Productos a procesar: {total}")

    if total == 0:
        print("\n ⚠️  No hay productos para procesar. Saliendo.")
        return

    # Crear la carpeta de salida si no existe (para evitar errores)
    try:
        os.makedirs("data/output", exist_ok=True)
    except Exception as e:
        print(f" ❌ Error al crear la carpeta de salida: {e}")
        return

    # =========================================================================
    # GENERACIÓN DEL ARCHIVO SQL
    # =========================================================================
    try:
        with open(ARCHIVO_SALIDA, 'w', encoding='utf-8') as f:
            # Cabecera del archivo SQL
            f.write("-- =========================================================\n")
            f.write("-- ACTUALIZACIÓN DE DESCRIPCIONES DE PRODUCTOS\n")
            f.write(f"-- Generado el {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("-- =========================================================\n\n")
            f.write("START TRANSACTION;\n\n")

            # Iterar sobre cada fila y generar sentencias SQL
            for idx, row in df.iterrows():
                ref = str(row[COL_CODIGO]).strip()
                if ref == '':
                    continue   # Saltar filas sin código

                desc_larga = escape_sql(row.get(COL_DESC_LARGA))
                desc_corta = escape_sql(row.get(COL_DESC_CORTA))

                f.write(f"-- Producto ref: {ref}\n")

                # 1. Actualizar descripción larga en llx_product
                if desc_larga != "NULL":
                    f.write(f"UPDATE llx_product SET description = {desc_larga} WHERE ref = '{ref}';\n")
                else:
                    f.write(f"-- Descripción larga vacía, no se actualiza.\n")

                # 2. Actualizar/insertar descripción corta en extrafields
                if desc_corta != "NULL":
                    # Insertar si no existe, actualizar si ya existe
                    f.write(f"INSERT INTO llx_product_extrafields (fk_object, descripcion_corta)\n")
                    f.write(f"SELECT rowid, {desc_corta} FROM llx_product WHERE ref = '{ref}'\n")
                    f.write(f"ON DUPLICATE KEY UPDATE descripcion_corta = VALUES(descripcion_corta);\n")
                else:
                    # Si la descripción corta está vacía, la ponemos a NULL
                    f.write(f"UPDATE llx_product_extrafields SET descripcion_corta = NULL\n")
                    f.write(f"WHERE fk_object = (SELECT rowid FROM llx_product WHERE ref = '{ref}');\n")

                f.write("\n")

                # Mostrar progreso cada 100 productos
                if (idx + 1) % 100 == 0:
                    print(f"    Procesados {idx + 1} de {total} productos...")

            f.write("COMMIT;\n")

        print(f"\n ✅ Archivo SQL generado exitosamente:")
        print(f"    {ARCHIVO_SALIDA}")
        print(f"    Total productos procesados: {total}")

    except Exception as e:
        print(f" ❌ Error al escribir el archivo SQL: {e}")
        return

    print("=" * 70)
    print(" ✨ Proceso completado. Revisa el archivo SQL y ejecútalo en phpMyAdmin.")
    print("=" * 70)


if __name__ == "__main__":
    main()