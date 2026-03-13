#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script: asignar_categoria_tpv_a_todos.py
Propósito: Genera un archivo SQL para:
           1. Crear la categoría 'Tpv' en llx_categorie (si no existe).
           2. Asignar dicha categoría a todos los productos de llx_product
              que aún no la tengan asignada.

Salida: Archivo SQL con nombre dinámico (fecha y hora) en la carpeta 'data/output/'.
        El SQL realiza los siguientes pasos:
           - Inserta la categoría 'Tpv' si no existe (INSERT IGNORE).
           - Obtiene su ID en una variable SQL.
           - Asigna la categoría a todos los productos que no la tengan.
           - Muestra el número de relaciones insertadas (para verificación).

Uso:
    1. Ejecutar el script.
    2. Revisar el archivo SQL generado.
    3. Ejecutarlo en phpMyAdmin o herramienta similar.
"""

import os
from datetime import datetime

# =============================================================================
# CONFIGURACIÓN DEL USUARIO (modificar si es necesario)
# =============================================================================
ARCHIVO_SALIDA = f"data/output/asignar_categoria_tpv_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"

# Datos de la categoría a crear/asignar
CATEGORIA_NOMBRE = 'Tpv'
CATEGORIA_TYPE = 0           # 0 = categoría de producto
ENTITY = 1                   # Entidad de Dolibarr (por defecto 1)
VISIBLE = 1                  # Visible en la web
POSITION = 0                 # Posición (orden)

# =============================================================================
# FUNCIÓN PRINCIPAL
# =============================================================================
def main():
    """Genera el archivo SQL con las instrucciones para asignar la categoría Tpv."""
    print("=" * 70)
    print(" 🏷️  GENERADOR SQL: ASIGNAR CATEGORÍA 'Tpv' A TODOS LOS PRODUCTOS")
    print("=" * 70)

    # Crear la carpeta de salida si no existe (para evitar errores)
    try:
        os.makedirs("data/output", exist_ok=True)
        print(" 📁 Carpeta 'data/output' verificada/creada.")
    except Exception as e:
        print(f" ❌ Error al crear la carpeta de salida: {e}")
        return

    # Generar el contenido del archivo SQL
    sql_content = generar_sql()

    # Escribir el archivo SQL
    try:
        with open(ARCHIVO_SALIDA, 'w', encoding='utf-8') as f:
            f.write(sql_content)
        print(f"\n ✅ Archivo SQL generado exitosamente:")
        print(f"    {ARCHIVO_SALIDA}")
    except Exception as e:
        print(f" ❌ Error al escribir el archivo SQL: {e}")
        return

    print("=" * 70)
    print(" ✨ Proceso completado. Revisa el archivo SQL y ejecútalo en phpMyAdmin.")
    print("=" * 70)


def generar_sql():
    """
    Construye el contenido del script SQL como un string.
    Incluye:
        - Cabecera con fecha y descripción.
        - START TRANSACTION.
        - Inserción de la categoría si no existe.
        - Obtención del ID de la categoría.
        - Asignación a productos sin esa categoría.
        - SELECT de verificación.
        - COMMIT.
    """
    lines = []
    lines.append("-- ===========================================================")
    lines.append("-- ASIGNAR CATEGORÍA 'Tpv' A TODOS LOS PRODUCTOS")
    lines.append(f"-- Generado el {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("-- ===========================================================")
    lines.append("")
    lines.append("START TRANSACTION;")
    lines.append("")

    # 1. Crear la categoría 'Tpv' si no existe
    lines.append("-- 1. Crear categoría 'Tpv' si no existe")
    lines.append(f"INSERT IGNORE INTO llx_categorie (label, type, entity, visible, position, fk_parent, description, color)")
    lines.append(f"VALUES ('{CATEGORIA_NOMBRE}', {CATEGORIA_TYPE}, {ENTITY}, {VISIBLE}, {POSITION}, 0, NULL, NULL);")
    lines.append("")

    # 2. Obtener el ID de la categoría (puede ser recién creada o existente)
    lines.append("-- 2. Obtener el ID de la categoría 'Tpv'")
    lines.append(f"SET @categorie_id := (SELECT rowid FROM llx_categorie WHERE label = '{CATEGORIA_NOMBRE}' AND type = {CATEGORIA_TYPE});")
    lines.append("")

    # 3. Asignar la categoría a todos los productos que aún no la tengan
    lines.append("-- 3. Asignar categoría a todos los productos (evitando duplicados)")
    lines.append("INSERT INTO llx_categorie_product (fk_categorie, fk_product)")
    lines.append("SELECT @categorie_id, p.rowid")
    lines.append("FROM llx_product p")
    lines.append("WHERE NOT EXISTS (")
    lines.append("    SELECT 1 FROM llx_categorie_product cp")
    lines.append("    WHERE cp.fk_categorie = @categorie_id AND cp.fk_product = p.rowid")
    lines.append(");")
    lines.append("")

    # 4. Mostrar cuántas relaciones se insertaron (opcional, para verificación)
    lines.append("-- 4. Mostrar número de relaciones insertadas (para verificación)")
    lines.append("SELECT ROW_COUNT() AS 'Relaciones insertadas';")
    lines.append("")

    lines.append("COMMIT;")
    lines.append("")

    return "\n".join(lines)


if __name__ == "__main__":
    main()