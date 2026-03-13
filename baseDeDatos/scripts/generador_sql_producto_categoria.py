#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script: generador_sql_producto_categoria.py
Propósito: Genera un archivo SQL para insertar relaciones producto-categoría
           en Dolibarr a partir de un archivo CSV. Permite elegir si buscar
           el producto por 'ref' o por 'barcode'.

Entrada: Archivo CSV con las columnas:
         - Código (referencia del producto)
         - categoría
         - subcategoría

Salida: Archivo SQL con sentencias INSERT IGNORE INTO llx_categorie_product.
        Las categorías se pueden asignar mediante IDs fijos (si están en el
        diccionario CAT_IDS) o mediante búsquedas dinámicas por nombre.

Uso:
    1. Colocar el archivo CSV en la ruta especificada en ARCHIVO_CSV.
    2. Ajustar las constantes de configuración según necesidad.
    3. Ejecutar el script.
    4. Revisar el archivo SQL generado y ejecutarlo en phpMyAdmin.
"""

import csv
import sys
import os

# =============================================================================
# CONFIGURACIÓN DEL USUARIO (modificar según necesidades)
# =============================================================================
ARCHIVO_CSV = "data/input/archivo.csv"        # Ruta al CSV de entrada
ARCHIVO_SQL = "data/output/insert_category_product.sql"  # Archivo SQL de salida
DELIMITADOR = ","                                   # Separador del CSV
ENTITY = 1                                          # Entidad de Dolibarr
TYPE = 0                                            # Tipo categoría producto (0 = producto)
CAMPO_PRODUCTO = "ref"                              # 'ref' o 'barcode'

# Índices de columnas en el CSV (según la estructura esperada)
IDX_REF = 0      # Columna "Código" (puede ser ref o barcode)
IDX_CAT = 8      # Columna "categoría"
IDX_SUBCAT = 9   # Columna "subcategoría"

# =============================================================================
# DICCIONARIO DE IDs DE CATEGORÍAS (extraído de la base de datos)
# =============================================================================
# Las claves pueden ser:
# - Nombre de categoría padre (para categorías de primer nivel)
# - Tupla (nombre_padre, nombre_hijo) para subcategorías conocidas
CAT_IDS = {
    # Categorías de primer nivel (hijas de tpv)
    "Aves": 1141,
    "Ferretería y Varios": 1142,
    "Gatos": 1143,
    "Otros": 1144,
    "Peces y Acuariofilia": 1145,
    "Perros": 1146,
    "Plantas y Jardinería": 1147,
    "Reptiles y Anfibios": 1148,
    "Roedores": 1149,

    # Subcategorías (clave = (padre, hijo))
    ("Reptiles y Anfibios", "Otros Reptiles"): 1150,
    ("Reptiles y Anfibios", "Alimento y Sustrato"): 1151,
    ("Reptiles y Anfibios", "Animales Vivos"): 1152,
    ("Reptiles y Anfibios", "Iluminación"): 1153,
    ("Reptiles y Anfibios", "Hábitat"): 1154,
    ("Peces y Acuariofilia", "Alimentación"): 1155,
    ("Roedores", "Lecho"): 1156,
    ("Roedores", "Alojamiento"): 1157,
    ("Roedores", "Otros Roedores"): 1158,
    ("Perros", "Alimentación (Pienso y Húmeda)"): 1159,
    ("Perros", "Descanso y Ropa"): 1160,
    ("Perros", "Snacks y Premios"): 1161,
    ("Perros", "Otros Perros"): 1162,
    ("Perros", "Paseo y Control"): 1163,
    ("Perros", "Higiene y Salud"): 1164,
}

# =============================================================================
# FUNCIONES AUXILIARES
# =============================================================================
def escapar_string(s):
    """
    Escapa comillas simples para su uso seguro en sentencias SQL.
    Reemplaza cada comilla simple por dos comillas simples.
    """
    return s.replace("'", "''")

# =============================================================================
# FUNCIÓN PRINCIPAL
# =============================================================================
def generar_sql():
    """Lee el CSV, procesa cada fila y genera el archivo SQL."""
    print("=" * 70)
    print(" 🔄 GENERADOR SQL: RELACIONES PRODUCTO-CATEGORÍA")
    print("=" * 70)

    # Verificar existencia del archivo de entrada
    if not os.path.exists(ARCHIVO_CSV):
        print(f" ❌ ERROR: No se encuentra el archivo '{ARCHIVO_CSV}'.")
        print("   Por favor, verifica la ruta y el nombre del archivo.")
        sys.exit(1)

    print(f" 📄 Leyendo archivo: {ARCHIVO_CSV}")
    print(f" 🔍 Buscando productos por campo: '{CAMPO_PRODUCTO}'")

    inserts = []          # Lista de sentencias SQL generadas
    advertencias = []     # Lista de advertencias encontradas durante el proceso
    debug_rows = []       # Para depuración (no se usa en la salida final)

    # Apertura del archivo CSV
    with open(ARCHIVO_CSV, mode='r', encoding='utf-8-sig') as f:
        reader = csv.reader(f, delimiter=DELIMITADOR)
        cabecera = next(reader)  # Saltar la fila de cabecera

        # Procesar cada fila del CSV
        for num_fila, fila in enumerate(reader, start=2):  # start=2 para contar filas (1-based + cabecera)
            # Extraer valores de las columnas según índices definidos
            codigo = fila[IDX_REF].strip() if len(fila) > IDX_REF else ""
            cat = fila[IDX_CAT].strip() if len(fila) > IDX_CAT else ""
            subcat = fila[IDX_SUBCAT].strip() if len(fila) > IDX_SUBCAT else ""

            # Guardar fila para posible depuración
            debug_rows.append([codigo, cat, subcat])

            # Validar que el código del producto no esté vacío
            if not codigo:
                advertencias.append(f"Fila {num_fila}: Código vacío, se omite.")
                continue

            # --- Determinar el ID de categoría (fijo o mediante subconsulta) ---
            categoria_id = None
            usa_subconsulta = False
            clave_subconsulta = None   # Para identificar qué tipo de búsqueda dinámica usar

            if subcat:
                # Hay subcategoría especificada
                if not cat:
                    # Subcategoría sin padre explícito
                    if subcat in CAT_IDS:
                        # Si el nombre de la subcategoría está directamente en el diccionario
                        categoria_id = CAT_IDS[subcat]
                    else:
                        # Buscar si hay alguna clave (padre, hijo) donde el hijo coincida
                        posibles = [cid for (p, s), cid in CAT_IDS.items() if isinstance(p, str) and s == subcat]
                        if len(posibles) == 1:
                            categoria_id = posibles[0]
                        elif len(posibles) > 1:
                            advertencias.append(f"Fila {num_fila}: Subcategoría '{subcat}' ambigua. Se usará subconsulta.")
                            usa_subconsulta = True
                            clave_subconsulta = ('sub', subcat)
                        else:
                            usa_subconsulta = True
                            clave_subconsulta = ('sub', subcat)
                else:
                    # Tenemos padre y subcategoría
                    clave = (cat, subcat)
                    if clave in CAT_IDS:
                        categoria_id = CAT_IDS[clave]
                    else:
                        usa_subconsulta = True
                        clave_subconsulta = ('sub_con_padre', cat, subcat)
            else:
                # No hay subcategoría, solo categoría
                if cat:
                    if cat in CAT_IDS:
                        categoria_id = CAT_IDS[cat]
                    else:
                        usa_subconsulta = True
                        clave_subconsulta = ('cat', cat)
                else:
                    # Sin categoría ni subcategoría: no se asigna ninguna
                    continue

            # --- Construir la condición WHERE para localizar el producto ---
            if CAMPO_PRODUCTO == "barcode":
                where_producto = f"p.barcode = '{escapar_string(codigo)}'"
            else:  # por defecto 'ref'
                where_producto = f"p.ref = '{escapar_string(codigo)}'"

            # --- Generar sentencia SQL según el tipo de asignación ---
            if categoria_id is not None:
                # Asignación con ID fijo (más eficiente)
                sql = f"""-- Producto {CAMPO_PRODUCTO}='{codigo}' -> categoría_id {categoria_id} (fijo)
