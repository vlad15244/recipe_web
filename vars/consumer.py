from channels.generic.websocket import AsyncWebsocketConsumer
from opcua import Client
import asyncio
import json
from datetime import datetime
import logging
import os
from .import opc_config

print("consumer module loaded!")  # Должно появиться в консоли при запуске сервера
logger = logging.getLogger(__name__)

plc_1 = opc_config.PLC('192.168.20.50', '4840')
var_list = opc_config.VariableList()

file_path = os.path.join(os.path.dirname(__file__),"plc", "config.json")

with open(file_path, "r", encoding='utf-8') as f:
    data = json.load(f)

for dt in data:
    var_list.add(opc_config.VariablePLC(dt["name"], f'{opc_config.ADR}.{dt["opc_adr"]}',plc_1,dt["scale"], dt["ID"]))  



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
        if self.client:
            await asyncio.to_thread(self.client.disconnect)

    async def fetch_data(self):
        while True:
            try:
                data = await asyncio.to_thread(var_list.list_json_with_Unit)
                await self.send(data)
                await asyncio.sleep(0.05)
            except Exception as e:
                logger.error(f"Ошибка данных: {e}")
                await asyncio.sleep(1)  # Пауза перед повторной попыткой



