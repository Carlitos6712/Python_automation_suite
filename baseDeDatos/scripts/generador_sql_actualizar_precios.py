#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script: generador_sql_actualizar_precios.py
Propósito: Genera un archivo SQL para actualizar precios de costo y venta
           de productos en Dolibarr a partir de un archivo Excel.

Entrada: Archivo Excel (.xlsx) con las columnas:
         - Código       : referencia del producto (se limpia automáticamente).
         - P. Costo     : precio de costo (puede incluir símbolo € y comas).
         - P. Venta     : precio de venta (puede incluir símbolo € y comas).

Proceso:
         - Lee el Excel y limpia códigos y precios.
         - Por cada producto válido, genera:
              * UPDATE de cost_price en llx_product.
              * Consulta para obtener el IVA actual del producto.
              * INSERT en llx_product_price para el nuevo precio de venta.

Salida: Archivo SQL con nombre dinámico (fecha y hora) en la carpeta 'data/output/'.

Uso:
    1. Colocar el archivo Excel en la ruta especificada en ARCHIVO_ENTRADA.
    2. Ajustar los nombres de columna en las constantes si es necesario.
    3. Ejecutar el script.
    4. Revisar el archivo SQL generado y ejecutarlo en phpMyAdmin.
"""

import pandas as pd
import os
import re
from datetime import datetime

# =============================================================================
# CONFIGURACIÓN DEL USUARIO (modificar según necesidades)
# =============================================================================
ARCHIVO_ENTRADA = "data/input/archivo.csv"   # Ruta al CSV de entrada
ARCHIVO_SALIDA = f"data/output/update_precios_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"

# Nombres exactos de las columnas en el CSV (deben coincidir)
COL_CODIGO = 'Código'
COL_PRECIO_COSTO = 'P. Costo'
COL_PRECIO_VENTA = 'P. Venta'

# =============================================================================
# FUNCIONES AUXILIARES
# =============================================================================
def limpiar_codigo(codigo):
    """
    Limpia el código:
        - Elimina espacios al inicio/fin.
        - Elimina caracteres no alfanuméricos al final (como !, ., etc.).
    Si después de limpiar queda vacío, retorna None.
    """
    if pd.isna(codigo):
        return None
    codigo = str(codigo).strip()
    # Eliminar caracteres no alfanuméricos al final (como !, ., etc.)
    codigo = re.sub(r'[^a-zA-Z0-9]+$', '', codigo)
    return codigo if codigo else None

def limpiar_precio(valor):
    """
    Convierte un precio con posible símbolo € y coma decimal a número float.
    Ejemplos: "12,50 €" -> 12.5, "45.99" -> 45.99
    Si no se puede convertir, retorna None.
    """
    if pd.isna(valor):
        return None
    # Convertir a string y quitar símbolo € y espacios
    valor_str = str(valor).replace('€', '').replace(' ', '').strip()
    # Reemplazar coma por punto si es necesario
    valor_str = valor_str.replace(',', '.')
    try:
        return float(valor_str)
    except:
        return None

def escape_sql(valor):
    """
    Escapa comillas simples para SQL.
    Si el valor es None retorna 'NULL', de lo contrario lo envuelve entre comillas.
    """
    if valor is None:
        return "NULL"
    s = str(valor).replace("'", "''")
    return f"'{s}'"

# =============================================================================
# FUNCIÓN PRINCIPAL
# =============================================================================
def main():
    """Función principal que orquesta la lectura, limpieza y generación del SQL."""
    print("=" * 70)
    print(" 💰 GENERADOR SQL: ACTUALIZACIÓN DE PRECIOS DESDE EXCEL")
    print("=" * 70)

    # Verificar existencia del archivo de entrada
    if not os.path.exists(ARCHIVO_ENTRADA):
        print(f" ❌ ERROR: No se encuentra el archivo '{ARCHIVO_ENTRADA}'.")
        print("   Por favor, verifica la ruta y el nombre del archivo.")
        return

    print(f" 📄 Leyendo archivo: {ARCHIVO_ENTRADA}")

    # Leer Excel con pandas (leer todo como texto para evitar conversiones automáticas)
    try:
        df = pd.read_excel(ARCHIVO_ENTRADA, dtype=str)
    except Exception as e:
        print(f" ❌ Error al leer el Excel: {e}")
        print("   Asegúrate de que el archivo no esté corrupto y que tenga extensión .xlsx")
        return

    # Limpiar nombres de columna (eliminar espacios al inicio/fin)
    df.columns = [col.strip() for col in df.columns]

    # Mostrar columnas detectadas para depuración
    print("\n 📋 Columnas detectadas en el Excel:")
    for col in df.columns:
        print(f"    - '{col}'")

    # Validar que las columnas requeridas existan
    necesarias = [COL_CODIGO, COL_PRECIO_COSTO, COL_PRECIO_VENTA]
    faltan = [c for c in necesarias if c not in df.columns]
    if faltan:
        print(f" ❌ El Excel debe contener las columnas: {', '.join(necesarias)}")
        print(f"    Faltan: {', '.join(faltan)}")
        print("   Verifica los nombres (incluyendo mayúsculas, acentos y espacios).")
        return

    total = len(df)
    print(f"\n ✅ Productos leídos: {total}")

    # =========================================================================
    # PROCESAR DATOS (limpiar códigos y precios)
    # =========================================================================
    datos_procesados = []
    errores = 0

    for idx, row in df.iterrows():
        codigo_original = row[COL_CODIGO]
        codigo = limpiar_codigo(codigo_original)
        if not codigo:
            print(f"    ⚠️ Fila {idx+2}: código inválido '{codigo_original}', se omite")
            errores += 1
            continue
        
        precio_costo = limpiar_precio(row[COL_PRECIO_COSTO])
        precio_venta = limpiar_precio(row[COL_PRECIO_VENTA])
        
        if precio_costo is None and precio_venta is None:
            print(f"    ⚠️ Fila {idx+2}: ambos precios inválidos, se omite")
            errores += 1
            continue
        
        datos_procesados.append({
            'codigo': codigo,
            'precio_costo': precio_costo,
            'precio_venta': precio_venta
        })

    print(f"\n ✅ Datos válidos: {len(datos_procesados)}  |  Errores: {errores}")

    if len(datos_procesados) == 0:
        print(" ⚠️  No hay datos válidos para procesar. Saliendo.")
        return

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
            f.write("-- ACTUALIZACIÓN DE PRECIOS DE PRODUCTOS\n")
            f.write(f"-- Generado el {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("-- =========================================================\n\n")
            f.write("START TRANSACTION;\n\n")

            for idx, prod in enumerate(datos_procesados):
                ref = prod['codigo']
                precio_costo = prod['precio_costo']
                precio_venta = prod['precio_venta']

                f.write(f"-- Producto ref: {ref}\n")

                # 1. Actualizar precio de costo en llx_product
                if precio_costo is not None:
                    f.write(f"UPDATE llx_product SET cost_price = {precio_costo:.8f} WHERE ref = '{ref}';\n")
                else:
                    f.write(f"-- Precio de costo no disponible, se omite.\n")

                # 2. Obtener la tasa de IVA actual del producto
                f.write(f"-- Obtener IVA actual del producto\n")
                f.write(f"SET @tva_tx := (SELECT tva_tx FROM llx_product_price WHERE fk_product = (SELECT rowid FROM llx_product WHERE ref = '{ref}') ORDER BY date_price DESC LIMIT 1);\n")
                f.write(f"SET @tva_tx := IFNULL(@tva_tx, 21.0);  -- IVA por defecto si no existe\n")

                # 3. Insertar nuevo precio de venta en llx_product_price
                if precio_venta is not None:
                    f.write(f"INSERT INTO llx_product_price (fk_product, price, price_ttc, price_base_type, tva_tx, date_price)\n")
                    f.write(f"SELECT p.rowid, {precio_venta:.8f}, {precio_venta:.8f} * (1 + @tva_tx/100), 'HT', @tva_tx, NOW()\n")
                    f.write(f"FROM llx_product p WHERE p.ref = '{ref}';\n")
                else:
                    f.write(f"-- Precio de venta no disponible, se omite.\n")

                f.write("\n")

                # Mostrar progreso cada 100 productos
                if (idx + 1) % 100 == 0:
                    print(f"    Procesados {idx + 1} de {len(datos_procesados)} productos...")

            f.write("COMMIT;\n")

        print(f"\n ✅ Archivo SQL generado exitosamente:")
        print(f"    {ARCHIVO_SALIDA}")
        print(f"    Total de productos válidos: {len(datos_procesados)}")

    except Exception as e:
        print(f" ❌ Error al escribir el archivo SQL: {e}")
        return

    print("=" * 70)
    print(" ✨ Proceso completado. Revisa el archivo SQL y ejecútalo en phpMyAdmin.")
    print("=" * 70)


if __name__ == "__main__":
    main()