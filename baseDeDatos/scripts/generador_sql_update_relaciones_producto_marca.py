#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script: generador_sql_update_relaciones_producto_marca.py
Autor:  Carlos Vico

Propósito:
    Genera un archivo SQL que CORRIGE relaciones producto-marca erróneas
    en llx_categorie_product de Dolibarr, a partir de un CSV.

    llx_categorie_product tiene PK compuesta (fk_categorie, fk_product),
    por lo que un UPDATE que cambie fk_categorie a un valor ya existente
    para ese fk_product lanzaría el error #1062 (entrada duplicada).

    La estrategia segura para cada producto es:
      1. DELETE de la relación incorrecta (cualquier marca distinta a la correcta).
      2. INSERT IGNORE de la relación correcta (idempotente si ya existe).

    Este patrón DELETE + INSERT IGNORE es más robusto que UPDATE para tablas
    con PK compuesta, ya que evita colisiones al cambiar parte de la clave.

Entrada:
    CSV con las columnas:
      - Código : referencia o código de barras del producto.
      - Marca  : nombre correcto de la marca (label en llx_categorie).

Salida:
    Archivo SQL con timestamp en data/output/ listo para ejecutar en phpMyAdmin.

Uso:
    1. Colocar el CSV en la ruta especificada en ARCHIVO_CSV.
    2. Ajustar las constantes de configuración.
    3. Ejecutar: python generador_sql_update_relaciones_producto_marca.py
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
    f"data/output/update_relaciones_producto_marca_"
    f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
)

DELIMITADOR = ";"           # Separador del CSV
ENCODING    = "utf-8-sig"   # utf-8-sig elimina el BOM generado por Excel

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

def subconsulta_rowid_marca(marca_esc: str, cat_esc: str) -> str:
    """
    Subconsulta que resuelve el rowid de la marca correcta dentro del
    subárbol de CATEGORIA_MARCAS.

    LIMIT 1 previene el error #1242 ante categorías homónimas residuales.

    Args:
        marca_esc: Nombre de la marca ya escapado para SQL.
        cat_esc:   Nombre de la categoría raíz ya escapado para SQL.

    Returns:
        str: Subconsulta SQL sin paréntesis exteriores.
    """
    return (
        f"    SELECT cat.rowid\n"
        f"    FROM   llx_categorie cat\n"
        f"    WHERE  cat.label     = '{marca_esc}'\n"
        f"      AND  cat.type      = {TYPE_CAT}\n"
        f"      AND  cat.entity    = {ENTITY}\n"
        f"      AND  cat.fk_parent = (\n"
        f"               SELECT c.rowid FROM llx_categorie c\n"
        f"               WHERE  c.label     = '{cat_esc}'\n"
        f"                 AND  c.type      = {TYPE_CAT}\n"
        f"                 AND  c.entity    = {ENTITY}\n"
        f"                 AND  c.fk_parent = 0\n"
        f"               LIMIT 1\n"
        f"           )\n"
        f"    LIMIT 1"
    )


def subconsulta_rowid_producto(prod_esc: str) -> str:
    """
    Subconsulta que resuelve el rowid del producto por ref o barcode.

    LIMIT 1 previene el error #1242 ante referencias duplicadas.

    Args:
        prod_esc: Valor del campo CAMPO_PRODUCTO_BD ya escapado.

    Returns:
        str: Subconsulta SQL sin paréntesis exteriores.
    """
    return (
        f"    SELECT rowid FROM llx_product\n"
        f"    WHERE  {CAMPO_PRODUCTO_BD} = '{prod_esc}'\n"
        f"      AND  entity = {ENTITY}\n"
        f"    LIMIT 1"
    )


def construir_bloque(producto: str, marca: str) -> str:
    """
    Construye el bloque DELETE + INSERT IGNORE para un producto.

    Por qué DELETE + INSERT en lugar de UPDATE:
      llx_categorie_product tiene PK compuesta (fk_categorie, fk_product).
      Un UPDATE que modifica fk_categorie puede colisionar con una fila
      existente que ya tenga (nueva_marca, producto), lanzando #1062.
      DELETE elimina primero cualquier relación errónea del producto
      con marcas distintas a la correcta, y luego INSERT IGNORE establece
      la relación correcta de forma idempotente.

    Args:
        producto: Valor del campo CAMPO_PRODUCTO_BD del producto.
        marca:    Nombre correcto de la marca.

    Returns:
        str: Bloque SQL completo para este producto.
    """
    prod_esc  = escapar_string(producto)
    marca_esc = escapar_string(marca)
    cat_esc   = escapar_string(CATEGORIA_MARCAS)

    sub_marca    = subconsulta_rowid_marca(marca_esc, cat_esc)
    sub_producto = subconsulta_rowid_producto(prod_esc)

    return (
        f"-- {CAMPO_PRODUCTO_BD}='{producto}' -> Marca='{marca}'\n"

        # DELETE: elimina las relaciones del producto con marcas incorrectas.
        # La condición fk_categorie != rowid_correcto preserva la relación
        # si ya apunta a la marca correcta, evitando un borrado innecesario.
        f"DELETE FROM llx_categorie_product\n"
        f"WHERE  fk_product = (\n"
        f"{sub_producto}\n"
        f")\n"
        f"  AND  fk_categorie IN (\n"
        f"           -- Todas las marcas del subárbol 'Marcas' asignadas a este producto\n"
        f"           SELECT cp.fk_categorie\n"
        f"           FROM   llx_categorie_product cp\n"
        f"           JOIN   llx_categorie cat ON cat.rowid = cp.fk_categorie\n"
        f"           WHERE  cp.fk_product = (\n"
        f"{sub_producto}\n"
        f"           )\n"
        f"             AND  cat.fk_parent = (\n"
        f"                      SELECT c.rowid FROM llx_categorie c\n"
        f"                      WHERE  c.label     = '{cat_esc}'\n"
        f"                        AND  c.type      = {TYPE_CAT}\n"
        f"                        AND  c.entity    = {ENTITY}\n"
        f"                        AND  c.fk_parent = 0\n"
        f"                      LIMIT 1\n"
        f"                  )\n"
        f"             AND  cat.rowid != (\n"
        f"{sub_marca}\n"  # No borra la relación correcta si ya existe
        f"             )\n"
        f"       );\n"

        # INSERT IGNORE: establece la relación correcta (idempotente).
        # Si el DELETE anterior dejó la fila correcta intacta, IGNORE la omite.
        f"INSERT IGNORE INTO llx_categorie_product (fk_categorie, fk_product)\n"
        f"SELECT (\n"
        f"{sub_marca}\n"
        f"), p.rowid\n"
        f"FROM   llx_product p\n"
        f"WHERE  p.{CAMPO_PRODUCTO_BD} = '{prod_esc}'\n"
        f"  AND  p.entity = {ENTITY}\n"
        f"LIMIT 1;\n"
    )


