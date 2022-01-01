class Movie:
    def __init__(self, title, rating, id):
        self.title = title
        self.age_rating = rating if self.is_valid_rating(rating) else None
        self.movie_id = id

    def __repr__(self):
        return f"Movie({self.title}, {self.age_rating}, {self.movie_id})"

    def __eq__(self, other):
        return self.movie_id == other.movie_id

    def is_valid_rating(self, rating):
        valid_ratings = ["G", "PG", "PG13", "NC16", "M18", "R21"]
        return rating in valid_ratings

    def get_title(self):
        return self.title

    def get_age_rating(self):
        return self.age_rating

    def get_id(self):
        return self.movie_id
