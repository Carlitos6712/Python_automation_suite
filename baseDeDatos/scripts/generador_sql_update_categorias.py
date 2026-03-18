#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script: generador_sql_update_categorias.py
Autor:  Carlos Vico

Propósito:
    Genera un archivo SQL que corrige las categorías asignadas a productos
    en Dolibarr, eliminando TODAS las relaciones de categoría del producto
    excepto las que pertenecen a ramas protegidas (ej: Marcas).

    Problema resuelto:
      Un producto puede acumular relaciones erróneas en distintos niveles:
        - Categorías sueltas sin padre (ej: 'Perros' con fk_parent = 0)
        - Subcategorías de ramas incorrectas (ej: 'Perros >> Otros Perros')
        - Categorías correctas de ejecuciones anteriores (ej: 'Tpv >> Perros')
      El DELETE elimina TODAS las relaciones de categoría del producto,
      excepto las que pertenezcan a ramas protegidas (CATEGORIAS_PROTEGIDAS).
      Después, INSERT IGNORE establece únicamente la relación correcta.

    Estrategia por producto:
      1. DELETE de todas las relaciones cuya categoría NO pertenece a ninguna
         rama protegida. Esto cubre cualquier nivel del árbol.
      2. INSERT IGNORE de la relación correcta según el CSV (idempotente).

Entrada:
    CSV separado por ';' con columnas:
      - Ref       : referencia del producto (ref en llx_product).
      - Categoria : nombre de la categoría correcta (hija de CATEGORIA_RAIZ).

Salida:
    Archivo SQL con timestamp en data/output/ listo para ejecutar en phpMyAdmin.

Uso:
    1. Ajustar CATEGORIAS_PROTEGIDAS con todas las ramas que NO deben tocarse.
    2. Ajustar las demás constantes de configuración.
    3. Ejecutar: python generador_sql_update_categorias.py
    4. Revisar y ejecutar el SQL generado en la BD.
"""

import pandas as pd
import os
from datetime import datetime

# =============================================================================
# CONFIGURACIÓN (modificar según el entorno)
# =============================================================================

ARCHIVO_ENTRADA = "data/input/pajaro_final_finalisimo_de_los_finales_finalizados.csv"  # Ruta al CSV de entrada
ARCHIVO_SALIDA = (
    f"data/output/update_categorias_"
    f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
)

SEP      = ';'
ENCODING = 'utf-8'

# Nombres exactos de las columnas del CSV (respetar mayúsculas y acentos)
COL_CODIGO    = 'Ref'
COL_CATEGORIA = 'Categoria'

# Categoría raíz de la que dependen las categorías gestionadas (ej: 'tpv')
CATEGORIA_RAIZ = 'Tpv'

# =============================================================================
# RAMAS PROTEGIDAS — sus categorías y subcategorías NO serán eliminadas
# Añadir aquí el nombre de cada categoría raíz de rama que debe preservarse.
# El DELETE excluirá cualquier categoría cuyo ancestro esté en esta lista.
#
# Ejemplo: 'Marcas' protege 'Marcas', 'Marcas >> Dibaq', 'Marcas >> Nike', etc.
# =============================================================================
CATEGORIAS_PROTEGIDAS: set = {
    'Marcas',
    # Añadir más raíces de ramas protegidas si es necesario
}

# Parámetros fijos de Dolibarr
ENTITY   = 1   # Entidad Dolibarr
TYPE     = 0   # 0 = categoría de productos
VISIBLE  = 1
POSITION = 0

# =============================================================================
# CATEGORÍAS QUE YA EXISTEN EN LA BASE DE DATOS (hijas de CATEGORIA_RAIZ)
# Rellenar con los nombres exactos tal como aparecen en llx_categorie.label.
# Estas recibirán UPDATE; el resto recibirán INSERT IGNORE.
#
# Consulta para obtenerlas:
#   SELECT c.label FROM llx_categorie c
#   JOIN llx_categorie raiz ON raiz.rowid = c.fk_parent
#   WHERE raiz.label = 'tpv' AND c.type = 0 AND c.entity = 1;
# =============================================================================
CATEGORIAS_EXISTENTES: set = {
    # Ejemplo:
    # 'Perros',
    # 'Gatos',
}


# =============================================================================
# UTILIDADES SQL
# =============================================================================

def escape_sql(valor) -> str:
    """
    Escapa un valor para uso seguro en sentencias SQL.

    Retorna 'NULL' si el valor está vacío o es NaN.
    De lo contrario, envuelve en comillas simples escapando las internas.

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

    df.columns = [col.strip() for col in df.columns]

    print("\n 📋 Columnas detectadas:")
    for col in df.columns:
        print(f"    - '{col}'")

    for col in [COL_CODIGO, COL_CATEGORIA]:
        if col not in df.columns:
            print(f" ❌ Columna obligatoria no encontrada: '{col}'")
            return None

    df = df.dropna(subset=[COL_CODIGO, COL_CATEGORIA])
    df = df[df[COL_CODIGO].astype(str).str.strip() != '']
    df = df[df[COL_CATEGORIA].astype(str).str.strip() != '']

    return df


