#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script: generador_sql_insert_productos_categorias.py
Propósito: Genera un archivo SQL con inserts para productos y categorías jerárquicas
           en Dolibarr a partir de un archivo CSV.

Entrada: Archivo CSV separado por ';' con las columnas:
         - Código, Producto, P. Venta, IVA_Asignado, categoria (obligatorias)
         - subcategoria, P. Costo, Existencia, Inv. Mínimo, P. Mayoreo,
           Peso, Volumen, Tamaño (opcionales)

Salida: Archivo SQL con nombre dinámico (fecha y hora) en la carpeta 'data/output/'.
        El SQL realiza:
           - Inserción de categorías principales (si no existen).
           - Inserción de subcategorías (como hijas de su categoría principal).
           - Inserción de productos con todos sus campos (incluyendo medidas).
           - Relación de cada producto con su categoría/subcategoría.

Uso:
    1. Colocar el archivo CSV en la ruta especificada en ARCHIVO_ENTRADA.
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
ARCHIVO_ENTRADA = "data/input/archivo.csv"
ARCHIVO_SALIDA = f"data/output/insert_final_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"

# Nombres exactos de las columnas en tu CSV (minúsculas)
COL_CATEGORIA = 'categoria'
COL_SUBCATEGORIA = 'subcategoria'

# =============================================================================
# FUNCIONES AUXILIARES
# =============================================================================

def escape_sql(valor):
    """
    Escapa comillas simples para SQL y envuelve el string entre comillas.
    Si el valor es nulo o vacío retorna 'NULL'.
    """
    if pd.isna(valor) or valor == '':
        return "NULL"
    s = str(valor).replace("'", "''")
    return f"'{s}'"

def valor_numerico(valor, por_defecto=0):
    """Convierte a float de forma segura; si falla retorna por_defecto."""
    try:
        return float(valor) if pd.notna(valor) else por_defecto
    except:
        return por_defecto

def extraer_medida(texto):
    """
    Extrae (valor, unidad_texto) de un texto como '30cm'.
    Retorna (None, None) si no se puede extraer.
    """
    if pd.isna(texto) or texto == '':
        return None, None
    texto = str(texto).strip().lower()
    m = re.match(r'^([\d\.]+)\s*([a-z]+)$', texto)
    if m:
        return float(m.group(1)), m.group(2)
    try:
        return float(texto), None
    except:
        return None, None

def unidad_peso(unidad):
    """Convierte unidad de peso a código Dolibarr."""
    if unidad in ('kg','kilo','kilos'):
        return 0
    if unidad in ('g','gr','gramo','gramos'):
        return 1
    return 0

def unidad_volumen(unidad):
    """Convierte unidad de volumen a código Dolibarr."""
    if unidad in ('l','litro','litros'):
        return 1
    if unidad in ('ml','mililitro','mililitros'):
        return 2
    return 1

def unidad_longitud(unidad):
    """Convierte unidad de longitud a código Dolibarr."""
    if unidad in ('cm','centimetro','centimetros'):
        return 1
    if unidad in ('m','metro','metros'):
        return 0
    return 1

