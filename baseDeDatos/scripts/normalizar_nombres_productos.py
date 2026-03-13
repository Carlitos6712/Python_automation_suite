#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script: normalizar_nombres_productos.py
Propósito: Genera un archivo SQL con sentencias UPDATE para normalizar los nombres
           de productos en Dolibarr y añadir un prefijo de lote basado en el orden
           de las filas del CSV.

Entrada: Archivo CSV con al menos dos columnas:
         - Columna ID (por ejemplo 'Ref'): identificador único del producto.
         - Columna nombre (por ejemplo 'Label'): nombre original a normalizar.

Proceso:
         - Lee el CSV.
         - Normaliza cada nombre: primera letra mayúscula, resto minúsculas.
         - Asigna un número de lote según el orden de fila (tamaño de lote configurable).
         - El nombre final será "lote-nombre_normalizado".
         - Genera una única sentencia UPDATE con CASE para actualizar todos los productos.

Salida: Archivo SQL en la ruta especificada (por defecto 'data/output/update_productos.sql').

Uso:
    1. Colocar el archivo CSV en la ruta correcta.
    2. Ajustar los parámetros de la función en el bloque `if __name__ == '__main__'`.
    3. Ejecutar el script.
    4. Revisar el archivo SQL generado y ejecutarlo en phpMyAdmin.
"""

import csv
import os

# =============================================================================
# FUNCIONES AUXILIARES
# =============================================================================

def normalizar_nombre(nombre):
    """
    Normaliza un nombre:
        - Convierte a string.
        - Elimina espacios al inicio y final.
        - Primera letra mayúscula, resto minúsculas.
    """
    if not isinstance(nombre, str):
        nombre = str(nombre)
    return nombre.strip().capitalize()

def generar_sql_desde_csv(archivo_csv, columna_nombre, columna_id,
                         nombre_tabla='llx_product', lote_tamano=50,
                         archivo_salida='update_productos.sql'):
    """
    Genera un archivo SQL con UPDATE para normalizar nombres y añadir prefijo de lote.
    
    Parámetros:
        archivo_csv (str): Ruta al archivo CSV de entrada.
        columna_nombre (str): Nombre de la columna que contiene el nombre original.
        columna_id (str): Nombre de la columna que contiene el identificador (ref).
        nombre_tabla (str): Nombre de la tabla en la base de datos.
        lote_tamano (int): Número de productos por lote.
        archivo_salida (str): Ruta donde se guardará el archivo SQL generado.
    
    Comportamiento:
        - Los lotes se asignan según el orden de las filas en el CSV (empezando en 1).
        - Todos los valores de ID se tratan como cadenas (con comillas en SQL).
        - Se genera una única sentencia UPDATE con CASE.
    """
    # Verificar existencia del archivo CSV
    if not os.path.exists(archivo_csv):
        print(f" ❌ ERROR: No se encuentra el archivo '{archivo_csv}'.")
        return

    # Leer CSV
    try:
        with open(archivo_csv, mode='r', encoding='utf-8') as f:
            lector = csv.DictReader(f)
            if columna_nombre not in lector.fieldnames:
                print(f" ❌ Error: No se encuentra la columna '{columna_nombre}' en el CSV.")
                print(f"    Columnas disponibles: {lector.fieldnames}")
                return
            if columna_id not in lector.fieldnames:
                print(f" ❌ Error: No se encuentra la columna ID '{columna_id}' en el CSV.")
                print(f"    Columnas disponibles: {lector.fieldnames}")
                return
            
            filas = list(lector)
    except Exception as e:
        print(f" ❌ Error al leer el CSV: {e}")
        return

    productos = []
    no_numericos = 0
    print(f"\n 📄 Procesando {len(filas)} filas...")

    for i, fila in enumerate(filas, start=1):  # i = número de fila (1-based)
        id_valor = fila[columna_id].strip()
        if not id_valor:
            print(f" ⚠️  Advertencia: ref vacío en fila {i}, se omite.")
            continue
        
        # Verificar si es numérico (solo para información)
        if not id_valor.isdigit():
            no_numericos += 1
        
        nombre_original = fila[columna_nombre]
        nombre_normalizado = normalizar_nombre(nombre_original)
        
        # Calcular número de lote
        lote = ((i - 1) // lote_tamano) + 1
        nombre_final = f"{lote}-{nombre_normalizado}"
        
        productos.append((id_valor, nombre_final))
    
    if not productos:
        print(" ⚠️  No hay datos válidos para procesar.")
        return
    
    # Escapar comillas simples en los valores (para SQL)
    def escapar(s):
        return s.replace("'", "''")
    
    casos = []
    ids_list = []
    for id_val, nombre in productos:
        id_escapado = escapar(id_val)
        nombre_escapado = escapar(nombre)
        # Ponemos el ID entre comillas simples (tratado como cadena)
        casos.append(f"WHEN '{id_escapado}' THEN '{nombre_escapado}'")
        ids_list.append(f"'{id_escapado}'")
    
    caso_str = "\n        ".join(casos)
    ids_str = ", ".join(ids_list)
    
    # Comentario de advertencia en el archivo SQL
    comentario = f"""-- =========================================================
