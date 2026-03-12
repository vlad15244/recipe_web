import asyncio
import logging
from asgiref.sync import sync_to_async
from datetime import datetime
from django.utils import timezone
from queue import Queue
import json
import os
from channels.generic.websocket import AsyncWebsocketConsumer

from . import opc_config, message_handler
from .models import Trends, Message, Recipe

logger = logging.getLogger(__name__)
# Буфер для архива
plc_buffer = Queue(maxsize=5)

# PLC, который опрашивается
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

# Формирование списка переменных
for dt in data:
    var_list.add(opc_config.VariablePLC(
        dt["name"], f'{opc_config.ADR}.{dt["opc_adr"]}', plc_1, dt["scale"], dt["ID"], dt["isArchive"]))
    
class OpcRuntime:
    def __init__(self):
        self.poll_task = None
        self.buffer_task = None
        self.message_task = None
        

    async def start(self):
        logger.info("Запуск фонового опроса PLC...")
        while True:
            try:
                logger.debug("Проверка подключения к PLC...")
                if not plc_1.Is_Connected:
                    logger.info("Подключение к PLC...")
                    await asyncio.to_thread(plc_1.run)
                    logger.info(f"Статус подключения: {plc_1.Is_Connected}")

                await asyncio.sleep(0.5)

                if plc_1.Is_Connected:
                    self.start_background_tasks()
                else:
                    # Если не подключились, ждём перед следующей попыткой
                    await asyncio.sleep(5)
                    continue

            except Exception as e:
                logger.error(f"Ошибка в фоновом опросе PLC: {e}")
                await asyncio.sleep(5)

    def start_background_tasks(self):
        """Запуск фоновых задач"""
        if self.poll_task is None or self.poll_task.done():
            self.poll_task = asyncio.create_task(self.fetch_data())
        if self.buffer_task is None or self.buffer_task.done():
            self.buffer_task = asyncio.create_task(self.periodic_buffer_save())
        if self.message_task is None or self.message_task.done():
            self.message_task = asyncio.create_task(self.message_clock())

    async def fetch_data(self):
        while True:
            try:
                data = await asyncio.to_thread(var_list.list_json_with_Unit)
                await asyncio.sleep(0.5)
            except Exception as e:
                logger.error(f"Ошибка опроса данных из PLC: {e}")
                await asyncio.sleep(1)

    async def periodic_buffer_save(self):
        while True:
            try:
                await save_to_buffer()
                await asyncio.sleep(60)
            except asyncio.CancelledError:
                logger.info("Задача сохранения в буфер отменена")
                break
            except Exception as e:
                logger.error(f"Ошибка в периодическом сохранении в буфер: {e}")
                await asyncio.sleep(60)

    async def message_clock(self):
        await asyncio.sleep(1)
        try:
            variable = var_list.get_variable_by_ID(24)
            if variable is None:
                logger.error("Переменная Error1 не найдена")
                return
            current_value = variable.AsInt()
            logger.info(f"Начальное значение Error1: {current_value}")
        except Exception as e:
            logger.error(f"Ошибка при получении начального значения Error1: {e}")

        while True:
            try:
                variable = var_list.get_variable_by_ID(24)
                if variable is None:
                    await asyncio.sleep(5)
                    continue
                new_value = variable.AsInt()
                if new_value != current_value:
                    result = message_handler.error_handling(data_message, variable)
                    records_to_create = []
                    for res in result:
                        records_to_create.append(
                            Message(
                                id_message=res[0],
                                message=res[1],
                                timestamp=timezone.now()
                            )
                )
                await sync_to_async(Message.objects.bulk_create)(records_to_create)
                current_value = new_value
                await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"Ошибка сохранения сообщений: {e}")
                await asyncio.sleep(60)

async def save_to_buffer():
    try:
        if plc_1.Is_Connected:
            for var in var_list.vars:
                if var.is_archive:
                    plc_buffer.put([var.ID, float(var.value), timezone.now()])
            if plc_buffer.full():
                logger.warning("Буфер переполнен. Отбрасываем новые данные.")
                await flush_buffer_to_db()
    except Exception as e:
        logger.error(f"Ошибка данных из PLC: {e}")

