from datetime import datetime
from collections import defaultdict

data = [
    [1,2,datetime(2025, 12, 20, 14, 30, 0)],
    [2,3,datetime(2025, 12, 20, 14, 30, 0)], 
    [3,13,datetime(2025, 12, 20, 14, 30, 0)],              
    [1,5,datetime(2025, 12, 20, 15, 30, 0)],
    [2,32,datetime(2025, 12, 20, 15, 30, 0)], 
    [1,45,datetime(2025, 12, 20, 16, 30, 0)],
    [2,55,datetime(2025, 12, 20, 17, 30, 0)],
    [1,101,datetime(2025, 12, 20, 17, 30, 0)],
    [3,222,datetime(2025, 12, 20, 17, 30, 0)],        
    [2,62,datetime(2025, 12, 20, 18, 30, 0)],    

]
"""
    =>
        4 2 3
        5 5 32
"""

# 1. Определяем временной интервал для группировки
def get_bucket(dt):
    return dt.replace(second=0, microsecond=0)  # группировка по минутам

def convert_buffer(data) -> list:

    # 1. Делаем некоторые обновления для работы не с QuerySet, а для списка
    processed_data = []
    for obj in data:
        processed_data.append([
            obj.id_var,      # замените на реальное имя поля
            obj.value,    # замените на реальное имя поля
            obj.timestamp # замените на реальное имя поля
        ])

    # 2. Собираем все уникальные ключи
    all_keys = sorted(set(d[0] for d in processed_data))

    # 3. Группируем данные по временным интервалам
    grouped = defaultdict(dict)  # {временной интервал: {ключ: значение}}
    for key, value, dt in processed_data:
        bucket = get_bucket(dt)
        grouped[bucket][key] = value

    # 4. Сортируем временные интервалы по возрастанию
    sorted_buckets = sorted(grouped.keys())

    # 5. Храним последние известные значения для каждого ключа
    last_values = {key: None for key in all_keys}

    # 6. Строим результат
    result = []
    for bucket in sorted_buckets:
        row = [bucket.strftime("%Y-%m-%d %H:%M:%S")]  # первый элемент — временной интервал
        for key in all_keys:
            if key in grouped[bucket]:
                # Если значение есть — берём его и обновляем last_values
                value = grouped[bucket][key]
                last_values[key] = value
                row.append(value)
            else:
                # Если нет — берём последнее известное значение
                value = last_values[key] if last_values[key] is not None else 0
                row.append(value)
        result.append(row)

    return result


if __name__ == "__main__":
    result = []
    result = convert_buffer(data)
    for r in result:
        print(r)
