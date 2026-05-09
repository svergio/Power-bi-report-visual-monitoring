"""
Excel to JSON Converter
Конвертация Excel файла с конфигурацией отчетов в reports.json
"""

import sys
import json
from pathlib import Path
import openpyxl
from datetime import time


def parse_excel(excel_path):
    """
    Парсинг Excel файла с конфигурацией отчетов
    
    Ожидаемые колонки:
    - Name: Название отчета
    - URL: Полный URL отчета
    - Interval: Интервал проверки в минутах
    - StartTime: Время первой проверки (HH:MM)
    - Threshold: Порог различий в % (опционально, по умолчанию 5.0)
    - Enabled: Включен ли отчет (опционально, по умолчанию True)
    
    Args:
        excel_path: Путь к Excel файлу
        
    Returns:
        Список словарей с конфигурацией отчетов
    """
    try:
        workbook = openpyxl.load_workbook(excel_path)
        sheet = workbook.active
        
        # Читаем заголовки
        headers = []
        for cell in sheet[1]:
            if cell.value:
                headers.append(cell.value.strip())
        
        print(f"Найденные колонки: {headers}")
        
        # Проверяем обязательные колонки
        required = ['Name', 'URL', 'Interval']
        missing = [col for col in required if col not in headers]
        if missing:
            raise ValueError(f"Отсутствуют обязательные колонки: {missing}")
        
        # Индексы колонок
        col_indices = {header: idx for idx, header in enumerate(headers)}
        
        reports = []
        row_num = 2
        
        for row in sheet.iter_rows(min_row=2, values_only=True):
            # Пропускаем пустые строки
            if not row or not any(row):
                continue
            
            try:
                # Извлекаем данные
                name = row[col_indices['Name']]
                url = row[col_indices['URL']]
                interval = row[col_indices['Interval']]
                
                if not name or not url:
                    print(f"Предупреждение: Строка {row_num} пропущена (пустое имя или URL)")
                    row_num += 1
                    continue
                
                # Генерируем ID из имени
                report_id = name.lower().replace(' ', '_').replace('(', '').replace(')', '')
                report_id = ''.join(c for c in report_id if c.isalnum() or c == '_')
                
                # StartTime
                start_time = row[col_indices.get('StartTime', len(row))] if 'StartTime' in col_indices else None
                if start_time:
                    if isinstance(start_time, time):
                        start_time = start_time.strftime('%H:%M')
                    elif isinstance(start_time, str):
                        start_time = start_time.strip()
                    else:
                        start_time = '09:00'
                else:
                    start_time = '09:00'
                
                # Threshold
                threshold = row[col_indices.get('Threshold', len(row))] if 'Threshold' in col_indices else None
                if threshold is None or not isinstance(threshold, (int, float)):
                    threshold = 5.0
                else:
                    threshold = float(threshold)
                
                # Enabled
                enabled = row[col_indices.get('Enabled', len(row))] if 'Enabled' in col_indices else None
                if enabled is None:
                    enabled = True
                elif isinstance(enabled, str):
                    enabled = enabled.lower() in ['yes', 'true', 'да', '1', 'y']
                else:
                    enabled = bool(enabled)
                
                report = {
                    'id': report_id,
                    'name': str(name).strip(),
                    'url': str(url).strip(),
                    'interval': int(interval),
                    'start_time': start_time,
                    'threshold': threshold,
                    'enabled': enabled
                }
                
                reports.append(report)
                print(f"Строка {row_num}: {report['name']} (interval: {report['interval']} мин)")
                
            except Exception as e:
                print(f"Ошибка в строке {row_num}: {e}")
            
            row_num += 1
        
        return reports
        
    except FileNotFoundError:
        print(f"Ошибка: Файл не найден: {excel_path}")
        return None
    except Exception as e:
        print(f"Ошибка при чтении Excel: {e}")
        return None


