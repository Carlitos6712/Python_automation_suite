#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script: generador_sql_update_extrafields_marca.py
Autor:  Carlos Vico

Propósito:
    Genera un archivo SQL que sincroniza el campo 'marca' en
    llx_product_extrafields contra los datos del CSV, actuando solo
    cuando hay diferencia real. La estrategia por producto es:

    1. UPDATE con cláusula WHERE marca != valor_csv (o IS NULL)
       → Solo escribe si la marca almacenada difiere.
       → No toca filas que ya están correctas (sin escrituras innecesarias).

    2. INSERT IGNORE como red de seguridad
       → Si el producto no tiene fila en extrafields, la crea.
       → INSERT IGNORE es idempotente: no falla si la fila ya existe.

    El orden importa: primero UPDATE, luego INSERT IGNORE.
    Si la fila existe  → UPDATE actúa (si difiere), INSERT IGNORE no hace nada.
    Si la fila no existe → UPDATE no actúa, INSERT IGNORE la crea.
    Juntos cubren todos los casos sin necesidad de conocer el estado previo.

Entrada:
    CSV separado por ';' con columnas:
      - Código : referencia del producto (ref en llx_product).
      - Marca  : valor deseado en llx_product_extrafields.marca.

Salida:
    Archivo SQL con timestamp en data/output/ listo para ejecutar en phpMyAdmin.

Uso:
    1. Ajustar las constantes de configuración si es necesario.
    2. Ejecutar: python generador_sql_update_extrafields_marca.py
    3. Revisar y ejecutar el SQL generado.
"""

import pandas as pd
import os
from datetime import datetime

# =============================================================================
# CONFIGURACIÓN (modificar según el entorno)
# =============================================================================

ARCHIVO_ENTRADA = "data/input/pajaro_final_finalisimo_de_los_finales_finalizados.csv"  # Ruta al CSV de entrada
ARCHIVO_SALIDA = (
    f"data/output/update_extrafields_marca_"
    f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
)

SEP      = ';'
ENCODING = 'utf-8'

# Nombres exactos de las columnas del CSV (respetar mayúsculas y acentos)
COL_CODIGO = 'Ref'
COL_MARCA  = 'Marca'

# Nombre de la columna en llx_product_extrafields donde se guarda la marca
COL_EXTRAFIELD_MARCA = 'marca'


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
        str: Valor SQL listo para usar en una sentencia.
    """
    if pd.isna(valor) or str(valor).strip() == '':
        return 'NULL'
    return "'{}'".format(str(valor).replace("'", "''"))


# =============================================================================
# LECTURA Y VALIDACIÓN DEL CSV
# =============================================================================

