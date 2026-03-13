#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script: generador_sql_relaciones_producto_categoria.py
Propósito: Genera un archivo SQL para insertar relaciones producto-categoría
           en llx_category_product de Dolibarr a partir de un archivo CSV.

Entrada: Archivo CSV con las columnas:
         - identificador_producto (según configuración, puede ser ref o barcode)
         - categoria
         - subcategoria (opcional)

Proceso:
         - Lee el CSV y por cada fila construye una sentencia INSERT IGNORE
           que obtiene los IDs de producto y categoría mediante subconsultas.
         - Soporta tres casos:
              * Categoría + Subcategoría: busca la subcategoría hija de la categoría.
              * Solo subcategoría: busca por nombre (puede ser ambigua, se genera advertencia).
              * Solo categoría: busca categoría de primer nivel (fk_parent != 0).
         - Busca el producto por el campo configurable (ref o barcode).

Salida: Archivo SQL en la carpeta 'data/output/' con todas las sentencias y advertencias.

Uso:
    1. Colocar el archivo CSV en la ruta especificada en ARCHIVO_CSV.
    2. Ajustar las constantes de configuración (nombres de columna, campo de búsqueda, etc.).
    3. Ejecutar el script.
    4. Revisar el archivo SQL generado y ejecutarlo en phpMyAdmin.
"""

import csv
import sys
import os

# =============================================================================
# CONFIGURACIÓN DEL USUARIO (modificar según necesidades)
# =============================================================================
ARCHIVO_CSV = "data/input/archivo.csv"               # Ruta al CSV de entrada
ARCHIVO_SQL = "data/output/asignar_categorias.sql"           # Archivo SQL de salida
DELIMITADOR = ","                                             # Separador del CSV (; o ,)
ENCODING = "utf-8-sig"                                        # Codificación del CSV

# Nombres exactos de las columnas en el CSV (deben coincidir)
COLUMNA_PRODUCTO = "Código"                   # Columna que identifica el producto (ref o código de barras)
COLUMNA_CATEGORIA = "Categoria"               # Columna con la categoría padre
COLUMNA_SUBCATEGORIA = "Subcategoria"         # Columna con la subcategoría (puede estar vacía)

# Campo por el que se busca el producto en la BD ('ref' o 'barcode')
CAMPO_PRODUCTO_BD = "barcode"                  # Cambiar a 'ref' si usas referencia

# Parámetros fijos de Dolibarr
ENTITY = 1                                      # Entidad (normalmente 1)
TYPE_CAT = 0                                    # Tipo categoría producto (0 = producto)

# =============================================================================
# FUNCIONES AUXILIARES
# =============================================================================
def escapar_string(s):
    """Escapa comillas simples para su uso seguro en sentencias SQL."""
    return s.replace("'", "''")

# =============================================================================
# FUNCIÓN PRINCIPAL
# =============================================================================
def generar_sql():
    """Lee el CSV, genera las sentencias SQL y escribe el archivo de salida."""
    print("=" * 70)
    print(" 🔗 GENERADOR SQL: RELACIONES PRODUCTO-CATEGORÍA")
    print("=" * 70)

    # Verificar existencia del archivo de entrada
    if not os.path.exists(ARCHIVO_CSV):
        print(f" ❌ ERROR: No se encuentra el archivo '{ARCHIVO_CSV}'.")
        print("   Por favor, verifica la ruta y el nombre del archivo.")
        sys.exit(1)

    print(f" 📄 Leyendo archivo: {ARCHIVO_CSV}")
    print(f" 🔍 Buscando productos por campo: '{CAMPO_PRODUCTO_BD}'")

    inserts = []          # Lista de sentencias SQL generadas
    advertencias = []     # Lista de advertencias encontradas durante el proceso
    fila_num = 0          # Contador de filas (para mensajes)

    try:
        with open(ARCHIVO_CSV, mode='r', encoding=ENCODING) as f:
            reader = csv.DictReader(f, delimiter=DELIMITADOR)

            # Mostrar columnas detectadas para depuración
            print("\n 📋 Columnas detectadas en el CSV:")
            for col in reader.fieldnames:
                print(f"    - '{col}'")

            # Verificar columnas requeridas
            if COLUMNA_PRODUCTO not in reader.fieldnames:
                print(f" ❌ ERROR: La columna '{COLUMNA_PRODUCTO}' no existe en el CSV.")
                print(f"    Columnas disponibles: {reader.fieldnames}")
                sys.exit(1)
            if COLUMNA_CATEGORIA not in reader.fieldnames:
                print(f" ❌ ERROR: La columna '{COLUMNA_CATEGORIA}' no existe en el CSV.")
                sys.exit(1)
            if COLUMNA_SUBCATEGORIA not in reader.fieldnames:
                print(f" ⚠️  La columna '{COLUMNA_SUBCATEGORIA}' no existe. Se tratará como vacía para todas las filas.")
                # Crear una columna virtual vacía en cada fila
                # (Como no podemos modificar el reader, ajustaremos la lectura manualmente)
                # En su lugar, agregamos la columna a la lista de fieldnames para la advertencia,
                # pero al leer las filas, subcategoria será None. Lo manejamos en el bucle.
                # Simplificamos: en el bucle usaremos .get() con valor por defecto ''.
                # No necesitamos modificar reader.fieldnames, solo recordar usar .get()

            for fila in reader:
                fila_num += 1
                producto = fila.get(COLUMNA_PRODUCTO, "").strip()
                categoria = fila.get(COLUMNA_CATEGORIA, "").strip()
                subcategoria = fila.get(COLUMNA_SUBCATEGORIA, "").strip() if COLUMNA_SUBCATEGORIA in fila else ""

                if not producto:
                    advertencias.append(f"Fila {fila_num}: identificador de producto vacío, se omite.")
                    continue

                # --- Construir la subconsulta para el producto ---
                where_producto = f"p.{CAMPO_PRODUCTO_BD} = '{escapar_string(producto)}'"

                # --- Construir la subconsulta para la categoría según los datos disponibles ---
                if subcategoria and categoria:
                    # Caso 1: Subcategoría con padre conocido
                    sql_categoria = f"""
    SELECT sub.rowid
    FROM llx_categorie sub
    INNER JOIN llx_categorie padre ON padre.rowid = sub.fk_parent
    WHERE padre.label = '{escapar_string(categoria)}'
      AND sub.label = '{escapar_string(subcategoria)}'
      AND sub.entity = {ENTITY} AND sub.type = {TYPE_CAT}
      AND padre.entity = {ENTITY} AND padre.type = {TYPE_CAT}