def validate_reports(reports):
    """
    Валидация конфигурации отчетов
    
    Args:
        reports: Список отчетов
        
    Returns:
        True если валидация прошла успешно
    """
    print(f"\nВалидация {len(reports)} отчетов...")
    
    errors = []
    warnings = []
    
    # Проверка уникальности ID
    ids = [r['id'] for r in reports]
    duplicates = [id for id in ids if ids.count(id) > 1]
    if duplicates:
        errors.append(f"Дубликаты ID: {set(duplicates)}")
    
    # Проверка каждого отчета
    for idx, report in enumerate(reports, 1):
        # URL
        if not report['url'].startswith('http'):
            errors.append(f"Отчет #{idx} ({report['name']}): некорректный URL")
        
        # Interval
        if report['interval'] < 1:
            errors.append(f"Отчет #{idx} ({report['name']}): интервал должен быть >= 1")
        if report['interval'] > 1440:
            warnings.append(f"Отчет #{idx} ({report['name']}): интервал > 24 часов")
        
        # Threshold
        if report['threshold'] < 0 or report['threshold'] > 100:
            errors.append(f"Отчет #{idx} ({report['name']}): threshold должен быть 0-100%")
    
    # Вывод результатов
    if errors:
        print(f"\nНайдено {len(errors)} ошибок:")
        for error in errors:
            print(f"  - {error}")
        return False
    
    if warnings:
        print(f"\nПредупреждения ({len(warnings)}):")
        for warning in warnings:
            print(f"  - {warning}")
    
    print(f"Валидация прошла успешно")
    return True


def save_json(reports, output_path):
    """
    Сохранение конфигурации в JSON файл
    
    Args:
        reports: Список отчетов
        output_path: Путь к выходному JSON файлу
    """
    try:
        config = {
            'reports': reports
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        
        print(f"\nКонфигурация сохранена: {output_path}")
        print(f"Всего отчетов: {len(reports)}")
        print(f"Включенных: {sum(1 for r in reports if r['enabled'])}")
        print(f"Отключенных: {sum(1 for r in reports if not r['enabled'])}")
        
        return True
        
    except Exception as e:
        print(f"Ошибка при сохранении JSON: {e}")
        return False


def print_summary(reports):
    """Вывод сводной информации"""
    print("\nСводка по отчетам:")
    
    # Группировка по интервалам
    intervals = {}
    for report in reports:
        interval = report['interval']
        if interval not in intervals:
            intervals[interval] = []
        intervals[interval].append(report)
    
    print(f"\nГруппировка по интервалам:")
    for interval in sorted(intervals.keys()):
        count = len(intervals[interval])
        print(f"  - {interval} мин: {count} отчет(ов)")
    
    # Расчет нагрузки
    total_checks_per_hour = sum(60 / r['interval'] for r in reports if r['enabled'])
    print(f"\nОжидаемая нагрузка:")
    print(f"  - Проверок в час: ~{int(total_checks_per_hour)}")
    print(f"  - Проверок в день: ~{int(total_checks_per_hour * 24)}")
    
    print("="*70)


def main():
    """Главная функция"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Конвертация Excel файла с отчетами в JSON'
    )
    parser.add_argument(
        'excel_file',
        type=str,
        help='Путь к Excel файлу'
    )
    parser.add_argument(
        '-o', '--output',
        type=str,
        default='reports.json',
        help='Путь к выходному JSON файлу (по умолчанию: reports.json)'
    )
    
    args = parser.parse_args()
    
    print("Excel to JSON Converter")
    print(f"\nВходной файл: {args.excel_file}")
    print(f"Выходной файл: {args.output}\n")
    
    # Парсинг Excel
    reports = parse_excel(args.excel_file)
    
    if not reports:
        print("\nОшибка: Не удалось прочитать отчеты из Excel")
        sys.exit(1)
    
    if len(reports) == 0:
        print("\nОшибка: Не найдено ни одного отчета")
        sys.exit(1)
    
    # Валидация
    if not validate_reports(reports):
        sys.exit(1)
    
    # Сохранение
    if not save_json(reports, args.output):
        sys.exit(1)
    
    # Сводка
    print_summary(reports)
    
    print(f"\nСледующий шаг: python monitor.py {args.output}")
    print()


if __name__ == "__main__":
    main()