# =============================================================================
# SUBCONSULTAS REUTILIZABLES
# =============================================================================

def sub_rowid_raiz(raiz_esc: str) -> str:
    """Rowid de la categoría raíz (tpv)."""
    return (
        f"        SELECT rowid FROM llx_categorie\n"
        f"        WHERE  label  = {raiz_esc}\n"
        f"          AND  type   = {TYPE}\n"
        f"          AND  entity = {ENTITY}\n"
        f"        LIMIT 1"
    )


def sub_rowid_categoria(cat_esc: str, raiz_esc: str) -> str:
    """Rowid de la categoría correcta hija de la raíz."""
    return (
        f"    SELECT c.rowid FROM llx_categorie c\n"
        f"    WHERE  c.label     = {cat_esc}\n"
        f"      AND  c.type      = {TYPE}\n"
        f"      AND  c.entity    = {ENTITY}\n"
        f"      AND  c.fk_parent = (\n"
        f"{sub_rowid_raiz(raiz_esc)}\n"
        f"      )\n"
        f"    LIMIT 1"
    )


def sub_rowid_producto(codigo_esc: str) -> str:
    """Rowid del producto por ref."""
    return (
        f"    SELECT rowid FROM llx_product\n"
        f"    WHERE  ref    = {codigo_esc}\n"
        f"      AND  entity = {ENTITY}\n"
        f"    LIMIT 1"
    )


def fragmento_exclusion_protegidas() -> str:
    """
    Genera el bloque SQL que excluye del DELETE las categorías pertenecientes
    a ramas protegidas, a cualquier nivel del árbol (raíz, hija, nieta...).

    La lógica usa tres niveles de ancestros para cubrir árboles de hasta
    3 niveles de profundidad, que es el caso habitual en Dolibarr:
      - Nivel 0: la propia categoría es una raíz protegida.
      - Nivel 1: su padre directo es una raíz protegida.
      - Nivel 2: su abuelo es una raíz protegida.

    Returns:
        str: Fragmento AND NOT IN (...) listo para insertar en el DELETE.
    """
    # Construir lista de valores SQL para el IN de las ramas protegidas
    protegidas_sql = ", ".join(escape_sql(p) for p in CATEGORIAS_PROTEGIDAS)

    return (
        f"  AND  cp.fk_categorie NOT IN (\n"
        f"       -- Excluir categorías cuyo ancestro (hasta 2 niveles) sea una rama protegida\n"
        f"       SELECT c.rowid FROM llx_categorie c\n"
        f"       LEFT JOIN llx_categorie padre  ON padre.rowid  = c.fk_parent\n"
        f"       LEFT JOIN llx_categorie abuelo ON abuelo.rowid = padre.fk_parent\n"
        f"       WHERE  c.type   = {TYPE}\n"
        f"         AND  c.entity = {ENTITY}\n"
        f"         AND  (\n"
        f"                  c.label      IN ({protegidas_sql})  -- propia es raíz protegida\n"
        f"               OR padre.label  IN ({protegidas_sql})  -- padre es raíz protegida\n"
        f"               OR abuelo.label IN ({protegidas_sql})  -- abuelo es raíz protegida\n"
        f"             )\n"
        f"  )"
    )


# =============================================================================
# GENERACIÓN DE BLOQUES SQL
# =============================================================================

