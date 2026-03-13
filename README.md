# SCRAPEO_DOLIBARR

Conjunto de utilidades Python para la gestión masiva de productos y categorías en **Dolibarr**.  
Los scripts se organizan en dos grandes áreas:

- **`baseDeDatos/scripts`** → Generan archivos SQL para actualizar/insertar datos directamente en la base de datos.
- **`csv/scripts`** → Procesan y transforman archivos CSV (limpieza, cruce de datos, división, normalización, etc.).
- **`img/`** → Contiene `scrapeo_imagenes.py` para la descarga/gestión de imágenes de productos.

Todos los scripts están diseñados para leer archivos de `data/input/` y escribir resultados en `data/output/` dentro de su respectiva rama.

---

## 📁 Estructura de Carpetas (basada en tu proyecto)

```
SCRAPEO_DOLIBARR/
│
├── baseDeDatos/
│   ├── scripts/               # Scripts que generan SQL
│   ├── sql/                    # (opcional) Archivos SQL generados
│   ├── config/                  # (opcional) Configuraciones adicionales
│   └── data/
│       ├── input/               # Coloca aquí los CSV/Excel para los scripts de BD
│       └── output/               # Aquí se guardan los SQL generados
│
├── csv/
│   ├── scripts/                 # Scripts de manipulación de CSV
│   └── data/
│       ├── input/                # Archivos CSV de entrada para estos scripts
│       └── output/                # CSV resultantes (ej. productos_normalizados.csv)
│
├── img/
│   └── scrapeo_imagenes.py       # Script para descargar imágenes
│
├── mod/                          # Módulos / extensiones de Dolibarr
│   └── module_ecommerceceng-14.0.39/
│
├── backup/                       # (opcional) Copias de seguridad
│
└── requeriments.txt               # Dependencias Python (pandas, openpyxl, etc.)
```

> **Importante:** Los scripts asumen que las carpetas `data/input` y `data/output` existen. Si no, algunas crean automáticamente la carpeta de salida.

---

## ⚙️ Requisitos e Instalación

1. **Python 3.6+** instalado.
2. Instalar las dependencias:

```bash
pip install -r requeriments.txt
```

El archivo `requeriments.txt` debe contener al menos:

```
pandas
openpyxl
xlrd
```

---

## 📜 Scripts de `baseDeDatos/scripts`

Estos scripts generan archivos SQL que debes ejecutar en phpMyAdmin o herramienta similar.  
Todos incluyen `START TRANSACTION;` y `COMMIT;` para poder deshacer si es necesario.

| Script | Propósito | Entrada (en `data/input/`) | Configuración clave |
|--------|-----------|-----------------------------|----------------------|
| `asignar_categoria_tpv_a_todos.py` | Crea la categoría 'Tpv' y la asigna a todos los productos. | Ninguna | `CATEGORIA_NOMBRE`, `ENTITY` |
| `generador_sql_actualizar_descripciones.py` | Actualiza descripción larga y corta desde CSV. | `inventario_descripciones.csv` | `COL_CODIGO`, `COL_DESC_CORTA`, `COL_DESC_LARGA` |
| `generador_sql_actualizar_precios_iva.py` | Actualiza precio con IVA, calculando el sin IVA según última tasa. | `inventario_iva.csv` | `COL_CODIGO`, `COL_PRECIO_IVA`, `IVA_DEFECTO` |
| `generador_sql_actualizar_precios.py` | Actualiza precios de costo y venta desde Excel. | `productos_original.xlsx` | `COL_CODIGO`, `COL_PRECIO_COSTO`, `COL_PRECIO_VENTA` |
| `generador_sql_categoria_marcas.py` | Crea categoría "Marcas" y subcategorías, y asocia productos. | `inventario_marcass.csv` | `COL_CODIGO`, `COL_MARCA`, `CATEGORIA_MARCAS` |
| `generador_sql_insert_productos_categorias.py` | Inserta productos completos y los relaciona con categorías. | `inventario_categorizado.csv` | `COL_CATEGORIA`, `COL_SUBCATEGORIA` (minúsculas) |
| `generador_sql_produto_categoria.py` | *(pendiente de descripción exacta)* | – | – |
| `generador_sql_relaciones_produto_categoria.py` | Inserta relaciones producto-categoría con búsqueda flexible. | `productos_final.csv` | `CAMPO_PRODUCTO_BD`, `COLUMNA_CATEGORIA`, `COLUMNA_SUBCATEGORIA` |
| `generador_sql_update_ref_barcode.py` | Actualiza `ref` y `barcode` desde CSV. | `productos_cod_ref.csv` | `COL_CODIGO`, `COL_REF_ANTIGUA` |
| `generar_sql_marcas_desde_extrafields.py` | Crea categorías de marca desde exportación de extrafields. | CSV con `fk_object` y `marca` | Argumentos CLI (`--csv`, `--output`) |
| `normalizar_nombres_productos.py` | Normaliza nombres y añade prefijo de lote (genera SQL). | CSV con `Ref` y `Label` | `columna_nombre`, `lote_tamano` (en el código) |

