class Cinema:
    def __init__(self, name, id):
        self.cinema_name = name
        self.cinema_id = id

    def __repr__(self):
        return f"Cinema({self.cinema_name}, {self.cinema_id})"

    def __eq__(self, other):
        return self.cinema_id == other.cinema_id

    def get_name(self):
        return self.cinema_name

    def get_id(self):
        return self.cinema_id