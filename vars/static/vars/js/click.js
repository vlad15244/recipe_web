      

  
      const input = document.getElementById('setpoint');
      input.addEventListener('input', function(){
        const command = {
            action: "setpoint",
            value: Number(this.value)
        }
            window.socket.send(JSON.stringify(command));        
      });


            function btState(value){
      const btn = document.getElementById('onclick');

      if (value.includes("False")){
        btn.textContent = 'Включить нагрев';
      }
      else
      {
        btn.textContent = 'Выключить нагрев';        
      }
    }