---

## 📜 Scripts de `csv/scripts`

Estos scripts trabajan directamente sobre archivos CSV, sin generar SQL. Son útiles para preparar los datos antes de la importación.

| Script | Propósito | Entrada (en `csv/data/input/`) | Salida (en `csv/data/output/`) | Configuración |
|--------|-----------|----------------------------------|--------------------------------|----------------|
| `cruzar_iva_por_nombre_produto.py` | Asigna IVA por similitud de nombre desde un archivo de referencia. | `tus_productos_nuevos.csv` y `productos_originales_con_iva.csv` | `productos_con_iva_nombre_*.csv` | `UMBRAL_SIMILITUD`, `IVA_DEFECTO` |
| `dividir_csv.py` | Divide un CSV grande en varias partes (con cabecera). | Cualquier CSV | Archivos con prefijo configurable | Argumentos CLI (`--input`, `--num-partes`) |
| `filtrar_productos_por_categorias.py` | Filtra productos que pertenecen a categorías deseadas y añade columnas extra. | `export_producto_finalisimo.csv` y `export_categorie_product_finalisimo.csv` | `productos_filtrados_final.csv` | `CATEGORIAS_DESEADAS`, nombres de columna |
| `normalizar_nombres_productos_con_lote.py` | Normaliza nombres y añade prefijo de lote (versión simplificada). | CSV con columna `Label` | `productos_normalizados.csv` | En el `if __name__ == '__main__'` |
| `unir_categoria_a_csv.py` | Añade columna de categoría a un CSV base usando otro CSV como diccionario. | Dos CSVs | CSV con nueva columna | Argumentos CLI (`-a`, `-b`, `-o`) |

---

## 🖼️ Script de `img/`

### `scrapeo_imagenes.py`

**Propósito:** Descarga o gestiona las imágenes de los productos.  
**Funcionamiento esperado:** Lee un CSV con referencias y descarga las imágenes asociadas (por ejemplo, `ref.jpg`) desde una URL o carpeta local.  
**Configuración:** Revisa las variables al inicio del script (ruta de entrada, columna de referencia, carpeta de destino, etc.).

---

## 🔧 Configuración General

- **Codificación:** La mayoría de scripts usan `utf-8` para lectura y `utf-8-sig` para escritura (compatible con Excel).
- **Separadores:** Por defecto, los scripts de `baseDeDatos` suelen usar `;` (punto y coma) y los de `csv` pueden usar `,` (coma). Verifica cada script.
- **Personalización:** Todos los scripts tienen una sección `CONFIGURACIÓN` al inicio con constantes que puedes modificar (rutas, nombres de columna, valores por defecto).

---

## 🚀 Flujo de Trabajo Típico

1. **Preparar los datos**: Usa los scripts de `csv/scripts` para limpiar, normalizar y enriquecer tus CSV.
2. **Generar SQL**: Una vez que los CSV están listos, usa los scripts de `baseDeDatos/scripts` para generar los archivos SQL.
3. **Ejecutar en Dolibarr**: Abre phpMyAdmin, selecciona la base de datos de Dolibarr y ejecuta el SQL generado (siempre con `START TRANSACTION` para poder revertir si algo falla).
4. **Descargar imágenes**: Si es necesario, usa `scrapeo_imagenes.py` para obtener las imágenes de los productos.

---

## ⚠️ Notas Importantes

- **Pruebas en un entorno seguro:** Siempre revisa los archivos SQL generados y, si es posible, pruébalos en una copia de la base de datos antes de ejecutarlos en producción.
- **IDs de categorías:** Algunos scripts (como el de marcas) utilizan IDs fijos. Asegúrate de que coinciden con los de tu instalación de Dolibarr.
- **Campos de búsqueda:** Verifica si el script busca por `ref` o por `barcode` (variable `CAMPO_PRODUCTO_BD`). Ajústalo según tu caso.

---

