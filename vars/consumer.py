from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from opcua import Client
import asyncio
import json
from datetime import datetime
import logging
import os
from .import opc_config

from .models import Recipe


# Должно появиться в консоли при запуске сервера
print("consumer module loaded!")
logger = logging.getLogger(__name__)

plc_1 = opc_config.PLC('192.168.20.50', '4840')
var_list = opc_config.VariableList()

file_path = os.path.join(os.path.dirname(__file__), "config.json")

with open(file_path, "r", encoding='utf-8') as f:
    data = json.load(f)

for dt in data:
    var_list.add(opc_config.VariablePLC(
        dt["name"], f'{opc_config.ADR}.{dt["opc_adr"]}', plc_1, dt["scale"], dt["ID"]))


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

    async def disconnect(self, close_code):
        logger.info(f"WebSocket закрыт. Код: {close_code}")
        if self.task:
            self.task.cancel()
        if plc_1.Is_Connected:
            await asyncio.to_thread(plc_1.disconnect)

    async def fetch_data(self):
        while True:
            try:
                data = await asyncio.to_thread(var_list.list_json_with_Unit)
                await self.send(data)
                await asyncio.sleep(0.05)
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
                content = await sync_to_async(Recipe.objects.get)(pk=id_recipe)
                print(content)
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
