const table = document.querySelector('.recipe-table');
const socket = new WebSocket('ws://localhost:8001/ws/opcua/');
let ID = 0;

table.addEventListener('click', function(event) {
    // Проверяем, что кликнули именно по ячейке
    if (event.target.tagName === 'TD') {
        const cell = event.target; // Кликнутая ячейка
        const row = cell.closest('tr'); // Родительская строка
        const rowIndex = row.rowIndex; // Индекс строки
        const cellIndex = cell.cellIndex; // Индекс ячейки
        const cellContent = cell.textContent; // Содержимое ячейки
        const url = row.getAttribute('data-id');

        ID = row.cells[0].textContent;
        visible_btn(ID)

        //Кнопка Просмотр
        const btn_show = document.querySelector('.btn_show');
        btn_show.href = String(ID);
        visible_btn_show(ID);
        //recipe_save(ID, socket);
        console.log(`Клик по ячейке: Строка ${rowIndex}, Столбец ${cellIndex}, Содержимое: ${cellContent}`);

    }
});


const saveBtn = document.getElementById('onsave');
saveBtn.addEventListener('click', () => {
  console.log(`Клик ${ID},`);   
   recipe_save(ID, socket)
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

  saveBtn.style.visibility = 'hidden';  
}





function visible_btn(value) {
  const btn = document.getElementById('onsave');
  const Val = Number(value);

  if (!isNaN(Val) && Val > 0){
    btn.style.visibility = 'visible';
  } else
  {
    btn.style.visibility = 'hidden';    
  }

}

function visible_btn_show(value) {
  const btn = document.querySelector('.btn_show');
  const Val = Number(value);

  if (!isNaN(Val) && Val > 0){
    btn.style.visibility = 'visible';
  } else
  {
    btn.style.visibility = 'hidden';    
  }

}


window.addEventListener('beforeunload', () => {
  socket.close();
});

document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('onsave').style.visibility = 'hidden';
    document.querySelector('.btn_show').style.visibility = 'hidden';
});