async def flush_buffer_to_db():
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
    async def connect(self):
        await self.accept()
        logger.info("WebSocket подключён")

        # Попытка подключиться к OPC UA до запуска цикла
        try:
            plc_1.run()
            logger.info("Подключено к OPC UA серверу")
        except Exception as e:
            logger.error(f"Ошибка подключения к OPC UA: {e}")
            await self.close()
            return
        # Запуск периодического опроса
        self.task = asyncio.create_task(self.fetch_data())
        # Запускаем поток периодического сохранения
        self.task_buffer = asyncio.create_task(self.periodic_buffer_save())
        # Запускаем поток формирование списка сообщений

        self.message_buffer = asyncio.create_task(self.message_clock())

    async def disconnect(self, close_code):
        logger.info(f"WebSocket закрыт. Код: {close_code}")
        if self.task:
            self.task.cancel()
        if self.task_buffer:
            self.task_buffer.cancel()  # Отмена задачи буфера
        if self.message_buffer:
            self.message_buffer.cancel()  # Отмена задачи буфера
        if plc_1.Is_Connected:
            await asyncio.to_thread(plc_1.disconnect)

    async def fetch_data(self):
        while True:
            try:
                data = await asyncio.to_thread(var_list.list_json_with_Unit)
                await self.send(data)
                await asyncio.sleep(0.5)
            except Exception as e:
                logger.error(f"Ошибка данных: {e}")
                await asyncio.sleep(1)  # Пауза перед повторной попыткой

    async def receive(self, text_data=None, bytes_data=None):
        """
        Обрабатывает входящие сообщения от WebSocket-клиента.
        Поддерживает текстовые и байтовые сообщения.
        """
        try:
            if text_data:
                await self.handle_text_message(text_data)
            elif bytes_data:
                await self.handle_bytes_message(bytes_data)
        except Exception as e:
            logger.error(f"Ошибка обработки сообщения: {e}")
            await self.close(code=4000)  # Закрываем с пользовательским кодом

    async def handle_text_message(self, message: str):
        """
        Обработка текстового сообщения.
        Пример: клиент может отправить команду для OPC UA.
        """
        logger.info(f"Получено текстовое сообщение: {message}")
        # Пример логики: если сообщение — команда, выполняем действие
        if (json.loads(message)).get("action") == "regulswitch":
            try:
                # Выполняем чтение данных из PLC (в отдельном потоке)
                toogle()
            except Exception as e:
                logger.error(f"Ошибка чтения данных из PLC: {e}")
                await self.send(text_data=f'{{"error": "Не удалось прочитать данные: {e}"}}')

        elif (json.loads(message)).get("action") == "setpoint":
            try:
                set_point = int((json.loads(message)).get("value"))
                write(set_point, "SP_Regule")
            except Exception as e:
                logger.error(f"Ошибка чтения данных из PLC: {e}")
                await self.send(text_data=f'{{"error": "Не удалось прочитать данные: {e}"}}')
        elif (json.loads(message)).get("action") == "recipe":
            try:
                id_recipe = int((json.loads(message)).get("ID"))


                recipe = await sync_to_async(Recipe.objects.get)(pk=id_recipe)

                recipe_save(recipe)

            except Exception as e:
                logger.error(f"Ошибка чтения данных из PLC: {e}")
                await self.send(text_data=f'{{"error": "Не удалось прочитать данные: {e}"}}')

    async def handle_bytes_message(self, data: bytes):
        """
        Обработка байтового сообщения.
        Можно использовать для передачи бинарных данных (например, файлов).
        """
        logger.info(f"Получено байтовое сообщение длиной {len(data)} байт")
        # Здесь можно добавить логику обработки бинарных данных
        # Например, сохранение в файл или передачу в OPC UA
        await self.send(bytes_data=b"Received " + data)

    async def periodic_buffer_save(self):
        """Периодически сохраняет данные в буфер раз в 60 секунд.
            Если размер больше допустимого, сохраняем в модель
        """
        while True:
            try:
                await save_to_buffer()
                await asyncio.sleep(60)  # 60 секунд

            except asyncio.CancelledError:
                logger.info("Задача сохранения в буфер отменена")
                break
            except Exception as e:
                logger.error(f"Ошибка в периодическом сохранении в буфер: {e}")
                await asyncio.sleep(60)  #

    async def message_clock(self):

        await asyncio.sleep(1)

        try:
            variable = var_list.get_variable_by_ID(24)
            if variable is None:
                logger.info(f"Ошибка")

            current_value = variable.AsInt()

            logger.info(f"Начальное значение Error1: {current_value}")

        except Exception as e:
            logger.error(
                f"Ошибка при получении начального значения Error1: {e}")

        while True:

            try:
                variable = var_list.get_variable_by_ID(24)

                if variable is None:
                    logger.info(f"Ошибка")
                    await asyncio.sleep(5)
                    continue

                new_value = variable.AsInt()

                if new_value != current_value:
                    """ делаем здесь, что надо"""
                    result = message_handler.error_handling(
                        data_message, variable)
                    records_to_create = []
                    for res in result:
                        records_to_create.append(
                            Message(
                                id_message=res[0],
                                message=res[1],
                                timestamp=timezone.now()
                            )
                        )
                    # Сохраняем в БД
                    await sync_to_async(Message.objects.bulk_create)(records_to_create)
                    current_value = new_value
                    # сохраняем в модель

                await asyncio.sleep(1)

            except Exception as e:
                logger.error(f"Ошибка сохранения сообщений: {e}")
                await asyncio.sleep(60)  #