#!/bin/bash
cd "$(dirname "$0")"
source .venv/bin/activate

echo ""
echo "======================================================================"
echo "СТРЕСС-ТЕСТ МОНИТОРИНГА - СТАТУС"
echo "======================================================================"
echo ""

if [ -f monitor.pid ]; then
    PID=$(cat monitor.pid)
    if ps -p $PID > /dev/null 2>&1; then
        echo "✓ Процесс работает (PID: $PID)"
        ps -p $PID -o pid,etime,%cpu,%mem,command | tail -1
    else
        echo "✗ Процесс не найден (PID: $PID)"
    fi
else
    echo "✗ Файл monitor.pid не найден"
fi

echo ""
echo "======================================================================"
echo "РЕЗУЛЬТАТЫ ИЗ БАЗЫ ДАННЫХ"
echo "======================================================================"

python <<'EOF'
import psycopg2
from datetime import datetime
from collections import defaultdict

conn = psycopg2.connect(
    host='10.3.0.100',
    port=5432,
    database='db_new',
    user='dwh_bi_user',
    password='Ojoaidf98$3'
)
cur = conn.cursor()
cur.execute("SET search_path TO sandbox;")

cur.execute("""
    SELECT report_id, COUNT(*) as checks, 
           AVG(diff_percent) as avg_diff,
           AVG(duration_sec) as avg_duration,
           MIN(check_time) as first_check,
           MAX(check_time) as last_check
    FROM monitoring_checks 
    WHERE check_time > NOW() - INTERVAL '2 hours'
    GROUP BY report_id
    ORDER BY report_id
""")

print("\nСтатистика по отчетам:")
print("-" * 90)
print(f"{'Отчет':<20} | {'Проверок':<8} | {'Ср.Diff%':<10} | {'Ср.Время':<10} | {'Интервал'}")
print("-" * 90)

for row in cur.fetchall():
    report_id, checks, avg_diff, avg_duration, first, last = row
    print(f"{report_id:<20} | {checks:<8} | {avg_diff:>7.2f}%  | {avg_duration:>7.1f}s  | {first.strftime('%H:%M')} - {last.strftime('%H:%M')}")

print("-" * 90)

cur.execute("""
    SELECT COUNT(*), 
           COUNT(DISTINCT report_id),
           AVG(duration_sec),
           MIN(check_time),
           MAX(check_time)
    FROM monitoring_checks 
    WHERE check_time > NOW() - INTERVAL '2 hours'
""")

total_checks, unique_reports, avg_time, first_time, last_time = cur.fetchone()
print(f"\nИтого:")
print(f"  Всего проверок: {total_checks}")
print(f"  Уникальных отчетов: {unique_reports}")
print(f"  Среднее время: {avg_time:.1f}s")
print(f"  Период: {first_time.strftime('%Y-%m-%d %H:%M')} - {last_time.strftime('%H:%M')}")

elapsed_minutes = (last_time - first_time).total_seconds() / 60
print(f"  Длительность теста: {elapsed_minutes:.1f} минут")

print("\n" + "="*90)
print("Последние 5 проверок:")
print("-" * 90)
cur.execute("""
    SELECT report_id, check_time, status, diff_percent, duration_sec 
    FROM monitoring_checks 
    WHERE check_time > NOW() - INTERVAL '2 hours'
    ORDER BY check_time DESC 
    LIMIT 5
""")
for row in cur.fetchall():
    print(f"{row[0]:<20} | {row[1]} | {row[2]:<10} | {row[3]:>6.2f}% | {row[4]:>5.1f}s")

print("="*90)
conn.close()
EOF

echo ""
echo "Для остановки теста: kill \$(cat monitor.pid)"
echo ""