INSERT IGNORE INTO llx_categorie_product (fk_categorie, fk_product)
SELECT {categoria_id}, p.rowid
FROM llx_product p
WHERE {where_producto} AND p.entity = {ENTITY};
"""
                inserts.append(sql)

            elif usa_subconsulta:
                # Asignación mediante búsqueda dinámica por nombre
                if clave_subconsulta[0] == 'sub_con_padre':
                    # Subcategoría con padre conocido
                    _, padre, hijo = clave_subconsulta
                    sql = f"""-- Producto {CAMPO_PRODUCTO}='{codigo}' -> subcategoría '{hijo}' hija de '{padre}' (búsqueda dinámica)
INSERT IGNORE INTO llx_categorie_product (fk_categorie, fk_product)
SELECT sub.rowid, p.rowid
FROM llx_categorie sub
INNER JOIN llx_categorie padre ON padre.rowid = sub.fk_parent
INNER JOIN llx_product p ON {where_producto}
WHERE padre.label = '{escapar_string(padre)}'
  AND sub.label = '{escapar_string(hijo)}'
  AND sub.entity = {ENTITY} AND sub.type = {TYPE}
  AND padre.entity = {ENTITY} AND padre.type = {TYPE};
"""
                elif clave_subconsulta[0] == 'sub':
                    # Solo nombre de subcategoría (puede ser ambigua)
                    _, hijo = clave_subconsulta
                    sql = f"""-- Producto {CAMPO_PRODUCTO}='{codigo}' -> subcategoría '{hijo}' (búsqueda dinámica, puede ser ambigua)
