import psycopg2
from Database.config import config
import datetime
import pandas as pd

class DatabaseManager:
    def __init__(self):
        self.conn = None
        self.cur = None
        try:
            # read connection parameters
            params = config(filename='./Database/database.ini')

            # connect to the PostgreSQL server
            print('Connecting to the PostgreSQL database...')
            conn = psycopg2.connect(**params)
            
            # create a cursor
            self.cur = conn.cursor()

            # enable case-insensitive text extension
            self.cur.execute('CREATE EXTENSION IF NOT EXISTS citext;')

            # create tables
            self.cur.execute('CREATE TABLE showtimes (movie_id INTEGER NOT NULL, provider_id VARCHAR(2) NOT NULL, cinema_id VARCHAR(10) NOT NULL, session_id VARCHAR(30) NOT NULL, showtime TIMESTAMP NOT NULL);')
            self.cur.execute('CREATE TABLE movie_id_to_title (movie_id SERIAL PRIMARY KEY, movie_title CITEXT UNIQUE);')
            self.cur.execute('CREATE TABLE cinema_id_to_name (provider_id VARCHAR(2) NOT NULL, cinema_id VARCHAR(10) NOT NULL, cinema_name VARCHAR(100) NOT NULL);')
        
        except (Exception, psycopg2.DatabaseError) as error:
            print(error)

    def close_conn(self):
        if self.cur:
            self.cur.close()
            print('Database cursor closed.')
        if self.conn:
            self.conn.close()
            print('Database connection closed.')

    def save_df_to_db(self, df, provider_id):
        records = df.to_dict('records')
        movies = df["Movie"].unique().tolist()
        for movie in movies:
            # Only insert movie if the title is distinct from existing titles (enforced by UNIQUE condition)
            self.cur.execute('INSERT INTO movie_id_to_title (movie_title) VALUES (%s) ON CONFLICT DO NOTHING;', (movie,))
        self.cur.execute('SELECT * FROM movie_id_to_title;')
        movie_title_to_id = dict((y.lower(),x) for x, y in self.cur.fetchall())
        for record in records:
            self.cur.execute('INSERT INTO showtimes (movie_id, provider_id, cinema_id, session_id, showtime) VALUES (%s, %s, %s, %s, %s);',
                (movie_title_to_id[record["Movie"].lower()], provider_id, record["Cinema"], record["SessionID"], record["Time"]))

    def save_cinema_id_to_name(self, cinema_id_to_name, provider_id):
        for cinema_id, cinema_name in cinema_id_to_name.items():
            self.cur.execute('INSERT INTO cinema_id_to_name (provider_id, cinema_id, cinema_name) VALUES (%s, %s, %s);', (provider_id, cinema_id, cinema_name))

    # movie_id_to_title getters

    def get_movie_ids(self):
        self.cur.execute('SELECT movie_id FROM movie_id_to_title;')
        return list(movie[0] for movie in self.cur.fetchall())

    def get_movie_titles(self):
        self.cur.execute('SELECT movie_title FROM movie_id_to_title;')
        return list(movie[0] for movie in self.cur.fetchall())

    def get_movie_title(self, movie_id):
        self.cur.execute('SELECT movie_title FROM movie_id_to_title WHERE movie_id = %s;', (movie_id,))
        return self.cur.fetchone()[0]

    # cinema_id_to_name getters

    def get_cinema_name(self, cinema_id, provider_id):
        self.cur.execute('SELECT cinema_name FROM cinema_id_to_name WHERE provider_id = %s AND cinema_id = %s;', (provider_id, cinema_id))
        return self.cur.fetchone()[0]

    # showtimes getters

    def get_movie_dates(self, movie_id):
        self.cur.execute('SELECT showtime::DATE FROM showtimes WHERE movie_id = %s AND showtime::DATE >= %s;', (movie_id, datetime.datetime.today()))
        dates = self.cur.fetchall()
        return sorted(set(x[0] for x in dates))

    def get_showtimes(self, movie_id, date):
        self.cur.execute('SELECT provider_id, cinema_id, showtime::TIME FROM showtimes WHERE movie_id = %s AND showtime::DATE = %s;', (movie_id, date))
        output = self.cur.fetchall()
        return pd.DataFrame(output, columns=["Provider", "Cinema", "Time"])

    def get_cinema_showtimes(self, movie_id, date, provider_id, cinema_id):
        self.cur.execute('SELECT showtime::TIME FROM showtimes WHERE movie_id = %s AND provider_id = %s AND cinema_id = %s AND showtime::DATE = %s;', (movie_id, provider_id, cinema_id, date))
        return sorted(time[0] for time in self.cur.fetchall())

    def get_session_id(self, movie_id, provider_id, cinema_id, dt):
        self.cur.execute('SELECT session_id FROM showtimes WHERE movie_id = %s AND provider_id = %s AND cinema_id = %s AND showtime = %s;', (movie_id, provider_id, cinema_id, dt))
        return self.cur.fetchone()[0]
