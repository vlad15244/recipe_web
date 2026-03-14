import asyncio
import logging
from asgiref.sync import sync_to_async
from datetime import datetime
from django.utils import timezone
import json
import os
from channels.generic.websocket import AsyncWebsocketConsumer

from . import opc_config, message_handler
from .models import Trends, Message, Recipe

logger = logging.getLogger(__name__)

# Буфер для архива — используем asyncio.Queue
plc_buffer = asyncio.Queue(maxsize=5)

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
        self.running = True  # Флаг для остановки

    def start_background_tasks(self):

        """Запуск фоновых задач"""

    async def start(self):
        logger.info("Запуск фонового опроса PLC...")
        while self.running:
            try:
                logger.debug("Проверка подключения к PLC...")
                if not plc_1.Is_Connected:
                    logger.info("Подключение к PLC...")
                    plc_1._attemmpt_coonection()
                    

                if plc_1.Is_Connected:
                    await asyncio.to_thread(plc_1.run)
                    self.start_background_tasks()
                else:
                    # Если не подключились, ждём перед следующей попыткой
                    await asyncio.sleep(5)
                    continue

            except Exception as e:
                logger.error(f"Ошибка в фоновом опросе PLC: {e}")
                await asyncio.sleep(5)    

class OpcUaConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()
        logger.info("WebSocket подключён")

        self.data_task = asyncio.create_task(self.fetch_data())

        # Попытка подключиться к OPC UA до запуска цикла
        try:
            logger.info("Подключено к OPC UA серверу")
        except Exception as e:
            logger.error(f"Ошибка подключения к OPC UA: {e}")
            await self.close()
            return

    async def disconnect(self, close_code):
        logger.info(f"WebSocket закрыт. Код: {close_code}")

    async def fetch_data(self):
        while True:
            try:
                data = await asyncio.to_thread(var_list.list_json_with_Unit)
                await self.send(text_data=json.dumps(data))
                await asyncio.sleep(0.5)
            except Exception as e:
                logger.error(f"Ошибка получения данных: {e}")
                await asyncio.sleep(1)  # Пауза перед повторной попыткой

# Инициализация глобального экземпляра OpcRuntime
opc_runtime = OpcRuntime()

# Функция для запуска фоновых задач (может вызываться при старте Django)
async def start_opc_runtime():
    """Запуск фоновых задач OPC UA"""
    await opc_runtime.start()