def sql_cabecera(f, total_cats: int, total_productos: int) -> None:
    """Escribe la cabecera informativa y abre la transacción."""
    protegidas_str = ', '.join(f"'{p}'" for p in CATEGORIAS_PROTEGIDAS)
    f.write("-- =============================================================\n")
    f.write(f"-- CORRECCIÓN CATEGORÍAS (raíz: '{CATEGORIA_RAIZ}') — DOLIBARR\n")
    f.write(f"-- Generado    : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    f.write( "-- Autor       : Carlos Vico\n")
    f.write(f"-- Raíz        : {CATEGORIA_RAIZ}\n")
    f.write(f"-- Protegidas  : {protegidas_str}\n")
    f.write(f"-- Categorías  : {total_cats}\n")
    f.write(f"-- Productos   : {total_productos}\n")
    f.write("-- Estrategia  : DELETE todas excepto ramas protegidas + INSERT IGNORE\n")
    f.write("-- =============================================================\n\n")
    f.write("START TRANSACTION;\n\n")


def sql_categorias(f, categorias: list) -> None:
    """
    Garantiza que cada categoría del CSV exista como hija de CATEGORIA_RAIZ.

    Args:
        f:          Fichero de escritura abierto.
        categorias: Lista de nombres de categoría únicos del CSV.
    """
    raiz_esc   = escape_sql(CATEGORIA_RAIZ)
    existentes = [c for c in categorias if c in CATEGORIAS_EXISTENTES]
    nuevas     = [c for c in categorias if c not in CATEGORIAS_EXISTENTES]

    f.write("-- -------------------------------------------------------\n")
    f.write(f"-- 1. Categorías hijas de '{CATEGORIA_RAIZ}'\n")
    f.write("-- -------------------------------------------------------\n\n")

    if existentes:
        f.write("-- 1a. UPDATE de categorías existentes\n")
        for cat in existentes:
            cat_esc = escape_sql(cat)
            f.write("UPDATE llx_categorie\n")
            f.write(f"SET    visible = {VISIBLE}, position = {POSITION}\n")
            f.write(f"WHERE  label     = {cat_esc}\n")
            f.write(f"  AND  type      = {TYPE}\n")
            f.write(f"  AND  entity    = {ENTITY}\n")
            f.write( "  AND  fk_parent = (\n")
            f.write(f"{sub_rowid_raiz(raiz_esc)}\n")
            f.write( "  );\n")
        f.write("\n")

    if nuevas:
        f.write(f"-- 1b. INSERT de categorías nuevas como hijas de '{CATEGORIA_RAIZ}'\n")
        for cat in nuevas:
            cat_esc = escape_sql(cat)
            f.write("INSERT IGNORE INTO llx_categorie\n")
            f.write("    (label, type, entity, visible, position, fk_parent, description, color)\n")
            f.write(f"SELECT {cat_esc}, {TYPE}, {ENTITY}, {VISIBLE}, {POSITION},\n")
            f.write( "       raiz.rowid, NULL, NULL\n")
            f.write( "FROM   llx_categorie raiz\n")
            f.write(f"WHERE  raiz.label  = {raiz_esc}\n")
            f.write(f"  AND  raiz.type   = {TYPE}\n")
            f.write(f"  AND  raiz.entity = {ENTITY}\n")
            f.write( "LIMIT 1;\n")
        f.write("\n")


def sql_asociar_productos(f, df: pd.DataFrame, total: int) -> None:
    """
    Corrige relaciones producto-categoría con DELETE total + INSERT IGNORE.

    El DELETE elimina TODAS las relaciones de categoría del producto,
    excepto las que pertenecen a ramas protegidas (a cualquier nivel).
    Esto cubre categorías sueltas, subcategorías de ramas incorrectas
    y cualquier asignación residual de ejecuciones anteriores.

    Args:
        f:     Fichero de escritura abierto.
        df:    DataFrame con columnas COL_CODIGO y COL_CATEGORIA.
        total: Total de filas para el log de progreso.
    """
    raiz_esc          = escape_sql(CATEGORIA_RAIZ)
    exclusion_sql     = fragmento_exclusion_protegidas()

    f.write("-- -------------------------------------------------------\n")
    f.write("-- 2. Corregir relaciones producto-categoría\n")
    f.write("--    DELETE: todas excepto ramas protegidas\n")
    f.write("--    INSERT IGNORE: asigna la categoría correcta del CSV\n")
    f.write("-- -------------------------------------------------------\n\n")

    for idx, row in df.iterrows():
        codigo    = str(row[COL_CODIGO]).strip()
        categoria = str(row[COL_CATEGORIA]).strip()

        if not codigo or not categoria:
            continue

        codigo_esc = escape_sql(codigo)
        cat_esc    = escape_sql(categoria)

        sub_cat      = sub_rowid_categoria(cat_esc, raiz_esc)
        sub_producto = sub_rowid_producto(codigo_esc)

        f.write(f"-- [{idx + 1}/{total}] ref={codigo} -> categoria={categoria}\n")

        # DELETE: elimina todas las relaciones excepto las de ramas protegidas
        f.write("DELETE cp FROM llx_categorie_product cp\n")
        f.write("JOIN   llx_categorie c ON c.rowid = cp.fk_categorie\n")
        f.write("WHERE  cp.fk_product = (\n")
        f.write(f"{sub_producto}\n")
        f.write(")\n")
        f.write(f"{exclusion_sql};\n")

        # INSERT IGNORE: establece la categoría correcta (idempotente)
        f.write("INSERT IGNORE INTO llx_categorie_product (fk_categorie, fk_product)\n")
        f.write("SELECT (\n")
        f.write(f"{sub_cat}\n")
        f.write("), p.rowid\n")
        f.write("FROM   llx_product p\n")
        f.write(f"WHERE  p.ref    = {codigo_esc}\n")
        f.write(f"  AND  p.entity = {ENTITY}\n")
        f.write("LIMIT 1;\n\n")

        if (idx + 1) % 100 == 0:
            f.write(f"-- ··· {idx + 1} de {total} productos procesados ···\n\n")
            print(f"    → {idx + 1} / {total} productos escritos...")

    f.write("COMMIT;\n")


# =============================================================================
# FUNCIÓN PRINCIPAL
# =============================================================================

def main() -> None:
    """Orquesta la lectura del CSV y la generación del archivo SQL."""
    print("=" * 70)
    print(f" 📂 GENERADOR SQL — CATEGORÍAS HIJAS DE '{CATEGORIA_RAIZ}' (DOLIBARR)")
    print("=" * 70)
    print(f" 🔒 Ramas protegidas: {', '.join(CATEGORIAS_PROTEGIDAS)}")

    df = leer_csv(ARCHIVO_ENTRADA)
    if df is None:
        return

    categorias_unicas: list = (
        df[COL_CATEGORIA]
        .astype(str)
        .str.strip()
        .unique()
        .tolist()
    )
    categorias_unicas = [c for c in categorias_unicas if c]

    total_productos = len(df)
    total_cats      = len(categorias_unicas)

    print(f"\n 📊 Categorías únicas : {total_cats}")
    print(f"    Existentes en BD  : {len([c for c in categorias_unicas if c in CATEGORIAS_EXISTENTES])}")
    print(f"    Nuevas            : {len([c for c in categorias_unicas if c not in CATEGORIAS_EXISTENTES])}")
    print(f" 📦 Productos válidos  : {total_productos}")

    if total_productos == 0:
        print("\n ⚠️  Sin productos para procesar. Saliendo.")
        return

    os.makedirs(os.path.dirname(ARCHIVO_SALIDA), exist_ok=True)

    try:
        with open(ARCHIVO_SALIDA, 'w', encoding='utf-8') as f:
            sql_cabecera(f, total_cats, total_productos)
            sql_categorias(f, categorias_unicas)
            sql_asociar_productos(f, df, total_productos)

        print(f"\n ✅ SQL generado: {ARCHIVO_SALIDA}")
        print(f"    Categorías  : {total_cats}")
        print(f"    Productos   : {total_productos}")

    except Exception as exc:
        print(f" ❌ Error al escribir el SQL: {exc}")
        return

    print("=" * 70)
    print(" ✨ Listo. Revisa el SQL y ejecútalo en phpMyAdmin.")
    print("=" * 70)


if __name__ == "__main__":
    main()