-- ARCHIVO GENERADO AUTOMÁTICAMENTE
-- =========================================================
-- Total registros: {len(productos)}
-- Valores no numéricos en ref: {no_numericos}
-- 
-- ATENCIÓN: 
--   * Si la columna 'ref' en la base de datos es numérica,
--     los valores no numéricos se compararán como 0, lo que
--     puede dar resultados inesperados. Verifica que todos los
--     ref sean numéricos o que la columna sea VARCHAR.
--   * Asegúrate de que la columna a actualizar se llama 'label'
--     en la tabla. Si no es así, cambia 'SET label = ...' por
--     el nombre correcto.
-- =========================================================

"""
    sql = f"""{comentario}UPDATE {nombre_tabla}
SET label = CASE ref
        {caso_str}
    END
WHERE ref IN ({ids_str});
"""

    # Crear carpeta de salida si no existe
    try:
        os.makedirs(os.path.dirname(archivo_salida), exist_ok=True)
    except Exception as e:
        print(f" ❌ Error al crear la carpeta de salida: {e}")
        return

    # Escribir archivo SQL
    try:
        with open(archivo_salida, 'w', encoding='utf-8') as f:
            f.write(sql)
    except Exception as e:
        print(f" ❌ Error al escribir el archivo SQL: {e}")
        return

    # Resumen en consola
    print("\n" + "=" * 60)
    print(" ✅ PROCESO COMPLETADO")
    print("=" * 60)
    print(f" 📁 Archivo SQL generado: {archivo_salida}")
    print(f" 📦 Total productos a actualizar: {len(productos)}")
    if no_numericos > 0:
        print(f" ⚠️  Se encontraron {no_numericos} valores de ref NO NUMÉRICOS.")
        print("    Revisa el archivo SQL generado y verifica que la columna 'ref' en la BD")
        print("    sea de tipo texto, o corrige esos valores en el CSV.")
    print("=" * 60)

# =============================================================================
# PUNTO DE ENTRADA PRINCIPAL
# =============================================================================
def main():
    """Configura los parámetros y ejecuta la generación del SQL."""
    print("=" * 60)
    print(" 🏷️  GENERADOR SQL: NORMALIZACIÓN DE NOMBRES DE PRODUCTOS")
    print("=" * 60)

    # ===== CONFIGURACIÓN (modificar según necesidades) =====
    generar_sql_desde_csv(
        archivo_csv='data/output/archivo.csv',
        columna_nombre='Label',            # columna con el nombre original
        columna_id='Ref',                   # columna con la referencia (puede ser texto o número)
        nombre_tabla='llx_product',         # tabla de productos en Dolibarr
        lote_tamano=50,                      # productos por lote
        archivo_salida='data/output/update_productos.sql'
    )

if __name__ == '__main__':
    main()