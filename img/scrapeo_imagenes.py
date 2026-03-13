import os
import requests
from requests_oauthlib import OAuth1
import mimetypes
from pathlib import Path
import time
import logging
from datetime import datetime

# ===== CONFIGURACIÓN =====
WORDPRESS_URL = "https://elpajaroblanco.com"  # Sin barra al final
IMAGES_FOLDER = "/ruta/a/tus/imagenes"   # Carpeta con las fotos

# API keys de WooCommerce
CONSUMER_KEY = "ck_f5817c3505812ef8943c9eba44dacdc5e14122c0"
CONSUMER_SECRET = "cs_d42373040233f6a99385bb47c9a8a38555846143"

# Extensiones de imagen permitidas
ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}

# Configuración de lotes
BATCH_SIZE = 10           # Número de imágenes por lote
PAUSE_BETWEEN_IMAGES = 1  # Segundos de espera entre cada imagen
PAUSE_BETWEEN_BATCHES = 3 # Segundos de espera entre lotes
MAX_RETRIES = 3           # Reintentos por operación fallida
# =========================

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f"imagenes_upload_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Crear autenticación OAuth1
auth = OAuth1(CONSUMER_KEY, CONSUMER_SECRET)

def get_product_by_sku(sku):
    """Busca un producto por SKU con reintentos."""
    url = f"{WORDPRESS_URL}/wp-json/wc/v3/products"
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(url, params={'sku': sku}, auth=auth, timeout=30)
            if response.status_code == 200:
                products = response.json()
                return products[0] if products else None
            else:
                logger.error(f"Error al buscar SKU {sku} (intento {attempt+1}): {response.status_code}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(2 ** attempt)  # Espera exponencial
        except requests.exceptions.RequestException as e:
            logger.error(f"Excepción al buscar SKU {sku} (intento {attempt+1}): {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(2 ** attempt)
    return None

def upload_media(image_path):
    """Sube una imagen con reintentos."""
    filename = os.path.basename(image_path)
    mime_type = mimetypes.guess_type(image_path)[0] or 'image/jpeg'
    
    for attempt in range(MAX_RETRIES):
        try:
            with open(image_path, 'rb') as f:
                files = {'file': (filename, f, mime_type)}
                response = requests.post(
                    f"{WORDPRESS_URL}/wp-json/wp/v2/media",
                    files=files,
                    auth=auth,
                    timeout=60  # Mayor timeout para subidas
                )
            
            if response.status_code == 201:
                return response.json()['id']
            else:
                logger.error(f"Error subiendo {filename} (intento {attempt+1}): {response.status_code}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(2 ** attempt)
        except requests.exceptions.RequestException as e:
            logger.error(f"Excepción subiendo {filename} (intento {attempt+1}): {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(2 ** attempt)
    return None

def update_product_featured_image(product_id, media_id, sku):
    """Asigna imagen destacada con reintentos."""
    url = f"{WORDPRESS_URL}/wp-json/wc/v3/products/{product_id}"
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.put(url, json={'featured_media': media_id}, auth=auth, timeout=30)
            if response.status_code == 200:
                logger.info(f"SKU {sku}: Producto ID {product_id} actualizado con imagen ID {media_id}")
                return True
            else:
                logger.error(f"Error actualizando producto {product_id} (SKU {sku}) (intento {attempt+1}): {response.status_code}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(2 ** attempt)
        except requests.exceptions.RequestException as e:
            logger.error(f"Excepción actualizando producto {product_id} (SKU {sku}) (intento {attempt+1}): {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(2 ** attempt)
    return False

def main():
    # Verificar carpeta
    if not os.path.isdir(IMAGES_FOLDER):
        logger.error(f"La carpeta {IMAGES_FOLDER} no existe.")
        return

    # Obtener lista de archivos de imagen
    image_files = []
    for file in Path(IMAGES_FOLDER).iterdir():
        if file.is_file() and file.suffix.lower() in ALLOWED_EXTENSIONS:
            image_files.append(file)
    
    total = len(image_files)
    logger.info(f"Se encontraron {total} imágenes para procesar.")

    # Estadísticas
    processed = 0
    successful = 0
    failed = []

    # Procesar por lotes
    for i in range(0, total, BATCH_SIZE):
        batch = image_files[i:i+BATCH_SIZE]
        logger.info(f"Procesando lote {i//BATCH_SIZE + 1}/{(total-1)//BATCH_SIZE + 1} ({len(batch)} imágenes)")

        for file in batch:
            sku = file.stem  # Nombre sin extensión
            logger.info(f"Procesando SKU: {sku} -> {file.name}")

            # Buscar producto por SKU
            product = get_product_by_sku(sku)
            if not product:
                logger.error(f"SKU {sku}: Producto no encontrado")
                failed.append((sku, "Producto no encontrado"))
                time.sleep(PAUSE_BETWEEN_IMAGES)
                continue

            product_id = product['id']
            product_name = product.get('name', '')
            logger.info(f"SKU {sku}: Producto encontrado: ID {product_id} - {product_name}")

            # Subir imagen
            media_id = upload_media(str(file))
            if not media_id:
                logger.error(f"SKU {sku}: No se pudo subir la imagen")
                failed.append((sku, "Error al subir imagen"))
                time.sleep(PAUSE_BETWEEN_IMAGES)
                continue

            # Asignar imagen destacada
            success = update_product_featured_image(product_id, media_id, sku)
            if success:
                successful += 1
            else:
                failed.append((sku, "Error al asignar imagen destacada"))

            processed += 1
            logger.info(f"Progreso: {processed}/{total} imágenes procesadas")

            # Pausa entre imágenes
            time.sleep(PAUSE_BETWEEN_IMAGES)

        # Pausa entre lotes
        if i + BATCH_SIZE < total:
            logger.info(f"Pausa de {PAUSE_BETWEEN_BATCHES} segundos antes del siguiente lote...")
            time.sleep(PAUSE_BETWEEN_BATCHES)

    # Resumen final
    logger.info("=" * 50)
    logger.info(f"Procesamiento completado. Total: {total}, Exitosos: {successful}, Fallidos: {len(failed)}")
    if failed:
        logger.info("Lista de SKU fallidos:")
        for sku, reason in failed:
            logger.info(f"  - {sku}: {reason}")

if __name__ == "__main__":
    main()