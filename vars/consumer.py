from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
import asyncio
import json
import logging
import os
from datetime import datetime
from django.utils import timezone
import os

# Логгер
logger = logging.getLogger(__name__)

# Импорты внутри файла (чтобы не зависеть от других модулей)
from . import opc_config, message_handler
from .models import Recipe, Trends, Message
from queue import Queue

# Буфер для архива
plc_buffer = Queue(maxsize=5)

# ПЛК, который опрашивается
plc_1 = opc_config.PLC('192.168.20.50', '4840')
# Список переменных, с которым работаем
var_list = opc_config.VariableList()

# Загрузка конфигурации
file_path = os.path.join(os.path.dirname(__file__), "config.json")
with open(file_path, "r", encoding='utf-8') as f:
    data = json.load(f)

file_path_message = os.path.join(os.path.dirname(__file__), "message.json")
with open(file_path_message, "r", encoding='utf-8') as f:
    data_message = json.load(f)

# Формирование списка переменных
for dt in data:
    var_list.add(opc_config.VariablePLC(
        dt["name"], f'{opc_config.ADR}.{dt["opc_adr"]}', plc_1, dt["scale"], dt["ID"], dt["isArchive"]))

# Вспомогательные функции
def toogle():
    try:
        var = var_list.get_variable_by_Name('xRegul')
        cur = var.value
        new_value = not cur
        var.value = new_value
    except Exception as e:
        print(f"Ошибка: {e}")

def write(value, name):
    try:
        var = var_list.get_variable_by_Name(name)
        var.value = value
    except Exception as e:
        print(f"Ошибка: {e}")

def recipe_save(recipe):
    try:
        var_list.get_variable_by_Name("Recipe_ID").value = recipe.pk
        var_list.get_variable_by_Name("Recipe_v1").value = recipe.var1
        var_list.get_variable_by_Name("Recipe_v2").value = recipe.var2
        var_list.get_variable_by_Name("Recipe_v3").value = recipe.var3
        var_list.get_variable_by_Name("Recipe_Name").value = recipe.name
    except Exception as e:
        print(f"Ошибка: {e}")

async def save_to_buffer():
    """Формируем буфер по всем данным, у которых is_archived = True"""
    try:
        if plc_1.Is_Connected:
            for var in var_list.vars:
                if var.is_archive:  # Только архивируемые переменные
                    plc_buffer.put([var.ID, float(var.value), timezone.now()])
            if plc_buffer.full():
                logger.warning("Буфер переполнен. Отбрасываем новые данные.")
                await flush_buffer_to_db()
    except Exception as e:
        logger.error(f"Ошибка сохранения в буфер: {e}")

async def flush_buffer_to_db():
    """Сохраняем буфер в БД"""
    try:
        with plc_buffer.mutex:
            buffer_items = list(plc_buffer.queue)
            plc_buffer.queue.clear()
        if not buffer_items:
            logger.info("Буфер пуст. Ничего не сохраняем в БД.")
            return
        records_to_create = []
        for batch in buffer_items:
            records_to_create.append(
                Trends(
                    id_var=batch[0],
                    value=batch[1],
                    timestamp=batch[2]
                )
            )
        await sync_to_async(Trends.objects.bulk_create)(records_to_create)
        logger.info(f"Сохранено {len(records_to_create)} записей в БД.")
    except Exception as e:
        logger.error(f"Ошибка при сохранении в БД: {e}")

class OpcUaConsumer(AsyncWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.periodic_task = None
        self.poller_task = None

    async def connect(self):
        await self.accept()
        logger.info("WebSocket подключён")
        # Запускаем фоновый опрос PLC
        if not self.poller_task or self.poller_task.done():
            self.poller_task = asyncio.create_task(self.start_opc_poller())
        # Запускаем периодическую отправку данных
        if not self.periodic_task or self.periodic_task.done():
            self.periodic_task = asyncio.create_task(self.send_periodic_data())

    async def disconnect(self, close_code):
        logger.info(f"WebSocket закрыт. Код: {close_code}")
        # Отменяем все фоновые задачи
        if self.periodic_task:
            self.periodic_task.cancel()
        if self.poller_task:
            self.poller_task.cancel()

    async def start_opc_poller(self):
        """Фоновый опрос OPC UA"""
        while True:
            try:
                # Подключение к OPC UA серверу
                if not plc_1.Is_Connected:
                    await asyncio.to_thread(plc_1.run)
                    logger.info("Подключено к OPC UA серверу")
                # Обновление значений переменных
                await asyncio.to_thread(var_list.update_values)
                # Сохранение в буфер
                await save_to_buffer()
                await asyncio.sleep(0.5)  # Интервал опроса
            except Exception as e:
                logger.error(f"Ошибка в фоновом опросе OPC UA: {e}")
                await asyncio.sleep(5)

    async def send_periodic_data(self):
        """Периодическая отправка данных клиентам"""
        while True:
            try:
                if plc_1.Is_Connected:
                    data = await asyncio.to_thread(var_list.list_json_with_Unit)
                    if data and data != '{}':
                        await self.send(text_data=data)
                else:
                    logger.warning("Получены пустые данные от PLC")
                    await asyncio.sleep(1)  # Интервал отправки

            except asyncio.CancelledError:
                logger.info("Периодическая отправка данных остановлена")
                break
            except Exception as e:
                logger.error(f"Ошибка отправки периодических данных: {e}")
                await asyncio.sleep(5)

    async def receive(self, text_data=None, bytes_data=None):
        try:
            if text_data:
                await self.handle_text_message(text_data)
        except Exception as e:
            logger.error(f"Ошибка обработки сообщения: {e}")
            await self.close(code=4000)

    async def handle_text_message(self, message: str):
        """Обработка текстовых сообщений от клиента"""
        logger.info(f"Получено текстовое сообщение: {message}")
        try:
            data = json.loads(message)
            action = data.get("action")

            if action == "regulswitch":
                toogle()
                await self._send_response("success", action)
            elif action == "setpoint":
                set_point = int(data.get("value"))
                write(set_point, "SP_Regule")
                await self._send_response("success", action)
            elif action == "recipe":
                id_recipe = int(data.get("ID"))
                recipe = await sync_to_async(Recipe.objects.get)(pk=id)
                recipe_save(recipe)
                await self._send_response("success", action)

            elif action == "get_data":
                # Отправляем текущие данные из OPC UA
                data = await asyncio.to_thread(var_list.list_json_with_Unit)
                if data and data != '{}':
                    await self.send(text_data=data)
                else:
                    logger.warning("По запросу get_data получены пустые данные")
                    await self._send_error("No data available")

            else:
                await self._send_error("Unknown action")

        except json.JSONDecodeError:
            await self._send_error("Invalid JSON format")
        except Recipe.DoesNotExist:
            await self._send_error("Recipe not found")
        except (ValueError, KeyError) as e:
            await self._send_error(f"Invalid data format: {e}")
        except Exception as e:
            logger.error(f"Ошибка выполнения действия {action}: {e}")
            await self._send_error(f"Failed to execute action: {e}")

    async def _send_response(self, status: str, action: str):
        """Вспомогательная функция для отправки успешного ответа."""
        response = {
            "status": status,
            "action": action,
            "timestamp": str(timezone.now())
        }
        await self.send(text_data=json.dumps(response))
