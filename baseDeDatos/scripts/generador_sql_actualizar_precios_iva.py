#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script: generador_sql_actualizar_precios_iva.py
Propósito: Genera un archivo SQL para actualizar el precio con IVA (price_ttc) 
           de productos en Dolibarr a partir de un archivo CSV.

Entrada: Archivo CSV separado por ';' con las columnas:
         - Código      : referencia del producto.
         - Precio IVA  : precio final con IVA (ej. "14,50" o "14.50").

Proceso por cada producto:
         - Obtiene la última tasa de IVA registrada en llx_product_price.
         - Si no existe, usa un IVA por defecto (configurable).
         - Calcula el precio sin IVA (price_ttc / (1 + IVA/100)).
         - Actualiza los campos price y price_ttc en llx_product.
         - Inserta un nuevo registro en llx_product_price.

Salida: Archivo SQL con nombre dinámico (fecha y hora) en la carpeta 'data/output/'.

Uso:
    1. Colocar el archivo CSV en la ruta especificada en ARCHIVO_ENTRADA.
    2. Ajustar los nombres de columna en las constantes COL_CODIGO y COL_PRECIO_IVA.
    3. Configurar las constantes adicionales según necesidad.
    4. Ejecutar el script.
    5. Revisar el archivo SQL generado y ejecutarlo en phpMyAdmin.
