# Power BI Multi-Report Monitor

Система мониторинга 96+ Power BI Report Server отчетов с обнаружением визуальных изменений через векторную математику.

## Математика

**Quadtree + MSE (Mean Squared Error)**
- Рекурсивное деление скриншота на блоки 32×32 px (5 уровней drill-down)
- MSE сравнение каждого блока между last_baseline и current
- Точная локализация измененных областей

**XOR Delta Compression**
```python
# Сохранение (NumPy + gzip)
delta = np.bitwise_xor(initial_baseline, current_screenshot)
compressed = gzip.compress(delta)  # ~12-150 KB вместо 423 KB PNG
→ PostgreSQL BYTEA

# Восстановление
restored = np.bitwise_xor(initial_baseline, decompress(delta))
→ 100% точность, побитовое совпадение
```

**Экономия:** 92-97% места (245 KB delta vs 3.4 MB PNG для 8 проверок)

## Три команды

### 1. BUILD - Инициализация (один раз)

```bash
python monitor.py --build reports.json
```

- Создает PostgreSQL схему (db_new.sandbox)
- Создает init_baseline для всех отчетов
- НЕ запускает мониторинг

### 2. CHECK - Ручная проверка

```bash
python monitor.py --check sales_dev_fix
```

- Проверяет один отчет немедленно
- Создает XOR delta (~12 KB) → PostgreSQL
- Создает diff.png (визуализация)
- Обновляет last_baseline

**Pipeline (унифицированный):**
1. Логин + создать current_screenshot.png
2. Сравнить с last_baseline.png (quadtree)
3. Создать XOR delta → БД
4. Создать current_screenshot_diff.png
5. Удалить old last_baseline
6. Переименовать current → last_baseline

### 3. START - Планировщик

```bash
python monitor.py reports.json
```

- Проверяет отчеты по расписанию (interval, start_time)
- Многопоточность: 1-5 потоков
- Бесконечный цикл (Ctrl+C для остановки)

### 4. RESTORE - Восстановление из БД

```bash
python monitor.py --restore-screenshot REPORT_ID CHECK_ID
```

- Восстанавливает скриншот из delta
- Файл: Data/recovery/restored_{report_id}_{check_id}.png

## Структура данных

```
Data/                                    # Файловый кеш
├── baselines/
│   └── {report_id}_init_baseline.png   # Неизменный эталон
├── changes/{report_id}/
│   ├── last_baseline.png               # Обновляется каждый чек
│   └── current_screenshot_diff.png     # Визуализация (перезаписывается)
├── recovery/
│   └── restored_*.png                  # Восстановленные из БД
└── import/
    └── reports.csv                     # Конфигурация (будущее)

PostgreSQL (db_new.sandbox):             # Logger
├── baselines: report_id, hash_value
└── monitoring_checks: status, diff_percent, delta_compressed (BYTEA)
```

**БД = logger (БЕЗ путей к файлам)**  
**Data/ = кеш (файлы БЕЗ timestamp)**

## Конфигурация

**reports.json:**
```json
{
  "reports": [
    {
      "id": "sales_dev_fix",
      "name": "Отчет продаж",
      "url": "http://dtln-sql-03/.../Sales",
      "interval": 60,
      "start_time": "09:30",
      "threshold": 5.0,
      "enabled": true
    }
  ]
}
```

**config.env:**
- PostgreSQL: `db_new.sandbox` @ 10.3.0.100
- Power BI: r.power@resoleasing.com
- Quadtree: MSE_THRESHOLD=1.0, MIN_BLOCK_SIZE=32, MAX_DEPTH=5

## Метрики

**diff_percent для анализа:**
- 0% = unchanged (данные не обновились)
- 0.01-10% = changed (нормальное обновление) ✓
- >20-30% = changed (возможная ошибка!) 🚨

**Статусы:**
- `baseline_created` - первый запуск
- `unchanged` - визуально идентично
- `changed` - обнаружены изменения
- `error` - ошибка скриншота

## PostgreSQL запросы

```sql
SET search_path TO sandbox;

-- История проверок
SELECT id, check_time, status, diff_percent, 
       LENGTH(delta_compressed)/1024 as delta_kb
FROM monitoring_checks 
WHERE report_id = 'sales_dev_fix'
ORDER BY check_time DESC;

-- Статистика
SELECT * FROM v_report_stats;

-- Последние проверки
SELECT * FROM v_latest_checks;
```

## Требования

- Python 3.8+
- PostgreSQL 12+ (db_new.sandbox)
- Chrome/Chromium
- NumPy, Pillow, Selenium, psycopg2

---

**Готово к production мониторингу 96 отчетов!**
