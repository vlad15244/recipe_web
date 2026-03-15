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
    

# количество переменных, которые архивируются

ARCHIVE_BUFFER = 5
SECONDS_BETWEEN_SAVE = 30

counter = 0

for var in var_list.vars:
    if var.is_archive:
        counter += 1

# Буфер для архива — используем asyncio.Queue - размер должен быть кратен кол-ву переменных с архивом 
plc_buffer = asyncio.Queue(maxsize=counter*ARCHIVE_BUFFER)

class OpcRuntime:
    def __init__(self):
        self.poll_task = None
        self.buffer_task = None
        self.message_task = None
        self.running = True  # Флаг для остановки

    def start_background_tasks(self):

        """Запуск фоновых задач"""
        if self.buffer_task is None or self.buffer_task.done():
            print("Start save buffer trends")
            self.buffer_task = asyncio.create_task(self.periodic_buffer_save())
        if self.message_task is None or self.message_task.done():
            self.message_task = asyncio.create_task(self.message_clock())
        

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

    async def stop(self):
        """Остановка всех фоновых задач"""
        self.running = False
        if self.buffer_task:
            self.buffer_task.cancel()
            try:
                await self.buffer_task
            except asyncio.CancelledError:
                pass

    async def periodic_buffer_save(self):
        while self.running:
            try:
                if plc_1.Is_Connected:


                    if not plc_buffer.full():
                        for var in var_list.vars:
                            if var.is_archive:
                                await plc_buffer.put([var.ID, float(var.value), timezone.now()])

                    if plc_buffer.qsize() >= counter*ARCHIVE_BUFFER:
                        

                        buffer_items = []
                        while not plc_buffer.empty():
                            buffer_items.append(await plc_buffer.get())
                            print(buffer_items)
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
                        print(f"Сохранено {len(records_to_create)} записей в БД.")                         

                await asyncio.sleep(SECONDS_BETWEEN_SAVE)

            except asyncio.CancelledError:
                logger.info("Задача сохранения в буфер отменена")
                break
            except Exception as e:
                logger.error(f"Ошибка в периодическом сохранении в буфер: {e}")
                await asyncio.sleep(60)  

    async def message_clock(self):
        await asyncio.sleep(5)
        try:
            variable = var_list.get_variable_by_ID(24)
            if variable is None:
                logger.error("Переменная Error1 не найдена")
                return
            current_value = variable.AsInt()
            logger.info(f"Начальное значение Error1: {current_value}")
        except Exception as e:
            logger.error(f"Ошибка при получении начального значения Error1: {e}")
            return
        
        while self.running:
            try:
                if plc_1.Is_Connected:
                    variable = var_list.get_variable_by_ID(24)
                if variable is None:
                    await asyncio.sleep(5)
                    continue

                result = None
                
                new_value = variable.AsInt()
                records_to_create = []
                if new_value != current_value:
                    result = message_handler.error_handling(data_message, variable)
                # Проверка на пустой результат
                if result:
                    for res in result:
                        records_to_create.append(
                            Message(
                                id_message=res[0],
                                message=res[1],
                    timestamp=timezone.now())) 
                current_value = new_value

            # Вызываем bulk_create только если есть записи
                if records_to_create:
                    await sync_to_async(Message.objects.bulk_create)(records_to_create)

                await asyncio.sleep(1)                                      

            except asyncio.CancelledError:
                logger.info("Задача message_clock отменена")
                break
            except Exception as e:
                logger.error(f"Ошибка сохранения сообщений: {e}")
                await asyncio.sleep(60)



class OpcUaConsumer(AsyncWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.data_task = None
        self._is_connected = False  # Флаг состояния соединения

    async def connect(self):
        await self.accept()
        self._is_connected = True  # Устанавливаем флаг при подключении
        logger.info("WebSocket подключён")

        # Попытка подключиться к OPC UA
        try:
            logger.info("Подключено к OPC UA серверу")
            # Здесь должен быть код подключения к OPC UA
        except Exception as e:
            logger.error(f"Ошибка подключения к OPC UA: {e}")
            await self.close()
            self._is_connected = False
            return

        # Запускаем фоновую задачу только если подключение успешно
        self.data_task = asyncio.create_task(self.fetch_data())

    async def disconnect(self, close_code):
        self._is_connected = False  # Сбрасываем флаг
        logger.info(f"WebSocket закрыт. Код: {close_code}")

        # Корректно останавливаем фоновую задачу
        if self.data_task and not self.data_task.done():
            self.data_task.cancel()
            try:
                await self.data_task
            except asyncio.CancelledError:
                logger.info("Фоновая задача fetch_data отменена")

    async def fetch_data(self):
        while self._is_connected:  # Проверяем статус соединения на каждой итерации
            try:
                data = await asyncio.to_thread(var_list.list_json_with_Unit)
                # Дополнительная проверка: отправляем данные только если соединение активно
                if self._is_connected:
                    await self.send(text_data=data)
                await asyncio.sleep(0.5)
            except asyncio.CancelledError:
                # Задача была отменена — корректно завершаем работу
                logger.info("Задача fetch_data была отменена")
                break
            except Exception as e:
                logger.error(f"Ошибка получения данных: {e}")
                # Если соединение разорвано, выходим из цикла
                if not self._is_connected:
                    break
                await asyncio.sleep(1)  # Пауза перед повторной попыткой

# Инициализация глобального экземпляра OpcRuntime
opc_runtime = OpcRuntime()

# Функция для запуска фоновых задач (может вызываться при старте Django)
async def start_opc_runtime():
    """Запуск фоновых задач OPC UA"""
    await opc_runtime.start()