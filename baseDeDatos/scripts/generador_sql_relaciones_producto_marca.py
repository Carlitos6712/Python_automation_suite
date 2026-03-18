#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script: generador_sql_relaciones_producto_marca.py
Autor:  Carlos Vico

Propósito:
    Genera un archivo SQL para insertar o actualizar relaciones producto-marca
    en llx_categorie_product de Dolibarr, a partir de un archivo CSV.

    La marca en Dolibarr se gestiona como una subcategoría hija de la
    categoría principal "Marcas". Este script genera INSERT IGNORE para
    cada par producto-marca, localizando ambos por sus campos de texto
    (ref/barcode y label) mediante subconsultas, sin IDs hardcodeados.

Entrada:
    CSV con las columnas:
      - Código    : referencia o código de barras del producto.
      - Marca     : nombre de la marca (label en llx_categorie).

Proceso:
    Por cada fila del CSV:
      1. Localiza el producto por ref o barcode en llx_product.
      2. Localiza la categoría-marca como subcategoría de "Marcas" en llx_categorie.
      3. Genera INSERT IGNORE en llx_categorie_product (idempotente).
      4. Registra advertencias para filas con datos incompletos.

Salida:
    Archivo SQL en data/output/ con todas las sentencias y advertencias.

Uso:
    1. Colocar el CSV en la ruta especificada en ARCHIVO_CSV.
    2. Ajustar las constantes de configuración.
    3. Ejecutar: python generador_sql_relaciones_producto_marca.py
    4. Revisar y ejecutar el SQL generado en phpMyAdmin.
