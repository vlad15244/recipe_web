
def error_handling(data : list, plc_var) -> list:
    for dt in data:
        result = []
        if dt["plc_value"] == plc_var.name:
            if dt["by_value"]: #Если стоит только по значению
                for txt in dt["text"]:
                    if txt["value"] == plc_var.value:
                        result.append(dt["message_id"])
                        result.append(txt["message"])
            else: #по битам
                bit_mask = format(plc_var.value, '032b')[::-1] #так как надо привести к 32 битам
                bit_counter = 0
                for txt in dt["text"]:
                    buffer = []
                    if txt["value"] == bit_counter and bit_mask[bit_counter] == '1':
                        buffer.append(dt["message_id"])
                        buffer.append(txt["message"])
                        result.append(buffer)
                    bit_counter += 1
    return result
            

if __name__ == "__main__":
    import json
    import os

    file_path = os.path.join(os.path.dirname(__file__), "message.json")
    with open(file_path, "r", encoding='utf-8') as f:
        data = json.load(f)

    print(error_handling(data, 6, "Error1"))
