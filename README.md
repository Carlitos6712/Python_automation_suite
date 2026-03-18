# SCRAPEO_DOLIBARR

Conjunto de utilidades Python para la gestión masiva de productos y categorías en **Dolibarr**.  
Los scripts se organizan en dos grandes áreas:

- **`baseDeDatos/scripts`** → Generan archivos SQL para actualizar/insertar datos directamente en la base de datos.
- **`csv/scripts`** → Procesan y transforman archivos CSV (limpieza, cruce de datos, división, normalización, etc.).
- **`img/`** → Contiene `scrapeo_imagenes.py` para la descarga/gestión de imágenes de productos.

Todos los scripts están diseñados para leer archivos de `data/input/` y escribir resultados en `data/output/` dentro de su respectiva rama.

---

## 📁 Estructura de Carpetas

```
SCRAPEO_DOLIBARR/
│
├── baseDeDatos/
│   ├── scripts/               # Scripts que generan SQL
│   ├── sql/                   # (opcional) Archivos SQL generados
│   ├── config/                # (opcional) Configuraciones adicionales
│   └── data/
│       ├── input/             # Coloca aquí los CSV/Excel para los scripts de BD
│       └── output/            # Aquí se guardan los SQL generados
│
├── csv/
│   ├── scripts/               # Scripts de manipulación de CSV
│   └── data/
│       ├── input/             # Archivos CSV de entrada para estos scripts
│       └── output/            # CSV resultantes
│
├── img/
│   └── scrapeo_imagenes.py    # Script para descargar imágenes
│
├── mod/                       # Módulos / extensiones de Dolibarr
│   └── module_ecommerceceng-14.0.39/
│
├── backup/                    # (opcional) Copias de seguridad
│
└── requeriments.txt           # Dependencias Python (pandas, openpyxl, etc.)
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

| Script | Propósito | Entrada (`data/input/`) | Configuración clave |
|--------|-----------|--------------------------|----------------------|
| `asignar_categoria_tpv_a_todos.py` | Crea la categoría `Tpv` y la asigna a todos los productos. | Ninguna | `CATEGORIA_NOMBRE`, `ENTITY` |
| `generador_sql_actualizar_descripciones.py` | Actualiza descripción larga y corta desde CSV. | `inventario_descripciones.csv` | `COL_CODIGO`, `COL_DESC_CORTA`, `COL_DESC_LARGA` |
| `generador_sql_actualizar_precios_iva.py` | Actualiza precio con IVA, calculando el sin IVA según última tasa. | `inventario_iva.csv` | `COL_CODIGO`, `COL_PRECIO_IVA`, `IVA_DEFECTO` |
| `generador_sql_actualizar_precios.py` | Actualiza precios de costo y venta desde Excel. | `productos_original.xlsx` | `COL_CODIGO`, `COL_PRECIO_COSTO`, `COL_PRECIO_VENTA` |
| `generador_sql_categoria_marcas.py` | Crea categoría `Marcas` con subcategorías y asocia productos. Genera INSERT IGNORE. | CSV con `Código` y `Marca` | `COL_CODIGO`, `COL_MARCA`, `CATEGORIA_MARCAS` |
| `generador_sql_insert_productos_categorias.py` | Inserta productos completos y los relaciona con categorías. | `inventario_categorizado.csv` | `COL_CATEGORIA`, `COL_SUBCATEGORIA` |
| `generador_sql_producto_categoria.py` | Inserta relaciones producto-categoría con búsqueda flexible (INSERT IGNORE). | CSV con `Código` y `Categoria` | `CAMPO_PRODUCTO_BD`, `COLUMNA_CATEGORIA`, `COLUMNA_SUBCATEGORIA` |
| `generador_sql_relaciones_producto_categoria.py` | **Corrige** relaciones producto-categoría erróneas. DELETE del subárbol de `tpv` + INSERT IGNORE de la correcta. Evita error #1062 en PK compuesta. | CSV con `Ref` y `Categoria` | `CAMPO_PRODUCTO_BD`, `CATEGORIA_RAIZ` |
| `generador_sql_relaciones_producto_marca.py` | **Corrige** relaciones producto-marca erróneas. DELETE del subárbol de `Marcas` + INSERT IGNORE de la correcta. Evita error #1062 en PK compuesta. | CSV con `Código` y `Marca` | `CAMPO_PRODUCTO_BD`, `CATEGORIA_MARCAS` |
| `generador_sql_update_categorias.py` | Actualiza categorías principales hijas de `tpv`. UPDATE si existen / INSERT IGNORE si son nuevas. DELETE de todas las relaciones del producto excepto ramas protegidas + INSERT IGNORE de la correcta. | CSV con `Ref` y `Categoria` | `CATEGORIA_RAIZ`, `CATEGORIAS_EXISTENTES`, `CATEGORIAS_PROTEGIDAS` |
| `generador_sql_update_extrafields_marca.py` | Sincroniza el campo `marca` en `llx_product_extrafields`. UPDATE si difiere (o es NULL) + INSERT IGNORE si no existe fila. | CSV con `Código` y `Marca` | `COL_EXTRAFIELD_MARCA` |
| `generador_sql_update_marcas.py` | Actualiza categorías de marca en `llx_categorie`. UPDATE para existentes / INSERT IGNORE para nuevas. Asocia productos con INSERT IGNORE. | CSV con `Ref` y `Marca` | `CATEGORIA_MARCAS`, `MARCAS_EXISTENTES` |
| `generador_sql_update_ref_barcode.py` | Actualiza `ref` y `barcode` desde CSV. | `productos_cod_ref.csv` | `COL_CODIGO`, `COL_REF_ANTIGUA` |
| `generador_sql_update_relaciones_producto_marca.py` | Corrige relaciones producto-marca con patrón DELETE + INSERT IGNORE. Previene #1062 y #1242. | CSV con `Código` y `Marca` | `CAMPO_PRODUCTO_BD`, `CATEGORIA_MARCAS` |
| `generar_sql_marcas_desde_extrafields.py` | Crea categorías de marca desde exportación de extrafields. | CSV con `fk_object` y `marca` | Argumentos CLI (`--csv`, `--output`) |
| `normalizar_nombres_productos.py` | Normaliza nombres y añade prefijo de lote (genera SQL). | CSV con `Ref` y `Label` | `columna_nombre`, `lote_tamano` |

---

## 📜 Scripts de `csv/scripts`

Estos scripts trabajan directamente sobre archivos CSV, sin generar SQL. Son útiles para preparar los datos antes de la importación.

| Script | Propósito | Entrada (`csv/data/input/`) | Salida (`csv/data/output/`) | Configuración |
|--------|-----------|------------------------------|------------------------------|----------------|
| `convertir_separador_csv.py` | Convierte el separador del CSV (ej: de `;` a `,`). Gestiona correctamente campos con comas internas envolviéndolos en comillas. | Cualquier CSV | CSV con nuevo separador | `SEP_ENTRADA`, `SEP_SALIDA`, `ENCODING_ENTRADA` |
| `cruzar_iva_por_nombre_producto.py` | Asigna IVA por similitud de nombre desde un archivo de referencia. | `tus_productos_nuevos.csv` y `productos_originales_con_iva.csv` | `productos_con_iva_nombre_*.csv` | `UMBRAL_SIMILITUD`, `IVA_DEFECTO` |
| `dividir_csv.py` | Divide un CSV grande en varias partes manteniendo la cabecera en cada parte. | Cualquier CSV | Archivos con prefijo configurable | Argumentos CLI (`--input`, `--num-partes`) |
| `filtrar_productos_por_categorias.py` | Filtra productos que pertenecen a categorías deseadas y añade columnas extra. | `export_producto_finalisimo.csv` y `export_categorie_product_finalisimo.csv` | `productos_filtrados_final.csv` | `CATEGORIAS_DESEADAS`, nombres de columna |
| `normalizar_nombres_productos_con_lote.py` | Normaliza nombres (capitalize) y añade prefijo de lote. Separador configurable para entrada y salida. | CSV con columna `Label` | `productos_normalizados.csv` | `SEPARADOR`, `COLUMNA_NOMBRE`, `LOTE_TAMANO` |
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
- **Separadores:** Los scripts de `baseDeDatos` usan `;` por defecto. Los de `csv` tienen el separador configurable mediante `SEP_ENTRADA` / `SEP_SALIDA`. Verifica cada script.
- **Personalización:** Todos los scripts tienen una sección `CONFIGURACIÓN` al inicio con constantes que puedes modificar (rutas, nombres de columna, valores por defecto).
- **LIMIT 1 en subconsultas:** Los scripts SQL que resuelven rowids por nombre usan `LIMIT 1` en todas las subconsultas para prevenir el error MySQL `#1242` (subquery returns more than 1 row) ante categorías homónimas.
- **Patrón DELETE + INSERT IGNORE:** Los scripts que corrigen relaciones en `llx_categorie_product` usan este patrón en lugar de UPDATE para evitar el error `#1062` (entrada duplicada en PK compuesta).