# =============================================================================
# LECTURA DEL CSV
# =============================================================================

def leer_csv(ruta: str) -> tuple[list, list]:
    """
    Lee el CSV y construye la lista de bloques SQL y advertencias.

    Args:
        ruta: Ruta al archivo CSV.

    Returns:
        tuple: (lista de bloques SQL, lista de advertencias)
    """
    bloques      = []
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

            if not producto:
                advertencias.append(f"Fila {num}: identificador de producto vacío, se omite.")
                continue
            if not marca:
                advertencias.append(f"Fila {num}: producto '{producto}' sin marca, se omite.")
                continue

            bloques.append(construir_bloque(producto, marca))

    return bloques, advertencias


# =============================================================================
# ESCRITURA DEL ARCHIVO SQL
# =============================================================================

def escribir_sql(bloques: list, advertencias: list) -> None:
    """
    Escribe el archivo SQL final con cabecera, bloques y advertencias.

    Args:
        bloques:      Lista de bloques DELETE+INSERT generados.
        advertencias: Lista de advertencias a incluir como comentarios.
    """
    os.makedirs(os.path.dirname(ARCHIVO_SQL), exist_ok=True)

    with open(ARCHIVO_SQL, 'w', encoding='utf-8') as f:
        f.write("-- =============================================================\n")
        f.write("-- CORRECCIÓN RELACIONES PRODUCTO-MARCA — llx_categorie_product\n")
        f.write(f"-- Generado  : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write( "-- Autor     : Carlos Vico\n")
        f.write(f"-- Origen    : {ARCHIVO_CSV}\n")
        f.write(f"-- Campo     : llx_product.{CAMPO_PRODUCTO_BD}\n")
        f.write(f"-- Cat. raíz : {CATEGORIA_MARCAS}\n")
        f.write(f"-- Productos : {len(bloques)}\n")
        f.write("-- Estrategia: DELETE marcas incorrectas + INSERT IGNORE marca correcta\n")
        f.write("-- Motivo    : PK compuesta (fk_categorie, fk_product) impide UPDATE directo\n")
        f.write("-- =============================================================\n\n")
        f.write("START TRANSACTION;\n\n")

        for bloque in bloques:
            f.write(bloque)
            f.write("\n")

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
    """Orquesta la lectura del CSV y la generación del SQL de corrección."""
    print("=" * 70)
    print(" 🔧 GENERADOR SQL — CORRECCIÓN RELACIONES PRODUCTO-MARCA")
    print("=" * 70)
    print(f" 🔍 Buscando productos por: llx_product.{CAMPO_PRODUCTO_BD}")
    print(f" 🏷️  Categoría raíz de marcas: '{CATEGORIA_MARCAS}'")

    if not os.path.exists(ARCHIVO_CSV):
        print(f" ❌ Archivo no encontrado: '{ARCHIVO_CSV}'")
        sys.exit(1)

    print(f" 📄 Leyendo: {ARCHIVO_CSV}")

    try:
        bloques, advertencias = leer_csv(ARCHIVO_CSV)
    except Exception as exc:
        print(f" ❌ Error al leer el CSV: {exc}")
        sys.exit(1)

    if not bloques:
        print(" ⚠️  No se generó ninguna sentencia. Revisa el CSV y las advertencias.")
        for warn in advertencias:
            print(f"    - {warn}")
        return

    try:
        escribir_sql(bloques, advertencias)
    except Exception as exc:
        print(f" ❌ Error al escribir el SQL: {exc}")
        return

    print(f"\n ✅ SQL generado: {ARCHIVO_SQL}")
    print(f"    Productos procesados: {len(bloques)}")
    if advertencias:
        print(f"    Advertencias       : {len(advertencias)} — revísalas en el archivo SQL.")

    print("=" * 70)
    print(" ✨ Listo. Revisa el SQL y ejecútalo en phpMyAdmin.")
    print("=" * 70)


if __name__ == "__main__":
    main()