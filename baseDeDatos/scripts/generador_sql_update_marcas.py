#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script: generador_sql_update_marcas.py
Autor:  Carlos Vico

Propósito:
    Genera un archivo SQL que actualiza la estructura de categorías de marcas
    en Dolibarr. La lógica distingue entre marcas existentes y nuevas:

    - Marcas EXISTENTES: se actualizan sus datos (label, visible, position)
      mediante UPDATE condicional usando el nombre como clave de búsqueda.
    - Marcas NUEVAS:     se insertan como subcategorías de "Marcas" usando
      INSERT IGNORE para evitar duplicados en ejecuciones repetidas.
    - Productos:         se asocian a su marca usando INSERT IGNORE en
      llx_categorie_product (idempotente).

Entrada:
    CSV separado por ';' con columnas:
      - Código : referencia del producto (ref en llx_product).
      - Marca  : nombre de la marca.

Salida:
    Archivo SQL con timestamp en data/output/ listo para ejecutar en phpMyAdmin.

Uso:
    1. Ajustar las constantes de configuración.
    2. Ejecutar: python generador_sql_update_marcas.py
    3. Revisar y ejecutar el SQL generado en la BD.
"""

import pandas as pd
import os
from datetime import datetime

# =============================================================================
# CONFIGURACIÓN (modificar según el entorno)
# =============================================================================

ARCHIVO_ENTRADA = "data/input/pajaro_final_finalisimo_de_los_finales_finalizados.csv"  # Ruta al CSV de entrada
ARCHIVO_SALIDA = (
    f"data/output/update_marcas_categoria_"
    f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
)

SEP      = ';'
ENCODING = 'utf-8'

# Nombres exactos de las columnas del CSV (respetar mayúsculas y acentos)
COL_CODIGO = 'Ref'
COL_MARCA  = 'Marca'

# Categoría raíz que agrupa todas las marcas en Dolibarr
CATEGORIA_MARCAS = 'Marcas'

# Valores por defecto para llx_categorie
ENTITY   = 1   # Entidad Dolibarr
TYPE     = 0   # 0 = categoría de productos
VISIBLE  = 1
POSITION = 0

# =============================================================================
# MARCAS QUE YA EXISTEN EN LA BASE DE DATOS
# Rellenar con los nombres exactos tal como aparecen en llx_categorie.label
# Estas marcas recibirán UPDATE; el resto recibirán INSERT IGNORE.
# =============================================================================
MARCAS_EXISTENTES: set = {
    # Ejemplo:
    # 'Nike',
    # 'Adidas',
}


# =============================================================================
# UTILIDADES SQL
# =============================================================================

def escape_sql(valor) -> str:
    """
    Escapa un valor para uso seguro en sentencias SQL.

    Retorna 'NULL' si el valor está vacío o es NaN.
    De lo contrario, envuelve en comillas simples escapando las internas.
    No se usa para valores numéricos controlados internamente.

    Args:
        valor: Valor a escapar (string, float, int o None).

    Returns:
        str: Valor listo para insertar en SQL.
    """
    if pd.isna(valor) or str(valor).strip() == '':
        return 'NULL'
    return "'{}'".format(str(valor).replace("'", "''"))


# =============================================================================
# LECTURA Y VALIDACIÓN DEL CSV
# =============================================================================

def leer_csv(ruta: str) -> pd.DataFrame | None:
    """
    Lee el CSV de entrada y valida su estructura básica.

    Args:
        ruta: Ruta al archivo CSV.

    Returns:
        DataFrame limpio o None si hay un error irrecuperable.
    """
    if not os.path.exists(ruta):
        print(f" ❌ Archivo no encontrado: '{ruta}'")
        return None

    try:
        df = pd.read_csv(
            ruta,
            sep=SEP,
            encoding=ENCODING,
            engine='python',
            quotechar='"',
            skipinitialspace=True,
            on_bad_lines='warn'
        )
    except Exception as exc:
        print(f" ❌ Error al leer el CSV: {exc}")
        return None

    # Normalizar nombres de columna para evitar fallos por espacios extra
    df.columns = [col.strip() for col in df.columns]

    print("\n 📋 Columnas detectadas:")
    for col in df.columns:
        print(f"    - '{col}'")

    if COL_CODIGO not in df.columns or COL_MARCA not in df.columns:
        print(
            f" ❌ Faltan columnas obligatorias: "
            f"'{COL_CODIGO}' y/o '{COL_MARCA}'"
        )
        return None

    # Eliminar filas incompletas en las columnas clave
    df = df.dropna(subset=[COL_CODIGO, COL_MARCA])
    df = df[df[COL_CODIGO].astype(str).str.strip() != '']
    df = df[df[COL_MARCA].astype(str).str.strip() != '']

    return df


# =============================================================================
# GENERACIÓN DE BLOQUES SQL
# =============================================================================

def sql_cabecera(f, total_marcas: int, total_productos: int) -> None:
    """Escribe la cabecera informativa y abre la transacción."""
    f.write("-- =============================================================\n")
    f.write("-- UPDATE/INSERT CATEGORÍAS DE MARCAS - DOLIBARR\n")
    f.write(f"-- Generado : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    f.write(f"-- Autor    : Carlos Vico\n")
    f.write(f"-- Marcas   : {total_marcas}\n")
    f.write(f"-- Productos: {total_productos}\n")
    f.write("-- =============================================================\n\n")
    f.write("START TRANSACTION;\n\n")


def sql_categoria_principal(f) -> None:
    """
    Garantiza que la categoría raíz 'Marcas' exista.
    INSERT IGNORE es idempotente: no falla si ya existe.
    """
    cat_esc = escape_sql(CATEGORIA_MARCAS)
    f.write("-- -------------------------------------------------------\n")
    f.write("-- 1. Asegurar que existe la categoría principal 'Marcas'\n")
    f.write("-- -------------------------------------------------------\n")
    f.write("INSERT IGNORE INTO llx_categorie\n")
    f.write("    (label, type, entity, visible, position, fk_parent, description, color)\n")
    f.write(f"VALUES ({cat_esc}, {TYPE}, {ENTITY}, {VISIBLE}, {POSITION}, 0, NULL, NULL);\n\n")


def sql_marcas(f, marcas_unicas: list) -> None:
    """
    Genera las sentencias para cada marca según si existe o no:

    - Existente → UPDATE que actualiza visible y position sin cambiar rowid.
    - Nueva     → INSERT IGNORE como subcategoría de 'Marcas'.

    Args:
        f:             Fichero de escritura abierto.
        marcas_unicas: Lista de nombres de marca únicos extraídos del CSV.
    """
    cat_esc = escape_sql(CATEGORIA_MARCAS)

    nuevas    = [m for m in marcas_unicas if m not in MARCAS_EXISTENTES]
    existentes = [m for m in marcas_unicas if m in MARCAS_EXISTENTES]

    # --- UPDATE para marcas que ya están en BD ---
    if existentes:
        f.write("-- -------------------------------------------------------\n")
        f.write("-- 2a. UPDATE de marcas existentes en llx_categorie\n")
        f.write("--     Solo actualiza metadatos; no toca el rowid ni fk_parent\n")
        f.write("-- -------------------------------------------------------\n")
        for marca in existentes:
            marca_esc = escape_sql(marca)
            f.write(f"UPDATE llx_categorie\n")
            f.write(f"SET    visible = {VISIBLE},\n")
            f.write(f"       position = {POSITION}\n")
            f.write(f"WHERE  label = {marca_esc}\n")
            f.write(f"  AND  type = {TYPE}\n")
            f.write(f"  AND  entity = {ENTITY}\n")
            # Restricción al subárbol de 'Marcas' para no tocar otras categorías homónimas
            f.write(f"  AND  fk_parent = (\n")
            f.write(f"       SELECT c.rowid FROM llx_categorie c\n")
            f.write(f"       WHERE c.label = {cat_esc} AND c.type = {TYPE} AND c.fk_parent = 0\n")
            f.write(f"  );\n")
        f.write("\n")

    # --- INSERT IGNORE para marcas nuevas ---
    if nuevas:
        f.write("-- -------------------------------------------------------\n")
        f.write("-- 2b. INSERT de marcas nuevas como subcategorías de 'Marcas'\n")
        f.write("--     INSERT IGNORE evita duplicados en re-ejecuciones\n")
        f.write("-- -------------------------------------------------------\n")
        for marca in nuevas:
            marca_esc = escape_sql(marca)
            f.write("INSERT IGNORE INTO llx_categorie\n")
            f.write("    (label, type, entity, visible, position, fk_parent, description, color)\n")
            f.write(f"SELECT {marca_esc}, {TYPE}, {ENTITY}, {VISIBLE}, {POSITION},\n")
            f.write(f"       c.rowid, NULL, NULL\n")
            f.write(f"FROM   llx_categorie c\n")
            f.write(f"WHERE  c.label = {cat_esc}\n")
            f.write(f"  AND  c.type = {TYPE}\n")
            f.write(f"  AND  c.fk_parent = 0;\n")
        f.write("\n")


def sql_asociar_productos(f, df: pd.DataFrame, total: int) -> None:
    """
    Asocia cada producto a su categoría-marca en llx_categorie_product.

    Usa INSERT IGNORE porque la tabla tiene UNIQUE KEY (fk_categorie, fk_product),
    lo que hace la operación idempotente y segura ante re-ejecuciones.

    Args:
        f:     Fichero de escritura abierto.
        df:    DataFrame con columnas COL_CODIGO y COL_MARCA.
        total: Total de filas para mostrar progreso.
    """
    cat_esc = escape_sql(CATEGORIA_MARCAS)

    f.write("-- -------------------------------------------------------\n")
    f.write("-- 3. Asociar productos a su categoría-marca\n")
    f.write("--    INSERT IGNORE es idempotente (no duplica relaciones)\n")
    f.write("-- -------------------------------------------------------\n")

    for idx, row in df.iterrows():
        codigo = str(row[COL_CODIGO]).strip()
        marca  = str(row[COL_MARCA]).strip()

        if not codigo or not marca:
            continue

        codigo_esc = escape_sql(codigo)
        marca_esc  = escape_sql(marca)

        f.write(f"-- [{idx + 1}/{total}] ref={codigo} -> marca={marca}\n")
        f.write("INSERT IGNORE INTO llx_categorie_product (fk_categorie, fk_product)\n")
        f.write("SELECT cat.rowid, p.rowid\n")
        f.write("FROM   llx_categorie cat\n")
        f.write("JOIN   llx_product   p   ON p.ref = {}\n".format(codigo_esc))
        f.write(f"WHERE  cat.label = {marca_esc}\n")
        f.write(f"  AND  cat.type = {TYPE}\n")
        f.write("  AND  cat.fk_parent = (\n")
        f.write("       SELECT c2.rowid FROM llx_categorie c2\n")
        f.write(f"       WHERE c2.label = {cat_esc} AND c2.type = {TYPE} AND c2.fk_parent = 0\n")
        f.write("  );\n")

        # Separador visual cada 100 filas para facilitar lectura del SQL
        if (idx + 1) % 100 == 0:
            f.write(f"\n-- ··· {idx + 1} de {total} productos procesados ···\n\n")
            print(f"    → {idx + 1} / {total} productos escritos...")

    f.write("\nCOMMIT;\n")


# =============================================================================
# FUNCIÓN PRINCIPAL
# =============================================================================

def main() -> None:
    """Orquesta la lectura del CSV y la generación del archivo SQL."""
    print("=" * 70)
    print(" 🏷️  GENERADOR SQL UPDATE — CATEGORÍAS DE MARCAS (DOLIBARR)")
    print("=" * 70)

    df = leer_csv(ARCHIVO_ENTRADA)
    if df is None:
        return

    marcas_unicas: list = (
        df[COL_MARCA]
        .astype(str)
        .str.strip()
        .unique()
        .tolist()
    )
    marcas_unicas = [m for m in marcas_unicas if m]

    total_productos = len(df)
    total_marcas    = len(marcas_unicas)

    print(f"\n 📊 Marcas únicas  : {total_marcas}")
    print(f"    Existentes en BD: {len([m for m in marcas_unicas if m in MARCAS_EXISTENTES])}")
    print(f"    Nuevas          : {len([m for m in marcas_unicas if m not in MARCAS_EXISTENTES])}")
    print(f" 📦 Productos válidos: {total_productos}")

    if total_productos == 0:
        print("\n ⚠️  Sin productos para procesar. Saliendo.")
        return

    # Crear directorio de salida si no existe
    os.makedirs(os.path.dirname(ARCHIVO_SALIDA), exist_ok=True)

    try:
        with open(ARCHIVO_SALIDA, 'w', encoding='utf-8') as f:
            sql_cabecera(f, total_marcas, total_productos)
            sql_categoria_principal(f)
            sql_marcas(f, marcas_unicas)
            sql_asociar_productos(f, df, total_productos)

        print(f"\n ✅ SQL generado: {ARCHIVO_SALIDA}")
        print(f"    Marcas procesadas : {total_marcas}")
        print(f"    Productos incluidos: {total_productos}")

    except Exception as exc:
        print(f" ❌ Error al escribir el SQL: {exc}")
        return

    print("=" * 70)
    print(" ✨ Listo. Revisa el SQL y ejecútalo en phpMyAdmin.")
    print("=" * 70)


if __name__ == "__main__":
    main()