# =============================================================================
# FUNCIÓN PRINCIPAL
# =============================================================================
def main():
    """Función principal que orquesta la lectura, validación y generación del SQL."""
    print("=" * 70)
    print(" 📂 GENERADOR SQL: INSERCIÓN DE PRODUCTOS Y CATEGORÍAS JERÁRQUICAS")
    print("=" * 70)

    # Verificar existencia del archivo de entrada
    if not os.path.exists(ARCHIVO_ENTRADA):
        print(f" ❌ ERROR: No se encuentra el archivo '{ARCHIVO_ENTRADA}'.")
        print("   Por favor, verifica la ruta y el nombre del archivo.")
        return

    print(f" 📄 Leyendo archivo: {ARCHIVO_ENTRADA}")

    # Leer CSV con separador ';' y manejo de errores
    try:
        df = pd.read_csv(
            ARCHIVO_ENTRADA,
            sep=';',
            encoding='utf-8',
            engine='python',
            quotechar='"',
            skipinitialspace=True,
            on_bad_lines='warn'      # Emite advertencia para líneas problemáticas
        )
    except Exception as e:
        print(f" ❌ Error al leer el CSV: {e}")
        print("   Revisa que el archivo no esté corrupto y que el separador sea correcto.")
        return

    # Mostrar las columnas detectadas para depuración
    print("\n 📋 Columnas encontradas en el CSV:")
    for i, col in enumerate(df.columns):
        print(f"    {i+1}. '{col}'")

    # Limpiar nombres de columna (eliminar espacios)
    df.columns = [col.strip() for col in df.columns]

    # Verificar que existan las columnas obligatorias
    columnas_necesarias = ['Código', 'Producto', 'P. Venta', 'IVA_Asignado', COL_CATEGORIA]
    faltan = [c for c in columnas_necesarias if c not in df.columns]
    if faltan:
        print(f" ❌ ERROR: Faltan columnas obligatorias: {faltan}")
        print("    Columnas disponibles:", list(df.columns))
        return

    total_productos = len(df)
    print(f"\n ✅ Productos cargados: {total_productos}")

    if total_productos == 0:
        print("\n ⚠️  No hay productos para procesar. Saliendo.")
        return

    # ---- 1. Obtener pares únicos de (categoria, subcategoria) ----
    pares = []
    for _, row in df.iterrows():
        cat = str(row[COL_CATEGORIA]).strip() if pd.notna(row[COL_CATEGORIA]) else ''
        sub = str(row[COL_SUBCATEGORIA]).strip() if COL_SUBCATEGORIA in df.columns and pd.notna(row[COL_SUBCATEGORIA]) else ''
        if cat:
            pares.append((cat, sub if sub else None))

    pares_unicos = list(set(pares))
    print(f" 📂 Pares (categoría, subcategoría) únicos: {len(pares_unicos)}")

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
            f.write("-- INSERTS FINALES PARA DOLIBARR\n")
            f.write(f"-- Generado el {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("-- =========================================================\n\n")
            f.write("START TRANSACTION;\n\n")

            # ---- Insertar categorías principales (fk_parent = 0) ----
            categorias_principales = sorted(set(cat for cat, sub in pares_unicos if cat))
            if categorias_principales:
                f.write("-- 1. Insertar categorías principales\n")
                for cat in categorias_principales:
                    cat_esc = escape_sql(cat)
                    f.write(f"INSERT IGNORE INTO llx_categorie (label, type, entity, visible, position, fk_parent, description, color)\n")
                    f.write(f"VALUES ({cat_esc}, 0, 1, 1, 0, 0, NULL, NULL);\n")
                f.write("\n")

            # ---- Insertar subcategorías (fk_parent = id de la categoría principal) ----
            subcats_unicas = [(cat, sub) for cat, sub in pares_unicos if sub]
            subcats_unicas = list(set(subcats_unicas))
            if subcats_unicas:
                f.write("-- 2. Insertar subcategorías\n")
                for cat, sub in subcats_unicas:
                    cat_esc = escape_sql(cat)
                    sub_esc = escape_sql(sub)
                    f.write(f"INSERT IGNORE INTO llx_categorie (label, type, entity, visible, position, fk_parent, description, color)\n")
                    f.write(f"SELECT {sub_esc}, 0, 1, 1, 0, c.rowid, NULL, NULL\n")
                    f.write(f"FROM llx_categorie c WHERE c.label = {cat_esc} AND c.type = 0 AND c.fk_parent = 0;\n")
                f.write("\n")

            # ---- Insertar productos ----
            f.write("-- 3. Insertar productos\n")
            for idx, row in df.iterrows():
                ref = str(row['Código']).strip()
                label = str(row['Producto']).strip()
                price = valor_numerico(row.get('P. Venta'))
                cost_price = valor_numerico(row.get('P. Costo'))
                tva_tx = valor_numerico(row.get('IVA_Asignado'), 21.0)
                stock = int(valor_numerico(row.get('Existencia'), 0))
                seuil_stock_alerte = int(valor_numerico(row.get('Inv. Mínimo'), 5))
                price_min = valor_numerico(row.get('P. Mayoreo'), 0)

                price_ttc = price * (1 + tva_tx / 100)
                price_min_ttc = price_min * (1 + tva_tx / 100) if price_min > 0 else 0.0

                # Medidas
                peso_val, peso_unidad = extraer_medida(row.get('Peso'))
                weight = peso_val if peso_val is not None else 0
                weight_units = unidad_peso(peso_unidad) if peso_unidad else 0

                vol_val, vol_unidad = extraer_medida(row.get('Volumen'))
                volume = vol_val if vol_val is not None else 0
                volume_units = unidad_volumen(vol_unidad) if vol_unidad else 1

                long_val, long_unidad = extraer_medida(row.get('Tamaño'))
                length = long_val if long_val is not None else 0
                length_units = unidad_longitud(long_unidad) if long_unidad else 1

                # Valores fijos (ajusta según tu instalación)
                entity = 1
                fk_country = 1          # España
                fk_user_author = 1      # admin
                barcode = escape_sql(ref)
                import_key = escape_sql(f"IMPORT_{datetime.now().strftime('%Y%m%d_%H%M%S')}")

                sql_prod = f"""INSERT INTO llx_product (
    rowid, ref, entity, ref_ext, datec, tms, fk_parent,
    label, description, note_public, note, customcode,
    fk_country, fk_state, price, price_ttc, price_min, price_min_ttc,
    price_base_type, price_label, cost_price, default_vat_code,
    tva_tx, recuperableonly, localtax1_tx, localtax1_type,
    localtax2_tx, localtax2_type, fk_user_author, fk_user_modif,
    tosell, tobuy, tobatch, sell_or_eat_by_mandatory, batch_mask,
    fk_product_type, duration, seuil_stock_alerte, url, barcode,
    fk_barcode_type, accountancy_code_sell, accountancy_code_sell_intra,
    accountancy_code_sell_export, accountancy_code_buy, accountancy_code_buy_intra,
    accountancy_code_buy_export, partnumber, net_measure, net_measure_units,
    weight, weight_units, length, length_units, width, width_units,
    height, height_units, surface, surface_units, volume, volume_units,
    stockable_product, stock, pmp, fifo, lifo, fk_default_warehouse,
    fk_default_bom, fk_default_workstation, canvas, finished, lifetime,
    qc_frequency, hidden, import_key, model_pdf, fk_price_expression,
    desiredstock, fk_unit, price_autogen, fk_project, mandatory_period,
    last_main_doc
) VALUES (
    NULL, {escape_sql(ref)}, {entity}, NULL, NOW(), NOW(), 0,
    {escape_sql(label)}, '', NULL, NULL, NULL,
    {fk_country}, 0, {price:.8f}, {price_ttc:.8f}, {price_min:.8f}, {price_min_ttc:.8f},
    'HT', NULL, {cost_price:.8f}, NULL,
    {tva_tx:.4f}, 0, 0, '', 0, '', {fk_user_author}, NULL,
    1, 1, 0, 0, NULL,
    0, NULL, {seuil_stock_alerte}, '', {barcode},
    0, '', '', '', '', '', '',
    '', NULL, NULL,
    {weight:.3f}, {weight_units}, {length:.3f}, {length_units}, 0, 0,
    0, 0, 0, 0, {volume:.3f}, {volume_units},
    1, {stock}, 0, NULL, NULL, NULL,
    NULL, NULL, '', 1, 0,
    0, 0, {import_key}, NULL, NULL,
    0, NULL, 0, NULL, 0,
    ''
);\n"""
                f.write(sql_prod + "\n")

                # Mostrar progreso cada 100 productos
                if (idx + 1) % 100 == 0:
                    print(f"    Procesados {idx + 1} de {total_productos} productos...")

            # ---- Relacionar productos con categorías/subcategorías ----
            f.write("\n-- 4. Relacionar productos con categorías/subcategorías\n")
            for idx, row in df.iterrows():
                ref = str(row['Código']).strip()
                cat = str(row[COL_CATEGORIA]).strip() if pd.notna(row[COL_CATEGORIA]) else ''
                sub = str(row[COL_SUBCATEGORIA]).strip() if COL_SUBCATEGORIA in df.columns and pd.notna(row[COL_SUBCATEGORIA]) else ''

                if sub:
                    # Asociar a la subcategoría
                    cat_esc = escape_sql(cat)
                    sub_esc = escape_sql(sub)
                    f.write(f"""INSERT INTO llx_categorie_product (fk_categorie, fk_product)
SELECT c2.rowid, p.rowid
FROM llx_categorie c1, llx_categorie c2, llx_product p
WHERE c1.label = {cat_esc} AND c1.type = 0 AND c1.fk_parent = 0
  AND c2.label = {sub_esc} AND c2.type = 0 AND c2.fk_parent = c1.rowid
  AND p.ref = {escape_sql(ref)}
ON DUPLICATE KEY UPDATE fk_categorie = fk_categorie;\n""")
                elif cat:
                    # Asociar a la categoría principal
                    cat_esc = escape_sql(cat)
                    f.write(f"""INSERT INTO llx_categorie_product (fk_categorie, fk_product)
SELECT c.rowid, p.rowid
FROM llx_categorie c, llx_product p
WHERE c.label = {cat_esc} AND c.type = 0 AND c.fk_parent = 0
  AND p.ref = {escape_sql(ref)}
ON DUPLICATE KEY UPDATE fk_categorie = fk_categorie;\n""")

                # Agregar separador cada 100 relaciones
                if (idx + 1) % 100 == 0:
                    f.write("\n")

            f.write("\nCOMMIT;\n")

        print(f"\n ✅ Archivo SQL generado exitosamente:")
        print(f"    {ARCHIVO_SALIDA}")
        print(f"    Total productos insertados: {total_productos}")

    except Exception as e:
        print(f" ❌ Error al escribir el archivo SQL: {e}")
        return

    print("=" * 70)
    print(" ✨ ¡LISTO! Revisa el archivo SQL y ejecútalo en phpMyAdmin.")
    print("=" * 70)


if __name__ == "__main__":
    main()