"""
Power BI Multi-Report Monitor
Система мониторинга 96+ Power BI отчетов с обнаружением визуальных изменений
"""

import os
import sys
import json
import time
import logging
import psycopg2
import signal
import gzip
import io
from datetime import datetime, timedelta
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from dotenv import load_dotenv
from pythonjsonlogger import jsonlogger

# Selenium
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service

# Image processing
from PIL import Image, ImageDraw, ImageChops
import imagehash
import numpy as np


# Global flag for graceful shutdown
shutdown_flag = False
db_lock = Lock()


def load_config():
    """Загрузить конфигурацию"""
    load_dotenv('config.env')
    
    return {
        # PostgreSQL
        'pg_host': os.getenv('PG_HOST', '10.3.0.100'),
        'pg_port': int(os.getenv('PG_PORT', '5432')),
        'pg_database': os.getenv('PG_DATABASE', 'db_new'),
        'pg_user': os.getenv('PG_USER', 'dwh_bi_user'),
        'pg_password': os.getenv('PG_PASSWORD', ''),
        'pg_schema': os.getenv('PG_SCHEMA', 'sandbox'),
        
        # Power BI Auth
        'pbi_username': os.getenv('POWERBI_USERNAME') or None,
        'pbi_password': os.getenv('POWERBI_PASSWORD') or None,
        
        # Monitoring (dynamic scaling)
        'min_worker_threads': int(os.getenv('MIN_WORKER_THREADS', '1')),
        'max_worker_threads': int(os.getenv('MAX_WORKER_THREADS', '5')),
        'page_load_wait': int(os.getenv('PAGE_LOAD_WAIT', '10')),
        'default_threshold': float(os.getenv('DEFAULT_THRESHOLD', '5.0')),
        'screenshot_width': int(os.getenv('SCREENSHOT_WIDTH', '1920')),
        'screenshot_height': int(os.getenv('SCREENSHOT_HEIGHT', '1080')),
        
        # Diff (Quadtree)
        'diff_enabled': os.getenv('DIFF_ENABLED', 'True').lower() == 'true',
        'mse_threshold': float(os.getenv('MSE_THRESHOLD', '100.0')),
        'min_block_size': int(os.getenv('MIN_BLOCK_SIZE', '32')),
        'max_depth': int(os.getenv('MAX_DEPTH', '5')),
        
        # Paths
        'screenshots_dir': os.getenv('SCREENSHOTS_DIR', './screenshots'),
        'logs_dir': os.getenv('LOGS_DIR', './logs'),
        'log_level': os.getenv('LOG_LEVEL', 'INFO')
    }


