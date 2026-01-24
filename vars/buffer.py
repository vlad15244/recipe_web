from datetime import datetime

class Buffer:

    def __init__(self, id, value):
        self.id = id
        self.value = value
        self.timestamp = datetime.now().isoformat()

    def to_dict(self):
        return {
            "var_id": self.id,
            "value": self.value,
            "timestamp": self.timestamp
        }
    def __repr__(self):
        return f"{self.id} - {self.Value} - {self.timestamp}"   
       

