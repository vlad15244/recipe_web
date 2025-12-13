
// Функция: создать/обновить таблицу по данным
function updateTable(data) {
  const container = document.getElementById('table-container');
  const table = document.createElement('table');

  // Шапка таблицы: столбцы PV и SP
  const thead = table.createTHead();
  const headerRow = thead.insertRow();
  headerRow.insertCell().textContent = 'Канал'; // первый столбец — номер канала
  headerRow.insertCell().textContent = 'PV';
  headerRow.insertCell().textContent = 'SP';
  headerRow.insertCell().textContent = 'MV'; 
  headerRow.insertCell().textContent = 'Состояние регулирования';
  table.classList.add('fixed-table-width');

  // Тело таблицы: по строке на канал (1–4)
  for (let channel = 1; channel <= 4; channel++) {
    const row = table.insertRow();

    // Ячейка: номер канала
    const cellChannel = row.insertCell();
    cellChannel.textContent = channel;

    // Ячейка: PV[channel]
    const cellPV = row.insertCell();
    cellPV.textContent = data[`PV${channel}`];

    // Ячейка: SP[channel]
    const cellSP = row.insertCell();
    cellSP.textContent = data[`SP${channel}`];

    // Ячейка: MV[channel]
    const cellMV = row.insertCell();
    cellMV.textContent = data[`MV${channel}`];

    const cellRegul = row.insertCell();
    cellRegul.textContent = formatStatus(data[`eToogle${channel}`]);
    cellRegul.classList.add();
    colorState(data[`eToogle${channel}`], cellRegul);
  }

  // Заменяем содержимое контейнера
  container.innerHTML = '';
  container.appendChild(table);
}

const socket = new WebSocket('ws://localhost:8001/ws/opcua/');

window.socket = socket;

socket.onmessage = function(event) {
  try {
    const data = JSON.parse(event.data);
    console.log('Получены данные:', data);
    updateTable(data);
    btState(data.xRegul);
  } catch (error) {
    console.error('Ошибка парсинга JSON:', error, 'Данные:', event.data);
  }
};

function formatStatus(value) {
  if (typeof value === 'string' && value.includes("False")) {
    return 'Нагрев выключен';
  } else {
    return 'Нагрев включен';
  }
}

function colorState(value, cell) {
  cell.classList.remove('state-false', 'state-true');


    if (typeof value === 'string' && value.includes("False"))
    {
      if (value.includes("False")) {
        cell.classList.add('state-false');
      } else {
        cell.classList.add('state-true');
      }
    }

}

function btState(value) {
  const btn = document.getElementById('onclick');


    if (typeof value === 'string' && value.includes("False"))
    {
      if (value.includes("False")) {
        btn.textContent = 'Включить нагрев';
      } else {
        btn.textContent = 'Выключить нагрев';
      }
    } 


}

socket.onopen = () => {
  console.log('WebSocket: соединение установлено');
  document.getElementById('table-container').innerHTML = '<p>Подключение установлено. Ожидание данных...</p>';
};

socket.onerror = (e) => {
  console.error('WebSocket: ошибка', e);
  document.getElementById('table-container').innerHTML = '<p style="color:red;">Ошибка соединения</p>';
};

socket.onclose = () => {
  console.log('WebSocket: соединение закрыто');
  document.getElementById('table-container').innerHTML = '<p style="color:orange;">Соединение закрыто</p>';
};

window.addEventListener('beforeunload', () => {
  socket.close();
});

function handleClick() {
  if (!socket || socket.readyState !== WebSocket.OPEN) {
    console.error('WebSocket соединение не установлено');
    return;
  }

  const command = {
    action: "regulswitch"
  };
  socket.send(JSON.stringify(command));
}

const input = document.getElementById('setpoint');
input.addEventListener('input', function() {
  const command = {
    action: "setpoint",
    value: Number(this.value)
  };
  window.socket.send(JSON.stringify(command));
});

