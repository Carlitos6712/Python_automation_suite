#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script: convertir_separador_csv.py
Autor:  Carlos Vico

Propósito:
    Convierte el separador de un archivo CSV de un carácter a otro.
    Gestiona correctamente los campos que contienen el nuevo separador
    dentro de su valor, envolviéndolos en comillas automáticamente.

    Caso de uso principal:
      CSV exportado con ';' (Excel español) que debe importarse con ','
      en herramientas como Dolibarr, WooCommerce, etc.

Entrada:
    Archivo CSV con el separador original configurado en SEP_ENTRADA.

Salida:
    Archivo CSV con el separador nuevo configurado en SEP_SALIDA.
    Los campos que contengan SEP_SALIDA en su valor quedan entre comillas.

Uso:
    1. Ajustar las constantes de configuración.
    2. Ejecutar: python convertir_separador_csv.py
"""

import csv
import os
from datetime import datetime

# =============================================================================
# CONFIGURACIÓN (modificar según necesidades)
# =============================================================================

ARCHIVO_ENTRADA = "data/input/pajaro_final_finalisimo_de_los_finales_finalizados.csv"  # Ruta al CSV de entrada
ARCHIVO_SALIDA  = (
    f"data/output/archivo_convertido_"
    f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
)

SEP_ENTRADA = ";"    # Separador actual del CSV
SEP_SALIDA  = ","    # Separador deseado en el CSV de salida

ENCODING_ENTRADA = "utf-8-sig"   # utf-8-sig elimina el BOM de Excel
ENCODING_SALIDA  = "utf-8"


# =============================================================================
# PROCESO
# =============================================================================

def convertir_separador(
    archivo_entrada: str,
    archivo_salida: str,
    sep_entrada: str,
    sep_salida: str,
    encoding_entrada: str,
    encoding_salida: str
) -> None:
    """
    Lee el CSV con sep_entrada y lo reescribe con sep_salida.

    Usa el módulo csv de Python para gestionar correctamente:
      - Campos que contienen el nuevo separador → se envuelven en comillas.
      - Campos que contienen saltos de línea    → se envuelven en comillas.
      - Comillas internas                        → se escapan duplicándolas.

    Args:
        archivo_entrada:  Ruta al CSV original.
        archivo_salida:   Ruta del CSV convertido.
        sep_entrada:      Separador actual del CSV.
        sep_salida:       Separador deseado en la salida.
        encoding_entrada: Codificación del archivo de entrada.
        encoding_salida:  Codificación del archivo de salida.
    """
    if not os.path.exists(archivo_entrada):
        print(f" ❌ Archivo no encontrado: '{archivo_entrada}'")
        return

    os.makedirs(os.path.dirname(archivo_salida) or '.', exist_ok=True)

    try:
        with open(archivo_entrada, mode='r', encoding=encoding_entrada, newline='') as f_in, \
             open(archivo_salida,  mode='w', encoding=encoding_salida,  newline='') as f_out:

            lector   = csv.reader(f_in,  delimiter=sep_entrada)
            escritor = csv.writer(f_out, delimiter=sep_salida, quoting=csv.QUOTE_MINIMAL)

            total_filas = 0
            for fila in lector:
                escritor.writerow(fila)
                total_filas += 1

        print(f" ✅ Conversión completada.")
        print(f"    Filas procesadas : {total_filas} (incluye cabecera)")
        print(f"    Separador entrada: '{sep_entrada}'")
        print(f"    Separador salida : '{sep_salida}'")
        print(f"    Archivo generado : {archivo_salida}")

    except Exception as exc:
        print(f" ❌ Error durante la conversión: {exc}")


# =============================================================================
# FUNCIÓN PRINCIPAL
# =============================================================================

def main() -> None:
    """Configura los parámetros y ejecuta la conversión del separador."""
    print("=" * 70)
    print(" 🔣  CONVERSOR DE SEPARADOR CSV")
    print("=" * 70)
    print(f" 📄 Entrada : {ARCHIVO_ENTRADA}  (separador: '{SEP_ENTRADA}')")
    print(f" 📁 Salida  : {ARCHIVO_SALIDA}  (separador: '{SEP_SALIDA}')")

    convertir_separador(
        archivo_entrada  = ARCHIVO_ENTRADA,
        archivo_salida   = ARCHIVO_SALIDA,
        sep_entrada      = SEP_ENTRADA,
        sep_salida       = SEP_SALIDA,
        encoding_entrada = ENCODING_ENTRADA,
        encoding_salida  = ENCODING_SALIDA
    )

    print("=" * 70)
    print(" ✨ Proceso completado.")
    print("=" * 70)


if __name__ == '__main__':
    main()