def leer_csv(ruta: str) -> pd.DataFrame | None:
    """
    Lee el CSV de entrada y valida que contenga las columnas necesarias.

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

    # Descartar filas con datos incompletos en las columnas clave
    df = df.dropna(subset=[COL_CODIGO, COL_MARCA])
    df = df[df[COL_CODIGO].astype(str).str.strip() != '']
    df = df[df[COL_MARCA].astype(str).str.strip() != '']

    return df


# =============================================================================
# GENERACIÓN DE BLOQUES SQL
# =============================================================================

def sql_cabecera(f, total: int) -> None:
    """Escribe la cabecera informativa y abre la transacción."""
    f.write("-- =============================================================\n")
    f.write("-- SYNC llx_product_extrafields.marca — DOLIBARR\n")
    f.write(f"-- Generado  : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    f.write( "-- Autor     : Carlos Vico\n")
    f.write(f"-- Productos : {total}\n")
    f.write("-- Estrategia: UPDATE si difiere (o es NULL) + INSERT IGNORE si no existe\n")
    f.write("-- =============================================================\n\n")
    f.write("START TRANSACTION;\n\n")


def sql_sync_producto(f, codigo: str, marca: str, idx: int, total: int) -> None:
    """
    Genera el bloque UPDATE + INSERT IGNORE para un único producto.

    UPDATE:
      La condición '(marca IS NULL OR marca != valor)' asegura que MySQL
      solo escribe si hay diferencia real, incluido el caso en que el campo
      está a NULL. Esto evita escrituras innecesarias que dispararían
      triggers o inflarían el binlog.

    INSERT IGNORE:
      La subconsulta NOT EXISTS restringe la inserción a productos que
      todavía no tienen fila en extrafields. IGNORE descarta el error
      de clave duplicada si la fila ya existe, haciendo la operación
      idempotente ante re-ejecuciones.

    Args:
        f:      Fichero de escritura abierto.
        codigo: Referencia del producto (ref en llx_product).
        marca:  Valor deseado para el campo marca.
        idx:    Índice actual (para el comentario de progreso).
        total:  Total de productos (para el comentario de progreso).
    """
    codigo_esc = escape_sql(codigo)
    marca_esc  = escape_sql(marca)

    f.write(f"-- [{idx}/{total}] ref={codigo} -> marca={marca}\n")

    # UPDATE solo si la marca almacenada difiere (o es NULL)
    f.write("UPDATE llx_product_extrafields\n")
    f.write(f"SET    {COL_EXTRAFIELD_MARCA} = {marca_esc}\n")
    f.write( "WHERE  fk_object = (\n")
    f.write(f"           SELECT rowid FROM llx_product WHERE ref = {codigo_esc}\n")
    f.write( "       )\n")
    f.write(f"  AND  ({COL_EXTRAFIELD_MARCA} IS NULL OR {COL_EXTRAFIELD_MARCA} != {marca_esc});\n")

    # INSERT IGNORE crea la fila si todavía no existe para este producto
    f.write("INSERT IGNORE INTO llx_product_extrafields\n")
    f.write(f"    (fk_object, {COL_EXTRAFIELD_MARCA})\n")
    f.write(f"SELECT p.rowid, {marca_esc}\n")
    f.write( "FROM   llx_product p\n")
    f.write(f"WHERE  p.ref = {codigo_esc}\n")
    f.write( "  AND  NOT EXISTS (\n")
    f.write( "           SELECT 1 FROM llx_product_extrafields e\n")
    f.write( "           WHERE  e.fk_object = p.rowid\n")
    f.write( "       );\n\n")


def sql_cuerpo(f, df: pd.DataFrame) -> None:
    """
    Itera el DataFrame y emite el bloque SQL de sincronización
    para cada producto.

    Usa índice de columna (get_loc) para acceder de forma robusta a columnas
    cuyos nombres pueden contener caracteres especiales (acentos, etc.).

    Args:
        f:  Fichero de escritura abierto.
        df: DataFrame con las columnas COL_CODIGO y COL_MARCA.
    """
    total       = len(df)
    idx_codigo  = df.columns.get_loc(COL_CODIGO)
    idx_marca   = df.columns.get_loc(COL_MARCA)

    f.write("-- -------------------------------------------------------\n")
    f.write("-- Sincronización producto a producto\n")
    f.write("-- -------------------------------------------------------\n\n")

    for idx, row in enumerate(df.itertuples(index=False), start=1):
        codigo = str(row[idx_codigo]).strip()
        marca  = str(row[idx_marca]).strip()

        if not codigo or not marca:
            continue

        sql_sync_producto(f, codigo, marca, idx, total)

        # Separador visual cada 100 productos para facilitar lectura del SQL
        if idx % 100 == 0:
            f.write(f"-- ··· {idx} de {total} productos escritos ···\n\n")
            print(f"    → {idx} / {total} productos escritos...")

    f.write("COMMIT;\n")


# =============================================================================
# FUNCIÓN PRINCIPAL
# =============================================================================

def main() -> None:
    """Orquesta la lectura del CSV y la generación del SQL de sincronización."""
    print("=" * 70)
    print(" 🏷️  GENERADOR SQL SYNC — llx_product_extrafields.marca")
    print("=" * 70)

    df = leer_csv(ARCHIVO_ENTRADA)
    if df is None:
        return

    total = len(df)
    print(f"\n 📦 Productos a sincronizar: {total}")

    if total == 0:
        print("\n ⚠️  Sin productos para procesar. Saliendo.")
        return

    os.makedirs(os.path.dirname(ARCHIVO_SALIDA), exist_ok=True)

    try:
        with open(ARCHIVO_SALIDA, 'w', encoding='utf-8') as f:
            sql_cabecera(f, total)
            sql_cuerpo(f, df)

        print(f"\n ✅ SQL generado: {ARCHIVO_SALIDA}")
        print(f"    Productos incluidos: {total}")

    except Exception as exc:
        print(f" ❌ Error al escribir el SQL: {exc}")
        return

    print("=" * 70)
    print(" ✨ Listo. Revisa el SQL y ejecútalo en phpMyAdmin.")
    print("=" * 70)


if __name__ == "__main__":
    main()