"""
                    comentario = f"subcategoría '{subcategoria}' hija de '{categoria}'"

                elif subcategoria and not categoria:
                    # Caso 2: Subcategoría sin padre especificado (búsqueda por nombre, puede ser ambigua)
                    sql_categoria = f"""
    SELECT rowid
    FROM llx_categorie
    WHERE label = '{escapar_string(subcategoria)}'
      AND entity = {ENTITY} AND type = {TYPE_CAT}
"""
                    comentario = f"subcategoría '{subcategoria}' (sin padre, puede ser ambigua)"
                    advertencias.append(f"Fila {fila_num}: subcategoría sin categoría padre, se usará búsqueda directa.")

                elif categoria and not subcategoria:
                    # Caso 3: Solo categoría (de primer nivel)
                    sql_categoria = f"""
    SELECT rowid
    FROM llx_categorie
    WHERE label = '{escapar_string(categoria)}'
      AND entity = {ENTITY} AND type = {TYPE_CAT}
      AND fk_parent != 0   -- asumimos que no es la raíz tpv, sino una categoría de nivel 1
"""
                    comentario = f"categoría '{categoria}' (primer nivel)"

                else:
                    # Sin categoría ni subcategoría
                    advertencias.append(f"Fila {fila_num}: no se especificó categoría ni subcategoría, se omite.")
                    continue

                # --- Generar la sentencia INSERT ---
                sql = f"""
-- {comentario} para producto {CAMPO_PRODUCTO_BD}='{producto}'
INSERT IGNORE INTO llx_category_product (fk_categorie, fk_product)
SELECT ({sql_categoria}), p.rowid
FROM llx_product p
WHERE {where_producto} AND p.entity = {ENTITY};
"""
                inserts.append(sql)

    except Exception as e:
        print(f" ❌ Error al leer el CSV: {e}")
        sys.exit(1)

    # Verificar que se generaron sentencias
    if not inserts:
        print(" ⚠️  No se generó ninguna sentencia SQL. Revisa el CSV y las advertencias.")
        if advertencias:
            print("\n Advertencias:")
            for w in advertencias:
                print(f"   - {w}")
        return

    # Crear la carpeta de salida si no existe
    try:
        os.makedirs(os.path.dirname(ARCHIVO_SQL), exist_ok=True)
    except Exception as e:
        print(f" ❌ Error al crear la carpeta de salida: {e}")
        return

    # --- Escribir archivo SQL ---
    try:
        with open(ARCHIVO_SQL, 'w', encoding='utf-8') as f:
            # Cabecera del archivo SQL
            f.write("-- =========================================================\n")
            f.write("-- ASIGNACIÓN DE CATEGORÍAS A PRODUCTOS\n")
            f.write(f"-- Generado desde: {ARCHIVO_CSV}\n")
            f.write(f"-- Buscando productos por campo: '{CAMPO_PRODUCTO_BD}'\n")
            f.write("-- =========================================================\n")
            f.write("START TRANSACTION;\n\n")

            # Escribir todas las sentencias generadas
            for sql in inserts:
                f.write(sql)
                f.write("\n")

            # Si hay advertencias, incluirlas como comentarios al final
            if advertencias:
                f.write("--\n-- ADVERTENCIAS (revisar manualmente):\n--\n")
                for warn in advertencias:
                    f.write(f"-- {warn}\n")

            f.write("\nCOMMIT;\n")

        print(f"\n ✅ Archivo SQL generado exitosamente:")
        print(f"    {ARCHIVO_SQL}")
        print(f" 📊 Sentencias generadas: {len(inserts)}")
        if advertencias:
            print(f" ⚠️  {len(advertencias)} advertencias. Revísalas en el archivo SQL.")

    except Exception as e:
        print(f" ❌ Error al escribir el archivo SQL: {e}")
        return

    print("=" * 70)
    print(" ✨ Proceso completado. Revisa el archivo SQL y ejecútalo en phpMyAdmin.")
    print("=" * 70)


if __name__ == "__main__":
    generar_sql()