---

## 🚀 Flujo de Trabajo Típico

1. **Preparar los datos**: Usa los scripts de `csv/scripts` para limpiar, normalizar y enriquecer tus CSV. Si el CSV viene de Excel español, usa `convertir_separador_csv.py` para pasar de `;` a `,` antes de importar.
2. **Generar SQL**: Una vez que los CSV están listos, usa los scripts de `baseDeDatos/scripts` para generar los archivos SQL.
3. **Ejecutar en Dolibarr**: Abre phpMyAdmin, selecciona la base de datos de Dolibarr y ejecuta el SQL generado (siempre con `START TRANSACTION` para poder revertir si algo falla).
4. **Descargar imágenes**: Si es necesario, usa `scrapeo_imagenes.py` para obtener las imágenes de los productos.

---

## ⚠️ Notas Importantes

- **Pruebas en un entorno seguro:** Siempre revisa los archivos SQL generados y, si es posible, pruébalos en una copia de la base de datos antes de ejecutarlos en producción.
- **IDs de categorías:** Los scripts de categorías usan los rowids `1133` (Tpv) y `40` (Marcas) como raíces. Verifica que coinciden con los de tu instalación ejecutando:
  ```sql
  SELECT rowid, label FROM llx_categorie WHERE label IN ('Tpv', 'Marcas') AND type = 0;
  ```
- **Campos de búsqueda:** Verifica si el script busca por `ref` o por `barcode` (variable `CAMPO_PRODUCTO_BD`). Ajústalo según tu caso.
- **Categorías protegidas:** Los scripts de corrección de categorías tienen un set `CATEGORIAS_PROTEGIDAS` que evita borrar ramas como `Marcas` al limpiar relaciones erróneas. Añade más ramas si es necesario.
- **Limpieza manual de categorías huérfanas:** Para eliminar relaciones con categorías que no pertenecen al subárbol de `Tpv` ni `Marcas`, usa directamente en phpMyAdmin:
  ```sql
  DELETE cp FROM llx_categorie_product cp
  JOIN llx_categorie cat ON cat.rowid = cp.fk_categorie
  WHERE cat.entity = 1 AND cat.type = 0
    AND cat.rowid NOT IN (
        SELECT c.rowid FROM llx_categorie c
        WHERE c.entity = 1 AND c.type = 0
          AND (
               c.rowid     IN (1133, 40)
            OR c.fk_parent IN (1133, 40)
            OR c.fk_parent IN (SELECT rowid FROM llx_categorie WHERE fk_parent IN (1133, 40))
          )
    );
  ```