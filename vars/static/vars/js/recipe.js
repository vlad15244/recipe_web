const table = document.querySelector('.recipe-table');
const socket = new WebSocket('ws://localhost:8001/ws/opcua/');

table.addEventListener('click', function(event) {
    // Проверяем, что кликнули именно по ячейке
    if (event.target.tagName === 'TD') {
        const cell = event.target; // Кликнутая ячейка
        const row = cell.closest('tr'); // Родительская строка
        const rowIndex = row.rowIndex; // Индекс строки
        const cellIndex = cell.cellIndex; // Индекс ячейки
        const cellContent = cell.textContent; // Содержимое ячейки

        const ID = row.cells[0].textContent;

        recipe_save(ID, socket);
        console.log(`Клик по ячейке: Строка ${rowIndex}, Столбец ${cellIndex}, Содержимое: ${cellContent}`);
        // Здесь ваша логика (например, переход по ссылке, открытие модального окна)
    }
});

function recipe_save(data, socket) {
  if (!socket || socket.readyState !== WebSocket.OPEN) {
    console.error('WebSocket соединение не установлено');
    return;
  }

  const command = {
    action: "recipe",
    ID: Number(data)
  };
  socket.send(JSON.stringify(command));
}

window.addEventListener('beforeunload', () => {
  socket.close();
});