def setup_logging(config):
    """Настройка structured logging для Grafana Loki"""
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, config['log_level'].upper()))
    
    # Console handler с JSON форматированием
    handler = logging.StreamHandler(sys.stdout)
    formatter = jsonlogger.JsonFormatter(
        '%(timestamp)s %(level)s %(name)s %(message)s',
        rename_fields={'levelname': 'level'}
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    return logger


def load_reports(json_path):
    """Загрузить конфигурацию отчетов из JSON"""
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        reports = data.get('reports', [])
        enabled_reports = [r for r in reports if r.get('enabled', True)]
        
        return enabled_reports
    except Exception as e:
        logging.error(f"Ошибка при загрузке JSON: {e}")
        return []


class DatabaseManager:
    """Менеджер для работы с PostgreSQL"""
    
    def __init__(self, config):
        self.config = config
        self.conn = None
        self.connect()
    
    def connect(self):
        """Подключение к БД"""
        try:
            self.conn = psycopg2.connect(
                host=self.config['pg_host'],
                port=self.config['pg_port'],
                database=self.config['pg_database'],
                user=self.config['pg_user'],
                password=self.config['pg_password']
            )
            # Устанавливаем схему sandbox
            cur = self.conn.cursor()
            cur.execute(f"SET search_path TO {self.config['pg_schema']}")
            cur.close()
            self.conn.commit()
        except Exception as e:
            logging.error(f"Ошибка подключения к БД: {e}")
            raise
    
    def get_baseline(self, report_id):
        """Получить baseline для отчета
        
        Returns:
            str: hash_value или None
        """
        with db_lock:
            try:
                cur = self.conn.cursor()
                cur.execute("""
                    SELECT hash_value 
                    FROM baselines 
                    WHERE report_id = %s
                """, (report_id,))
                result = cur.fetchone()
                cur.close()
                return result[0] if result else None
            except Exception as e:
                logging.error(f"Ошибка при получении baseline: {e}")
                return None
    
    def save_baseline(self, report_id, report_name, hash_value):
        """Сохранить baseline метаданные (файлы в Data/)"""
        with db_lock:
            try:
                cur = self.conn.cursor()
                cur.execute("""
                    INSERT INTO baselines (report_id, report_name, hash_value)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (report_id) 
                    DO UPDATE SET 
                        hash_value = EXCLUDED.hash_value,
                        updated_at = CURRENT_TIMESTAMP
                """, (report_id, report_name, hash_value))
                self.conn.commit()
                cur.close()
            except Exception as e:
                logging.error(f"Ошибка при сохранении baseline: {e}")
                self.conn.rollback()
    
    def update_last_baseline(self, report_id, hash_value):
        """Обновить hash last_baseline (файл в Data/changes)"""
        with db_lock:
            try:
                cur = self.conn.cursor()
                cur.execute("""
                    UPDATE baselines 
                    SET hash_value = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE report_id = %s
                """, (hash_value, report_id))
                self.conn.commit()
                cur.close()
            except Exception as e:
                logging.error(f"Ошибка при обновлении last_baseline: {e}")
                self.conn.rollback()
    
    def save_check_result(self, result):
        """Сохранить результат проверки (лог, БЕЗ путей к файлам)"""
        with db_lock:
            try:
                cur = self.conn.cursor()
                cur.execute("""
                    INSERT INTO monitoring_checks (
                        report_id, report_name, report_url, check_time, status,
                        diff_percent, screenshot_hash, delta_compressed, error, duration_sec, next_check_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    result.get('report_id'),
                    result.get('report_name'),
                    result.get('report_url'),
                    result.get('check_time'),
                    result.get('status'),
                    result.get('diff_percent'),
                    result.get('screenshot_hash'),
                    result.get('delta_compressed'),
                    result.get('error'),
                    result.get('duration_sec'),
                    result.get('next_check_at')
                ))
                self.conn.commit()
                cur.close()
            except Exception as e:
                logging.error(f"Ошибка при сохранении результата: {e}")
                self.conn.rollback()
    
    def get_delta(self, check_id):
        """Получить delta по check_id
        
        Args:
            check_id: ID конкретной проверки
            
        Returns:
            bytes or None: Compressed delta (BYTEA)
        """
        with db_lock:
            try:
                cur = self.conn.cursor()
                cur.execute("""
                    SELECT delta_compressed 
                    FROM monitoring_checks 
                    WHERE id = %s
                """, (check_id,))
                result = cur.fetchone()
                cur.close()
                return result[0] if result else None
            except Exception as e:
                logging.error(f"Ошибка при получении delta: {e}")
                return None
    
    def restore_screenshot(self, report_id, check_id):
        """Восстановить screenshot по (report_id, check_id)
        
        Args:
            report_id: ID отчета
            check_id: ID конкретной проверки
            
        Returns:
            PIL.Image or None: Восстановленное изображение
        """
        try:
            # 1. Вычислить init_baseline_path из report_id (файл в Data/)
            init_baseline_path = f'Data/baselines/{report_id}_init_baseline.png'
            
            if not os.path.exists(init_baseline_path):
                logging.error(f"Initial baseline не существует: {init_baseline_path}")
                return None
            
            # 2. Получить delta из БД
            delta_compressed = self.get_delta(check_id)
            
            if not delta_compressed:
                # Нет delta - возвращаем initial
                return Image.open(init_baseline_path)
            
            # 3. Восстановить через XOR
            restored = DeltaEncoder.decode(init_baseline_path, delta_compressed)
            return restored
            
        except Exception as e:
            logging.error(f"Ошибка при восстановлении screenshot: {e}")
            return None
    
    def close(self):
        """Закрыть соединение"""
        if self.conn:
            self.conn.close()


class ReportMonitor:
    """Класс для мониторинга одного отчета"""
    
    def __init__(self, config, debug=False):
        self.config = config
        self.driver = None
        self.debug = debug
    
    def _init_driver(self):
        """Инициализация Selenium WebDriver"""
        if self.driver:
            return
        
        options = Options()
        
        # В debug режиме показываем браузер
        if not self.debug:
            options.add_argument('--headless=new')
        
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument(f'--window-size={self.config["screenshot_width"]},{self.config["screenshot_height"]}')
        options.add_argument('--disable-blink-features=AutomationControlled')
        
        # Для Windows/NTLM Auth - разрешаем автоматическую аутентификацию
        username = self.config.get('pbi_username')
        password = self.config.get('pbi_password')
        
        if username and password:
            # Chrome extension для автоматической NTLM аутентификации
            # Альтернатива: использовать requests-ntlm перед Selenium
            prefs = {
                "credentials_enable_service": True,
                "profile.password_manager_enabled": True
            }
            options.add_experimental_option("prefs", prefs)
            
            # Auth server list для автоматической NTLM
            options.add_argument('--auth-server-whitelist=dtln-sql-03')
            options.add_argument('--auth-negotiate-delegate-whitelist=dtln-sql-03')
        
        try:
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
        except Exception as e:
            logging.error(f"Ошибка инициализации WebDriver: {e}")
            raise
    
    def _build_auth_url(self, url):
        """Встроить креды в URL для Basic Auth"""
        from urllib.parse import urlparse, urlunparse, quote
        
        username = self.config.get('pbi_username')
        password = self.config.get('pbi_password')
        
        if not username or not password:
            return url
        
        parsed = urlparse(url)
        
        # URL-encode username и password
        username_encoded = quote(username, safe='')
        password_encoded = quote(password, safe='')
        
        # Встраиваем username:password в URL
        netloc = f"{username_encoded}:{password_encoded}@{parsed.hostname}"
        if parsed.port:
            netloc += f":{parsed.port}"
        
        auth_url = urlunparse((
            parsed.scheme,
            netloc,
            parsed.path,
            parsed.params,
            parsed.query,
            parsed.fragment
        ))
        
        return auth_url
    
    def take_screenshot(self, url, output_path):
        """Сделать скриншот отчета"""
        try:
            self._init_driver()
            
            # Встраиваем креды в URL для Basic Auth
            auth_url = self._build_auth_url(url)
            
            if self.debug:
                logging.info(f"DEBUG: Открываем URL с Basic Auth")
                logging.info(f"DEBUG: Оригинальный URL: {url}")
            
            self.driver.get(auth_url)
            
            # Ждем загрузки body
            WebDriverWait(self.driver, 30).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            if self.debug:
                logging.info(f"DEBUG: Текущий URL: {self.driver.current_url}")
                logging.info(f"DEBUG: Title: {self.driver.title}")
                
                # Выводим структуру страницы
                try:
                    body_text = self.driver.find_element(By.TAG_NAME, "body").text[:200]
                    logging.info(f"DEBUG: Текст body (первые 200 символов): {body_text}")
                    
                    # Ищем все iframe
                    iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
                    logging.info(f"DEBUG: Найдено iframe: {len(iframes)}")
                    for idx, iframe in enumerate(iframes[:3]):  # Первые 3
                        src = iframe.get_attribute('src') or 'no src'
                        logging.info(f"DEBUG:   iframe[{idx}]: {src[:100]}")
                except Exception as e:
                    logging.info(f"DEBUG: Ошибка при анализе страницы: {e}")
            
            # Ждем загрузки Power BI iframe
            try:
                # Power BI Report Server рендерит отчет в iframe
                iframe = WebDriverWait(self.driver, 20).until(
                    EC.presence_of_element_located((By.TAG_NAME, "iframe"))
                )
                
                if self.debug:
                    logging.info(f"DEBUG: Найден iframe: {iframe.get_attribute('src')[:100]}...")
                
                # ПЕРЕКЛЮЧАЕМСЯ В IFRAME с отчетом!
                self.driver.switch_to.frame(iframe)
                
                if self.debug:
                    logging.info("DEBUG: Переключились в iframe с отчетом")
                
            except Exception as e:
                if self.debug:
                    logging.warning(f"DEBUG: Не удалось найти/переключиться в iframe: {e}")
                    logging.info("DEBUG: Продолжаем без iframe")
            
            # Ждем исчезновения спиннеров загрузки
            try:
                # Power BI обычно использует элементы с классами loading, spinner и т.д.
                time.sleep(5)  # Даем время начать загрузку
                WebDriverWait(self.driver, 30).until_not(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".spinner, .loading, [class*='loading'], [class*='spinner']"))
                )
                if self.debug:
                    logging.info("DEBUG: Спиннеры загрузки исчезли")
            except:
                if self.debug:
                    logging.info("DEBUG: Спиннеры не найдены или уже исчезли")
            
            # Дополнительное ожидание для визуалов
            if self.debug:
                logging.info(f"DEBUG: Дополнительно ждем {self.config['page_load_wait']} сек")
            
            time.sleep(self.config['page_load_wait'])
            
            # Возвращаемся из iframe обратно к основному контенту для полного скриншота
            try:
                self.driver.switch_to.default_content()
                if self.debug:
                    logging.info("DEBUG: Вернулись в основной контент для скриншота")
            except:
                pass
            
            # Делаем скриншот
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            self.driver.save_screenshot(output_path)
            
            if self.debug:
                logging.info(f"DEBUG: Скриншот сохранен: {output_path}")
                file_size = os.path.getsize(output_path) / 1024
                logging.info(f"DEBUG: Размер файла: {file_size:.1f} KB")
            
            return True
        except Exception as e:
            logging.error(f"Ошибка при создании скриншота: {e}")
            return False
    
    def calculate_hash(self, image_path):
        """Вычислить perceptual hash"""
        try:
            img = Image.open(image_path)
            return str(imagehash.dhash(img))
        except Exception as e:
            logging.error(f"Ошибка вычисления hash: {e}")
            return None
    
    def _calculate_mse(self, block1, block2):
        """Вычислить Mean Squared Error между двумя блоками"""
        arr1 = np.array(block1, dtype=np.float32)
        arr2 = np.array(block2, dtype=np.float32)
        mse = np.mean((arr1 - arr2) ** 2)
        return mse
    
    def _quadtree_compare(self, baseline_img, current_img, x, y, width, height, threshold, min_size=32, depth=0, max_depth=5):
        """
        Рекурсивное сравнение через квадродерево с контролем глубины
        
        Args:
            depth: Текущая глубина рекурсии
            max_depth: Максимальная глубина (drill-down уровней)
        
        Returns:
            List of changed blocks: [(x, y, width, height, mse), ...]
        """
        # Вырезаем блоки
        baseline_block = baseline_img.crop((x, y, x + width, y + height))
        current_block = current_img.crop((x, y, x + width, y + height))
        
        # Вычисляем MSE для блока
        mse = self._calculate_mse(baseline_block, current_block)
        
        # Если блок не изменился - возвращаем пустой список
        if mse <= threshold:
            return []
        
        # Останавливаем рекурсию если:
        # 1. Достигли max_depth (для self-verification через drill-down)
        # 2. Блок стал меньше min_size
        if depth >= max_depth or width <= min_size or height <= min_size:
            return [(x, y, width, height, mse)]
        
        # Делим блок на 4 части (drill-down на следующий уровень)
        changed_blocks = []
        half_w = width // 2
        half_h = height // 2
        
        quadrants = [
            (x, y, half_w, half_h),
            (x + half_w, y, width - half_w, half_h),
            (x, y + half_h, half_w, height - half_h),
            (x + half_w, y + half_h, width - half_w, height - half_h)
        ]
        
        for qx, qy, qw, qh in quadrants:
            changed_blocks.extend(
                self._quadtree_compare(
                    baseline_img, current_img, 
                    qx, qy, qw, qh, 
                    threshold, min_size, 
                    depth + 1, max_depth
                )
            )
        
        return changed_blocks
    
    def compare_images(self, baseline_path, current_path, mse_threshold=100.0, min_block_size=32, max_depth=5):
        """
        Сравнить изображения через quadtree алгоритм
        
        Args:
            baseline_path: Путь к baseline
            current_path: Путь к current
            mse_threshold: Порог MSE для определения изменения блока
            min_block_size: Минимальный размер блока для деления
            
        Returns:
            Dict с результатами сравнения
        """
        try:
            baseline_img = Image.open(baseline_path).convert('RGB')
            current_img = Image.open(current_path).convert('RGB')
            
            # Выравниваем размеры
            if baseline_img.size != current_img.size:
                current_img = current_img.resize(baseline_img.size)
            
            width, height = baseline_img.size
            
            # Вычисляем hash для логирования
            baseline_hash = self.calculate_hash(baseline_path)
            current_hash = self.calculate_hash(current_path)
            
            # Quadtree сравнение с drill-down (depth=0 -> max_depth)
            changed_blocks = self._quadtree_compare(
                baseline_img, current_img, 
                0, 0, width, height, 
                mse_threshold, min_block_size,
                depth=0, max_depth=max_depth
            )
            
            # Вычисляем процент измененной площади
            total_area = width * height
            changed_area = sum(block[2] * block[3] for block in changed_blocks)
            diff_percent = (changed_area / total_area) * 100
            
            # Hamming distance для логов (но не используем для diff_percent)
            if baseline_hash and current_hash:
                baseline_hash_obj = imagehash.hex_to_hash(baseline_hash)
                current_hash_obj = imagehash.hex_to_hash(current_hash)
                hamming_distance = int(baseline_hash_obj - current_hash_obj)  # Конвертируем в Python int
            else:
                hamming_distance = 0
            
            return {
                'baseline_hash': baseline_hash,
                'current_hash': current_hash,
                'hamming_distance': hamming_distance,
                'diff_percent': round(diff_percent, 2),
                'changed_blocks': changed_blocks,
                'changed_blocks_count': len(changed_blocks)
            }
        except Exception as e:
            logging.error(f"Ошибка при сравнении: {e}")
            return None
    
    def create_diff_image(self, baseline_path, current_path, diff_path, changed_blocks):
        """
        Создать diff изображение с визуализацией измененных блоков
        
        Args:
            baseline_path: Путь к baseline
            current_path: Путь к current
            diff_path: Путь для сохранения diff
            changed_blocks: Список измененных блоков [(x, y, w, h, mse), ...]
        """
        try:
            if not self.config['diff_enabled']:
                return None
            
            # Загружаем current как основу
            current_img = Image.open(current_path).convert('RGB')
            draw = ImageDraw.Draw(current_img)
            
            # Рисуем прямоугольники вокруг измененных блоков
            for x, y, width, height, mse in changed_blocks:
                # Красный прямоугольник вокруг измененного блока
                draw.rectangle(
                    [x, y, x + width, y + height],
                    outline=(255, 0, 0),  # Красная обводка
                    width=3
                )
                
                # Полупрозрачная красная заливка (опционально)
                # Можно добавить если нужно
            
            current_img.save(diff_path)
            return diff_path
            
        except Exception as e:
            logging.error(f"Ошибка при создании diff: {e}")
            return None
    
    def close(self):
        """Закрыть WebDriver"""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
            self.driver = None


class DeltaEncoder:
    """XOR Delta encoding через векторную математику (NumPy)"""
    
    @staticmethod
    def encode(initial_path, current_path):
        """Создать compressed delta: initial XOR current
        
        Args:
            initial_path: Путь к initial_baseline
            current_path: Путь к current screenshot
            
        Returns:
            bytes: gzip compressed delta для BYTEA в PostgreSQL
        """
        try:
            initial = np.array(Image.open(initial_path))
            current = np.array(Image.open(current_path))
            
            # Векторизованная XOR операция
            delta = np.bitwise_xor(initial, current)
            
            # Сериализация + gzip compression
            buffer = io.BytesIO()
            np.save(buffer, delta)
            compressed = gzip.compress(buffer.getvalue(), compresslevel=6)
            
            return compressed
            
        except Exception as e:
            logging.error(f"Ошибка при encode delta: {e}")
            return None
    
    @staticmethod
    def decode(initial_path, compressed_delta):
        """Восстановить screenshot: initial XOR delta
        
        Args:
            initial_path: Путь к initial_baseline
            compressed_delta: bytes из БД (BYTEA)
            
        Returns:
            PIL.Image: Восстановленное изображение
        """
        try:
            initial = np.array(Image.open(initial_path))
            
            # Распаковка gzip
            decompressed = gzip.decompress(compressed_delta)
            buffer = io.BytesIO(decompressed)
            delta = np.load(buffer)
            
            # Обратная XOR операция
            restored = np.bitwise_xor(initial, delta)
            
            return Image.fromarray(restored.astype(np.uint8))
            
        except Exception as e:
            logging.error(f"Ошибка при decode delta: {e}")
            return None


def check_report(report, config, db_manager, debug=False):
    """Проверить один отчет"""
    start_time = time.time()
    report_id = report['id']
    report_name = report['name']
    report_url = report['url']
    threshold = report.get('threshold', config['default_threshold'])
    
    result = {
        'report_id': report_id,
        'report_name': report_name,
        'report_url': report_url,
        'check_time': datetime.now(),
        'status': 'unknown',
        'duration_sec': 0,
        'next_check_at': datetime.now() + timedelta(minutes=report['interval'])
    }
    
    monitor = ReportMonitor(config, debug=debug)
    
    try:
        # Пути к файлам (БЕЗ timestamp)
        data_dir = Path(config['screenshots_dir'])
        baseline_dir = data_dir / 'baselines'
        changes_dir = data_dir / 'changes' / report_id
        
        init_baseline_path = str(baseline_dir / f'{report_id}_init_baseline.png')
        last_baseline_path = str(changes_dir / 'last_baseline.png')
        current_path = str(changes_dir / 'current_screenshot.png')
        diff_path = str(changes_dir / 'current_screenshot_diff.png')
        
        # Создаем директории
        baseline_dir.mkdir(parents=True, exist_ok=True)
        changes_dir.mkdir(parents=True, exist_ok=True)
        
        # Проверяем наличие baseline
        baseline_exists = False
        if db_manager:
            baseline_record = db_manager.get_baseline(report_id)
            baseline_exists = baseline_record and os.path.exists(init_baseline_path) and os.path.exists(last_baseline_path)
        else:
            baseline_exists = os.path.exists(init_baseline_path) and os.path.exists(last_baseline_path)
        
        if not baseline_exists:
            # Создаем initial baseline (первый эталон)
            logging.info(f"Создание baseline для {report_name}")
            if monitor.take_screenshot(report_url, init_baseline_path):
                # Копируем initial в last_baseline
                import shutil
                shutil.copy2(init_baseline_path, last_baseline_path)
                
                hash_value = monitor.calculate_hash(last_baseline_path)
                screenshot_hash = hash_value
                
                if db_manager:
                    db_manager.save_baseline(report_id, report_name, hash_value)
                
                result['status'] = 'baseline_created'
                result['baseline_hash'] = hash_value
                result['screenshot_hash'] = screenshot_hash
            else:
                result['status'] = 'error'
                result['error'] = 'Не удалось создать baseline'
        else:
            # Унифицированный pipeline для ЛЮБОГО чека
            # 1-2. Логин + создать current_screenshot.png
            if monitor.take_screenshot(report_url, current_path):
                current_hash = monitor.calculate_hash(current_path)
                result['screenshot_hash'] = current_hash
                
                # 3-4. Взять last_baseline + сравнить
                comparison = monitor.compare_images(
                    last_baseline_path, current_path,
                    mse_threshold=config['mse_threshold'],
                    min_block_size=config['min_block_size'],
                    max_depth=config['max_depth']
                )
                
                if comparison:
                    result.update(comparison)
                    diff_percent = comparison['diff_percent']
                    
                    # 5. Статус (для анализа, не влияет на pipeline)
                    result['status'] = 'changed' if diff_percent > 0 else 'unchanged'
                    
                    # 6. Создать XOR delta (ВСЕГДА)
                    try:
                        delta_compressed = DeltaEncoder.encode(init_baseline_path, current_path)
                        result['delta_compressed'] = delta_compressed
                        
                        if delta_compressed:
                            delta_size_kb = len(delta_compressed) / 1024
                            logging.debug(f"Delta created: {delta_size_kb:.1f} KB")
                    except Exception as e:
                        logging.warning(f"Не удалось создать delta: {e}")
                        result['delta_compressed'] = None
                    
                    # 7. Создать diff визуализацию (ВСЕГДА)
                    diff_img = monitor.create_diff_image(
                        last_baseline_path, current_path, diff_path,
                        comparison['changed_blocks']
                    )
                    
                    # 8. Удалить old last_baseline.png
                    if os.path.exists(last_baseline_path):
                        os.remove(last_baseline_path)
                    
                    # 9. Переименовать current → last_baseline
                    os.rename(current_path, last_baseline_path)
                    
                    # Обновить в БД
                    if db_manager:
                        db_manager.update_last_baseline(report_id, current_hash)
                    
                else:
                    result['status'] = 'error'
                    result['error'] = 'Ошибка при сравнении'
            else:
                result['status'] = 'error'
                result['error'] = 'Не удалось создать скриншот'
        
    except Exception as e:
        result['status'] = 'error'
        result['error'] = str(e)
        logging.error(f"Ошибка при проверке {report_name}: {e}", exc_info=True)
    
    finally:
        monitor.close()
        result['duration_sec'] = round(time.time() - start_time, 2)
    
    # Сохраняем результат в БД (если доступен)
    if db_manager:
        db_manager.save_check_result(result)
    
    # Логируем в JSON
    log_data = {
        'report_id': report_id,
        'report_name': report_name,
        'status': result['status'],
        'diff_percent': result.get('diff_percent'),
        'duration_sec': result['duration_sec']
    }
    
    if result['status'] == 'changed':
        logging.warning('Visual changes detected', extra=log_data)
    elif result['status'] == 'unchanged':
        logging.info('No changes detected', extra=log_data)
    elif result['status'] == 'baseline_created':
        logging.info('Baseline created', extra=log_data)
    else:
        logging.error('Check failed', extra={**log_data, 'error': result.get('error')})
    
    return result


def calculate_next_run(report, current_time):
    """Вычислить время следующего запуска"""
    start_time_str = report.get('start_time', '09:00')
    interval = report['interval']
    
    # Парсим start_time
    start_hour, start_minute = map(int, start_time_str.split(':'))
    
    # Первый запуск сегодня
    today = current_time.date()
    first_run_today = datetime.combine(today, datetime.min.time()).replace(
        hour=start_hour, minute=start_minute
    )
    
    if current_time < first_run_today:
        return first_run_today
    
    # Вычисляем сколько интервалов прошло с первого запуска
    elapsed = (current_time - first_run_today).total_seconds() / 60
    intervals_passed = int(elapsed / interval)
    
    # Следующий запуск
    next_run = first_run_today + timedelta(minutes=(intervals_passed + 1) * interval)
    
    return next_run


def signal_handler(signum, frame):
    """Обработчик сигналов для graceful shutdown"""
    global shutdown_flag
    logging.info(f"Получен сигнал {signum}, останавливаем мониторинг...")
    shutdown_flag = True


def build_mode(reports_json, config, debug=False):
    """BUILD - Инициализация БД и baseline для всех отчетов"""
    print("="*70)
    print("BUILD MODE: Инициализация системы")
    print("="*70)
    
    # 1. Инициализация БД
    print("\n1. Инициализация PostgreSQL...")
    import subprocess
    result = subprocess.run(['python', 'init_db.py'], capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Ошибка инициализации БД: {result.stderr}")
        sys.exit(1)
    print("✓ БД инициализирована")
    
    # 2. Подключение к БД
    db_manager = DatabaseManager(config)
    
    # 3. Читаем отчеты
    reports = load_reports(reports_json)
    if not reports:
        print("Нет отчетов для инициализации")
        sys.exit(1)
    
    print(f"\nСоздание baseline для {len(reports)} отчетов...\n")
    
    # 4. Создаем init_baseline для каждого отчета
    for idx, report in enumerate(reports, 1):
        report_id = report['id']
        report_name = report['name']
        report_url = report['url']
        
        print(f"{idx}/{len(reports)}: {report_name}")
        
        # Пути
        init_path = f'Data/baselines/{report_id}_init_baseline.png'
        last_path = f'Data/changes/{report_id}/last_baseline.png'
        
        # Создаем директории
        Path('Data/baselines').mkdir(parents=True, exist_ok=True)
        Path(f'Data/changes/{report_id}').mkdir(parents=True, exist_ok=True)
        
        # Скриншот
        monitor = ReportMonitor(config, debug=debug)
        if monitor.take_screenshot(report_url, init_path):
            # Копия в last_baseline
            import shutil
            shutil.copy2(init_path, last_path)
            
            # Сохранить hash в БД
            hash_value = monitor.calculate_hash(last_path)
            db_manager.save_baseline(report_id, report_name, hash_value)
            
            print(f"  ✓ Baseline создан: {init_path}")
        else:
            print(f"  ✗ Ошибка создания baseline")
        
        monitor.close()
    
    db_manager.close()
    
    print("\n" + "="*70)
    print("✓ BUILD ЗАВЕРШЕН!")
    print("="*70)
    print("\nСледующие шаги:")
    print("  1. python monitor.py --check REPORT_ID")
    print("  2. python monitor.py reports.json (планировщик)")


def check_mode(report_id, config, reports_json='reports.json', debug=False):
    """CHECK - Ручная проверка одного отчета"""
    print(f"CHECK MODE: {report_id}")
    
    # Найти конфигурацию отчета
    reports = load_reports(reports_json)
    report = next((r for r in reports if r['id'] == report_id), None)
    
    if not report:
        print(f"Ошибка: Отчет {report_id} не найден в {reports_json}")
        sys.exit(1)
    
    # Выполнить check
    db_manager = DatabaseManager(config)
    result = check_report(report, config, db_manager, debug=debug)
    db_manager.close()
    
    # Вывести результат
    print("\n" + "="*70)
    print("РЕЗУЛЬТАТ ПРОВЕРКИ")
    print("="*70)
    print(f"Отчет: {result['report_name']}")
    print(f"Статус: {result['status']}")
    if result.get('diff_percent') is not None:
        print(f"diff_percent: {result['diff_percent']}%")
    if result.get('error'):
        print(f"Ошибка: {result['error']}")
    print(f"Длительность: {result['duration_sec']} сек")
    print("="*70)


def start_mode(reports_json, config, debug=False):
    """START - Планировщик с таймерами (текущая логика)"""
    global shutdown_flag
    
    # Загрузка отчетов
    reports = load_reports(reports_json)
    
    if not reports:
        logging.error("Нет включенных отчетов для мониторинга")
        sys.exit(1)
    
    logging.info(f"Загружено {len(reports)} отчетов для мониторинга")
    
    # Подключение к БД
    db_manager = DatabaseManager(config)
    logging.info(f"Подключено к PostgreSQL: {config['pg_database']}.{config['pg_schema']}")
    
    # Текущая логика планировщика (из старого main)
    # ... (копируем существующую логику с таймерами)
    logging.info("START MODE: Запуск планировщика по расписанию")
    logging.info("Нажмите Ctrl+C для остановки")
    
    # Для начала просто делаем check-now как в старом коде
    # Потом добавим реальные таймеры
    min_worker_threads = config.get('min_worker_threads', 1)
    max_worker_threads = config.get('max_worker_threads', 5)
    max_workers = max(min_worker_threads, min(max_worker_threads, len(reports)))
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        while not shutdown_flag:
            logging.info("Запуск проверки всех отчетов...")
            
            futures = {
                executor.submit(check_report, report, config, db_manager, debug): report
                for report in reports
            }
            
            for future in as_completed(futures):
                try:
                    result = future.result()
                    print(f"{result['report_name']}: {result['status']}")
                except Exception as e:
                    logging.error(f"Ошибка: {e}")
            
            min_interval = min(r.get('interval', 60) for r in reports)
            logging.info(f"Ожидание следующего цикла ({min_interval} мин)...")
            for _ in range(min_interval * 60):
                if shutdown_flag:
                    break
                time.sleep(1)
    
    db_manager.close()
    logging.info("Мониторинг остановлен")


def main():
    """Главная функция - роутинг между командами"""
    global shutdown_flag
    
    import argparse
    parser = argparse.ArgumentParser(description='Power BI Multi-Report Monitor')
    
    # Команды
    parser.add_argument('--build', metavar='REPORTS_JSON', help='BUILD: Инициализация БД + baseline для всех отчетов')
    parser.add_argument('--check', metavar='REPORT_ID', help='CHECK: Ручная проверка одного отчета')
    parser.add_argument('--check-all', metavar='REPORTS_JSON', help='CHECK-ALL: Проверка всех отчетов (без планировщика)')
    parser.add_argument('--restore-screenshot', nargs=2, metavar=('REPORT_ID', 'CHECK_ID'), help='Восстановить скриншот из БД')
    parser.add_argument('reports_json', nargs='?', help='START: Запуск планировщика')
    
    # Флаги
    parser.add_argument('--config', default='reports.json', help='JSON конфигурация отчетов (для --check)')
    parser.add_argument('--debug', action='store_true', help='Debug режим: видимый браузер')
    
    args = parser.parse_args()
    
    # Загрузка конфигурации
    config = load_config()
    logger = setup_logging(config)
    
    # Регистрируем обработчики сигналов
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # РОУТИНГ КОМАНД
    
    # 1. BUILD - Инициализация
    if args.build:
        build_mode(args.build, config, debug=args.debug)
        sys.exit(0)
    
    # 2. CHECK - Ручная проверка одного отчета
    if args.check:
        check_mode(args.check, config, reports_json=args.config, debug=args.debug)
        sys.exit(0)
    
    # 3. CHECK-ALL - Проверка всех отчетов
    if args.check_all:
        reports = load_reports(args.check_all)
        db_manager = DatabaseManager(config)
        for report in reports:
            result = check_report(report, config, db_manager, debug=args.debug)
            print(f"{result['report_name']}: {result['status']} ({result.get('diff_percent', 0)}%)")
        db_manager.close()
        sys.exit(0)
    
    # 4. RESTORE - Восстановление скриншота
    if args.restore_screenshot:
        report_id, check_id = args.restore_screenshot
        check_id = int(check_id)
        
        print(f"Восстановление скриншота: report_id={report_id}, check_id={check_id}")
        
        # Подключаемся к БД
        try:
            db_manager = DatabaseManager(config)
            restored = db_manager.restore_screenshot(report_id, check_id)
            
            if restored:
                output_path = f'Data/recovery/restored_{report_id}_{check_id}.png'
                restored.save(output_path)
                print(f"✓ Скриншот восстановлен: {output_path}")
                
                # Показываем информацию
                from pathlib import Path
                file_size = Path(output_path).stat().st_size / 1024
                print(f"  Размер: {file_size:.1f} KB")
                print(f"  Размер: {restored.size}")
            else:
                print("✗ Не удалось восстановить скриншот")
                sys.exit(1)
        except Exception as e:
            print(f"✗ Ошибка: {e}")
            sys.exit(1)
        
        sys.exit(0)
    
    # 5. START - Планировщик
    if args.reports_json:
        start_mode(args.reports_json, config, debug=args.debug)
        sys.exit(0)
    
    # Нет команды - показать help
    parser.print_help()
    sys.exit(1)


if __name__ == "__main__":
    main()