"""

import pandas as pd
import os
import re
from datetime import datetime

# =============================================================================
# CONFIGURACIÓN DEL USUARIO (modificar según necesidades)
# =============================================================================
ARCHIVO_ENTRADA = "data/input/archivo.csv"          # Ruta al CSV de entrada
ARCHIVO_SALIDA = f"data/output/update_precio_iva_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"

SEP = ','                     # Separador del CSV
ENCODING = 'utf-8'            # Codificación del archivo CSV

# Nombres exactos de las columnas en el CSV (deben coincidir)
COL_CODIGO = 'Código'         # Columna con la referencia del producto
COL_PRECIO_IVA = 'Precio IVA' # Columna con el precio con IVA

# Tasa de IVA por defecto si el producto no tiene ningún precio previo
IVA_DEFECTO = 21.0

# Valores fijos para la inserción en llx_product_price
ENTITY = 1
FK_USER_AUTHOR = 1            # ID del usuario admin (ajusta si necesario)
PRICE_LEVEL = 1
PRICE_BASE_TYPE = "'HT'"
RECUPERABLEONLY = 0
LOCALTAX1_TYPE = "'0'"
LOCALTAX2_TYPE = "'0'"
TOSELL = 1
PRICE_BY_QTY = 0
MULTICURRENCY_TX = 1.0

# Control: si el precio es 0, ¿se actualiza? (False = se omite)
ACTUALIZAR_PRECIOS_CERO = False

# =============================================================================
# FUNCIONES AUXILIARES
# =============================================================================
def limpiar_precio(valor):
    """
    Convierte un valor como "14,50" o "14.50" a float.
    Elimina símbolos de moneda, reemplaza coma por punto.
    Si no se puede extraer un número válido, retorna 0.0.
    """
    if pd.isna(valor) or str(valor).strip() == '':
        return 0.0
    s = str(valor).strip()
    # Eliminar cualquier carácter no numérico excepto punto, coma y signo menos
    s = re.sub(r'[^\d.,-]', '', s)
    # Reemplazar coma decimal por punto
    s = s.replace(',', '.')
    # Extraer el primer número válido (incluyendo decimales)
    match = re.search(r'(-?\d+\.?\d*)', s)
    return float(match.group(1)) if match else 0.0

# =============================================================================
# FUNCIÓN PRINCIPAL
# =============================================================================
def main():
    """Función principal que orquesta la lectura, validación y generación del SQL."""
    print("=" * 70)
    print(" 💰 GENERADOR SQL: ACTUALIZAR PRECIOS CON IVA DESDE CSV")
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
    if COL_CODIGO not in df.columns or COL_PRECIO_IVA not in df.columns:
        print(f" ❌ El CSV debe contener las columnas '{COL_CODIGO}' y '{COL_PRECIO_IVA}'.")
        print("   Verifica los nombres (incluyendo mayúsculas, acentos y espacios).")
        return

    # Limpiar y convertir precios
    df['precio_iva'] = df[COL_PRECIO_IVA].apply(limpiar_precio)

    # Eliminar filas con código vacío o nulo
    df = df.dropna(subset=[COL_CODIGO])
    df = df[df[COL_CODIGO].astype(str).str.strip() != '']
    total = len(df)
    print(f"\n ✅ Registros válidos a procesar: {total}")

    if total == 0:
        print("\n ⚠️  No hay registros para procesar después de limpiar vacíos.")
        return

    # Mostrar una muestra de los primeros registros para confirmar
    print("\n 🔍 Primeros 5 registros (Código -> Precio IVA):")
    for i, row in df.head(5).iterrows():
        print(f"    {row[COL_CODIGO]} -> {row['precio_iva']:.2f}")

    # Crear la carpeta de salida si no existe
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
            f.write("-- ACTUALIZACIÓN DE PRECIOS CON IVA\n")
            f.write(f"-- Generado el {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("-- =========================================================\n\n")
            f.write("START TRANSACTION;\n\n")

            # Iterar sobre cada fila y generar sentencias SQL
            for idx, row in df.iterrows():
                codigo = str(row[COL_CODIGO]).strip()
                precio_iva = row['precio_iva']

                if precio_iva == 0.0 and not ACTUALIZAR_PRECIOS_CERO:
                    f.write(f"-- Producto {codigo}: precio 0, se omite.\n\n")
                    continue

                # Escapar posibles comillas simples en el código
                codigo_esc = codigo.replace("'", "''")

                f.write(f"-- Producto {codigo}\n")

                # Obtener el ID del producto y la última tasa de IVA (o usar defecto)
                f.write(f"SET @product_id := (SELECT rowid FROM llx_product WHERE ref = '{codigo_esc}');\n")
                f.write(f"SET @tva_tx := COALESCE((SELECT tva_tx FROM llx_product_price WHERE fk_product = @product_id ORDER BY date_price DESC LIMIT 1), {IVA_DEFECTO});\n")
                f.write(f"SET @precio_iva = {precio_iva:.8f};\n")
                f.write(f"SET @precio_ht = @precio_iva / (1 + @tva_tx/100);\n\n")

                # Actualizar llx_product (solo si el producto existe)
                f.write(f"UPDATE llx_product SET\n")
                f.write(f"    price = @precio_ht,\n")
                f.write(f"    price_ttc = @precio_iva\n")
                f.write(f"WHERE rowid = @product_id;\n\n")

                # Insertar nuevo precio en llx_product_price
                f.write(f"INSERT INTO llx_product_price (\n")
                f.write(f"    entity, fk_product, date_price, price_level,\n")
                f.write(f"    price, price_ttc, price_base_type, tva_tx,\n")
                f.write(f"    recuperableonly, localtax1_type, localtax2_type,\n")
                f.write(f"    fk_user_author, tosell, price_by_qty,\n")
                f.write(f"    multicurrency_tx\n")
                f.write(f") VALUES (\n")
                f.write(f"    {ENTITY}, @product_id, NOW(), {PRICE_LEVEL},\n")
                f.write(f"    @precio_ht, @precio_iva, {PRICE_BASE_TYPE}, @tva_tx,\n")
                f.write(f"    {RECUPERABLEONLY}, {LOCALTAX1_TYPE}, {LOCALTAX2_TYPE},\n")
                f.write(f"    {FK_USER_AUTHOR}, {TOSELL}, {PRICE_BY_QTY},\n")
                f.write(f"    {MULTICURRENCY_TX}\n")
                f.write(f");\n\n")

                # Mostrar progreso cada 100 productos
                if (idx + 1) % 100 == 0:
                    print(f"    Procesados {idx + 1} de {total} productos...")

            f.write("COMMIT;\n")

        print(f"\n ✅ Archivo SQL generado exitosamente:")
        print(f"    {ARCHIVO_SALIDA}")
        print(f"    Total de productos procesados: {total}")

    except Exception as e:
        print(f" ❌ Error al escribir el archivo SQL: {e}")
        return

    print("=" * 70)
    print(" ✨ Proceso completado. Revisa el archivo SQL y ejecútalo en phpMyAdmin.")
    print("=" * 70)


if __name__ == "__main__":
    main()