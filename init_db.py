"""
Initialize PostgreSQL Database
Инициализация базы данных для Power BI мониторинга
"""

import os
import sys
import psycopg2
from pathlib import Path
from dotenv import load_dotenv


def load_config():
    """Загрузить конфигурацию PostgreSQL"""
    load_dotenv('config.env')
    
    return {
        'host': os.getenv('PG_HOST', '10.3.0.100'),
        'port': int(os.getenv('PG_PORT', '5432')),
        'database': os.getenv('PG_DATABASE', 'db_new'),
        'user': os.getenv('PG_USER', 'dwh_bi_user'),
        'password': os.getenv('PG_PASSWORD', ''),
        'schema': os.getenv('PG_SCHEMA', 'sandbox')
    }


def create_directories():
    """Создать необходимые директории"""
    dirs = [
        './Data/baselines',
        './Data/changes',
        './Data/recovery',
        './Data/import',
        './logs'
    ]
    
    for dir_path in dirs:
        Path(dir_path).mkdir(parents=True, exist_ok=True)


def init_database(config):
    """Инициализировать базу данных"""
    conn = None
    
    try:
        print(f"\nПодключение к PostgreSQL: {config['host']}:{config['port']}")
        print(f"База данных: {config['database']}")
        print(f"Схема: {config['schema']}")
        
        # Подключаемся к существующей БД db_new
        conn = psycopg2.connect(
            host=config['host'],
            port=config['port'],
            database=config['database'],
            user=config['user'],
            password=config['password']
        )
        conn.autocommit = True
        cursor = conn.cursor()
        
        print(f"Подключено к базе данных: {config['database']}")
        
        # Проверяем существование схемы sandbox
        cursor.execute("""
            SELECT schema_name FROM information_schema.schemata 
            WHERE schema_name = %s
        """, (config['schema'],))
        if cursor.fetchone():
            print(f"Схема {config['schema']} существует")
        else:
            print(f"Ошибка: Схема {config['schema']} не найдена!")
            return False
        
        # Читаем и выполняем schema.sql
        schema_path = Path(__file__).parent / 'schema.sql'
        if not schema_path.exists():
            print(f"Ошибка: Файл schema.sql не найден: {schema_path}")
            return False
        
        print(f"\nВыполнение schema.sql в схеме {config['schema']}...")
        with open(schema_path, 'r', encoding='utf-8') as f:
            schema_sql = f.read()
        
        # Устанавливаем search_path перед выполнением
        cursor.execute(f"SET search_path TO {config['schema']}")
        cursor.execute(schema_sql)
        conn.commit()
        print(f"Таблицы созданы успешно")
        
        # Проверяем НАШИ таблицы (только для мониторинга)
        our_tables = ['baselines', 'monitoring_checks']
        
        print(f"\nТаблицы мониторинга в схеме {config['schema']}:")
        for table_name in our_tables:
            cursor.execute(f"""
                SELECT COUNT(*) 
                FROM information_schema.tables 
                WHERE table_schema = %s AND table_name = %s
            """, (config['schema'], table_name))
            exists = cursor.fetchone()[0]
            
            if exists:
                cursor.execute(f"SELECT COUNT(*) FROM {config['schema']}.{table_name}")
                count = cursor.fetchone()[0]
                print(f"  {table_name}: {count} записей")
            else:
                print(f"  {table_name}: не создана")
        
        # Проверяем НАШИ view
        our_views = ['v_latest_checks', 'v_report_stats']
        
        print(f"\nView для анализа:")
        for view_name in our_views:
            cursor.execute(f"""
                SELECT COUNT(*) 
                FROM information_schema.views 
                WHERE table_schema = %s AND table_name = %s
            """, (config['schema'], view_name))
            exists = cursor.fetchone()[0]
            
            if exists:
                print(f"  {view_name}: OK")
            else:
                print(f"  {view_name}: не создана")
        
        cursor.close()
        conn.close()
        
        return True
        
    except psycopg2.Error as e:
        print(f"\nОшибка PostgreSQL: {e}")
        return False
        
    except Exception as e:
        print(f"\nОшибка: {e}")
        return False
        
    finally:
        if conn:
            conn.close()


def test_connection(config):
    """Тест подключения к базе"""
    try:
        conn = psycopg2.connect(
            host=config['host'],
            port=config['port'],
            database=config['database'],
            user=config['user'],
            password=config['password']
        )
        cursor = conn.cursor()
        cursor.execute("SELECT version()")
        version = cursor.fetchone()[0]
        print(f"\nПодключение успешно!")
        print(f"PostgreSQL версия: {version.split(',')[0]}")
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"\nОшибка подключения: {e}")
        return False


def main():
    """Главная функция"""
    print("Power BI Monitor - Инициализация базы данных")
    
    # Загружаем конфигурацию
    config = load_config()
    
    # Создаем директории
    print("\nСоздание директорий...")
    create_directories()
    
    # Инициализируем БД
    if not init_database(config):
        print("\nОшибка при инициализации базы данных")
        sys.exit(1)
    
    # Тестируем подключение
    if not test_connection(config):
        sys.exit(1)
    
    print("\nИнициализация завершена успешно!")
    print("\nСледующие шаги:")
    print("1. Подготовьте Excel файл с отчетами")
    print("2. Конвертируйте в JSON: python excel_to_json.py reports.xlsx")
    print("3. Запустите мониторинг: python monitor.py reports.json")
    print()


if __name__ == "__main__":
    main()

