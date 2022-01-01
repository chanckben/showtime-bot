class Showtime:
    def __init__(self, movie, cinema, session_time, session_id):
        self.movie = movie
        self.cinema = cinema
        self.session_time = session_time
        self.session_id = session_id

    def __repr__(self):
        return f"Showtime({self.movie.get_title()}, {self.cinema.get_name()}, {self.session_time})"

    def get_movie(self):
        return self.movie

    def get_cinema(self):
        return self.cinema

    def get_session_time(self):
        return self.session_time

    def get_session_id(self):
        return self.session_id