"""

import csv
import sys
import os
from datetime import datetime

# =============================================================================
# CONFIGURACIÓN (modificar según el entorno)
# =============================================================================

ARCHIVO_CSV = "data/input/pajaro_final_finalisimo_de_los_finales_finalizados.csv"  # Ruta al CSV de entrada
ARCHIVO_SQL = (
    f"data/output/relaciones_producto_marca_"
    f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
)

DELIMITADOR = ";"           # Separador del CSV
ENCODING    = "utf-8-sig"   # Codificación del CSV (utf-8-sig elimina el BOM de Excel)

# Nombres exactos de las columnas en el CSV (respetar mayúsculas y acentos)
COLUMNA_PRODUCTO = "Ref"
COLUMNA_MARCA    = "Marca"

# Campo por el que se busca el producto en llx_product ('ref' o 'barcode')
CAMPO_PRODUCTO_BD = "ref"   # Cambiar a 'barcode' si usas código de barras

# Nombre de la categoría raíz que agrupa todas las marcas en Dolibarr
CATEGORIA_MARCAS = "Marcas"

# Parámetros fijos de Dolibarr
ENTITY   = 1   # Entidad
TYPE_CAT = 0   # 0 = categoría de productos


# =============================================================================
# UTILIDADES
# =============================================================================

def escapar_string(s: str) -> str:
    """
    Escapa comillas simples para uso seguro en sentencias SQL.

    Args:
        s: Cadena de texto a escapar.

    Returns:
        str: Cadena con comillas simples duplicadas.
    """
    return s.replace("'", "''")


def validar_columnas(fieldnames: list) -> list:
    """
    Comprueba que las columnas obligatorias existan en el CSV.

    Args:
        fieldnames: Lista de nombres de columna detectados.

    Returns:
        list: Lista de errores encontrados (vacía si todo es correcto).
    """
    errores = []
    for col in [COLUMNA_PRODUCTO, COLUMNA_MARCA]:
        if col not in fieldnames:
            errores.append(f"Columna obligatoria no encontrada: '{col}'")
    return errores


# =============================================================================
# CONSTRUCCIÓN DE SENTENCIAS SQL
# =============================================================================

def construir_insert(producto: str, marca: str) -> str:
    """
    Construye la sentencia INSERT IGNORE para relacionar un producto
    con su categoría-marca en llx_categorie_product.

    La subconsulta de categoría restringe la búsqueda al subárbol de
    CATEGORIA_MARCAS para evitar colisiones con marcas homónimas en
    otras ramas del árbol de categorías.

    Args:
        producto: Valor del campo CAMPO_PRODUCTO_BD del producto.
        marca:    Nombre de la marca (label en llx_categorie).

    Returns:
        str: Sentencia SQL lista para escribir en el archivo.
    """
    prod_esc  = escapar_string(producto)
    marca_esc = escapar_string(marca)
    cat_esc   = escapar_string(CATEGORIA_MARCAS)

    return (
        f"-- Producto {CAMPO_PRODUCTO_BD}='{producto}' -> Marca='{marca}'\n"
        f"INSERT IGNORE INTO llx_categorie_product (fk_categorie, fk_product)\n"
        f"SELECT cat.rowid, p.rowid\n"
        f"FROM   llx_categorie cat\n"
        f"JOIN   llx_product   p ON p.{CAMPO_PRODUCTO_BD} = '{prod_esc}'\n"
        f"                      AND p.entity = {ENTITY}\n"
        f"WHERE  cat.label    = '{marca_esc}'\n"
        f"  AND  cat.type     = {TYPE_CAT}\n"
        f"  AND  cat.entity   = {ENTITY}\n"
        f"  AND  cat.fk_parent = (\n"
        f"           SELECT c.rowid\n"
        f"           FROM   llx_categorie c\n"
        f"           WHERE  c.label    = '{cat_esc}'\n"
        f"             AND  c.type     = {TYPE_CAT}\n"
        f"             AND  c.entity   = {ENTITY}\n"
        f"             AND  c.fk_parent = 0\n"
        f"       );\n"
    )


# =============================================================================
# LECTURA DEL CSV
# =============================================================================

def leer_csv(ruta: str) -> tuple[list, list]:
    """
    Lee el CSV y construye la lista de sentencias SQL y advertencias.

    Args:
        ruta: Ruta al archivo CSV.

    Returns:
        tuple: (lista de sentencias SQL, lista de advertencias)
    """
    inserts      = []
    advertencias = []

    with open(ruta, mode='r', encoding=ENCODING) as f:
        reader = csv.DictReader(f, delimiter=DELIMITADOR)

        print("\n 📋 Columnas detectadas en el CSV:")
        for col in reader.fieldnames:
            print(f"    - '{col}'")

        errores = validar_columnas(reader.fieldnames)
        if errores:
            for error in errores:
                print(f" ❌ {error}")
            sys.exit(1)

        for num, fila in enumerate(reader, start=1):
            producto = fila.get(COLUMNA_PRODUCTO, "").strip()
            marca    = fila.get(COLUMNA_MARCA, "").strip()

            # Registrar y saltar filas con datos incompletos
            if not producto:
                advertencias.append(f"Fila {num}: identificador de producto vacío, se omite.")
                continue
            if not marca:
                advertencias.append(f"Fila {num}: producto '{producto}' sin marca, se omite.")
                continue

            inserts.append(construir_insert(producto, marca))

    return inserts, advertencias


# =============================================================================
# ESCRITURA DEL ARCHIVO SQL
# =============================================================================

def escribir_sql(inserts: list, advertencias: list) -> None:
    """
    Escribe el archivo SQL final con cabecera, sentencias y advertencias.

    Args:
        inserts:      Lista de sentencias INSERT generadas.
        advertencias: Lista de advertencias a incluir como comentarios.
    """
    os.makedirs(os.path.dirname(ARCHIVO_SQL), exist_ok=True)

    with open(ARCHIVO_SQL, 'w', encoding='utf-8') as f:
        # Cabecera
        f.write("-- =============================================================\n")
        f.write("-- RELACIONES PRODUCTO-MARCA EN llx_categorie_product\n")
        f.write(f"-- Generado  : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write( "-- Autor     : Carlos Vico\n")
        f.write(f"-- Origen    : {ARCHIVO_CSV}\n")
        f.write(f"-- Campo     : llx_product.{CAMPO_PRODUCTO_BD}\n")
        f.write(f"-- Cat. raíz : {CATEGORIA_MARCAS}\n")
        f.write(f"-- Sentencias: {len(inserts)}\n")
        f.write("-- =============================================================\n\n")
        f.write("START TRANSACTION;\n\n")

        # Sentencias
        for sql in inserts:
            f.write(sql)
            f.write("\n")

        # Advertencias como comentarios al final del archivo
        if advertencias:
            f.write("-- -------------------------------------------------------------\n")
            f.write("-- ADVERTENCIAS (revisar manualmente antes de ejecutar)\n")
            f.write("-- -------------------------------------------------------------\n")
            for warn in advertencias:
                f.write(f"-- ⚠️  {warn}\n")
            f.write("\n")

        f.write("COMMIT;\n")


# =============================================================================
# FUNCIÓN PRINCIPAL
# =============================================================================

def main() -> None:
    """Orquesta la lectura del CSV y la generación del SQL de relaciones."""
    print("=" * 70)
    print(" 🔗 GENERADOR SQL — RELACIONES PRODUCTO-MARCA")
    print("=" * 70)
    print(f" 🔍 Buscando productos por: llx_product.{CAMPO_PRODUCTO_BD}")
    print(f" 🏷️  Categoría raíz de marcas: '{CATEGORIA_MARCAS}'")

    if not os.path.exists(ARCHIVO_CSV):
        print(f" ❌ Archivo no encontrado: '{ARCHIVO_CSV}'")
        sys.exit(1)

    print(f" 📄 Leyendo: {ARCHIVO_CSV}")

    try:
        inserts, advertencias = leer_csv(ARCHIVO_CSV)
    except Exception as exc:
        print(f" ❌ Error al leer el CSV: {exc}")
        sys.exit(1)

    if not inserts:
        print(" ⚠️  No se generó ninguna sentencia. Revisa el CSV y las advertencias.")
        for warn in advertencias:
            print(f"    - {warn}")
        return

    try:
        escribir_sql(inserts, advertencias)
    except Exception as exc:
        print(f" ❌ Error al escribir el SQL: {exc}")
        return

    print(f"\n ✅ SQL generado: {ARCHIVO_SQL}")
    print(f"    Sentencias : {len(inserts)}")
    if advertencias:
        print(f"    Advertencias: {len(advertencias)} — revísalas en el archivo SQL.")

    print("=" * 70)
    print(" ✨ Listo. Revisa el SQL y ejecútalo en phpMyAdmin.")
    print("=" * 70)


if __name__ == "__main__":
    main()