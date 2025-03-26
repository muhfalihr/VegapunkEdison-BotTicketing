class TempStorage:
    def __init__(self):
        self.store = {}

    def get(self, key, default=None):
        return self.store.get(key, default)

    def set(self, key, value):
        self.store[key] = value

    def update(self, data):
        if isinstance(data, dict):
            self.store.update(data)
    
    def clear(self):
        self.store.clear()

class Store:
    def __init__(self):
        self.temp = TempStorage()

    def __getitem__(self, key):
        return self.temp.get(key)

    def __setitem__(self, key, value):
        self.temp.set(key, value)

    def tempstore(self, key, value):
        self.temp.set(key, value)

    def jsontempstore(self, data):
        self.temp.update(data)

    def cleartemp(self):
        self.temp.clear()