INSERT IGNORE INTO llx_categorie_product (fk_categorie, fk_product)
SELECT c.rowid, p.rowid
FROM llx_categorie c, llx_product p
WHERE {where_producto}
  AND c.label = '{escapar_string(hijo)}'
  AND c.entity = {ENTITY} AND c.type = {TYPE};
"""
                elif clave_subconsulta[0] == 'cat':
                    # Solo nombre de categoría
                    _, nombre_cat = clave_subconsulta
                    sql = f"""-- Producto {CAMPO_PRODUCTO}='{codigo}' -> categoría '{nombre_cat}' (búsqueda dinámica)
INSERT IGNORE INTO llx_categorie_product (fk_categorie, fk_product)
SELECT c.rowid, p.rowid
FROM llx_categorie c, llx_product p
WHERE {where_producto}
  AND c.label = '{escapar_string(nombre_cat)}'
  AND c.entity = {ENTITY} AND c.type = {TYPE};
"""
                inserts.append(sql)

    # --- Escritura del archivo SQL de salida ---
    try:
        with open(ARCHIVO_SQL, 'w', encoding='utf-8') as f:
            # Cabecera del archivo SQL
            f.write("-- =========================================================\n")
            f.write("-- INSERCIÓN DE RELACIONES PRODUCTO-CATEGORÍA\n")
            f.write(f"-- Buscando productos por campo: '{CAMPO_PRODUCTO}'\n")
            f.write("-- =========================================================\n")
            f.write("START TRANSACTION;\n\n")

            # Escribir todas las sentencias generadas
            for sql in inserts:
                f.write(sql)
                f.write("\n")

            # Si hay advertencias, incluirlas como comentarios al final
            if advertencias:
                f.write("--\n-- ADVERTENCIAS DURANTE EL PROCESADO:\n--\n")
                for warn in advertencias:
                    f.write(f"-- {warn}\n")

            f.write("\nCOMMIT;\n")

        print(f"\n ✅ Archivo SQL generado exitosamente:")
        print(f"    {ARCHIVO_SQL}")
        print(f" 📊 Sentencias SQL generadas: {len(inserts)}")
        if advertencias:
            print(f" ⚠️  {len(advertencias)} advertencias. Revísalas en el archivo SQL.")

    except Exception as e:
        print(f" ❌ Error al escribir el archivo SQL: {e}")
        sys.exit(1)

    print("=" * 70)
    print(" ✨ Proceso completado. Revisa el archivo SQL y ejecútalo en phpMyAdmin.")
    print("=" * 70)


if __name__ == "__main__":
    generar_sql()