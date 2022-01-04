import datetime
import json
import pandas as pd

class DatabaseManager:
    def __init__(self):
        # Database is dictionary for local testing, Redis db for production
        self.db = {}
        self.movie_id_to_title = {}
        self.movie_title_to_id = {}
        self.cinema_id_to_name = {}

    # Serialization and deserialization

    def serialize_db_key(self, movie_id, date):
        return f"{movie_id}|{date}"

    def serialize_db_val(self, provider_id, cinema_id, time, session_id):
        return f"{provider_id}|{cinema_id}|{time}|{session_id}"

    def deserialize_db_key(self, key):
        movie_id, date = key.split('|')
        return (movie_id, datetime.date.fromisoformat(date))

    def deserialize_db_val(self, val):
        provider_id, cinema_id, time, session_id = val.split('|')
        return (provider_id, cinema_id, time, session_id)

    def get_deserialized_keys(self):
        return list(map(lambda key: self.deserialize_db_key(key), self.db.keys()))

    # Showtime dataframe methods

    def save_df_to_db(self, df, provider_id):
        # Each key-value pair will be of the following format
        # Key: Movie_ID|Date(YYYY-MM-DD) (e.g. HO00001704|2021-12-28)
        # Value: Provider_ID|Cinema_ID|Time (e.g. CA|1110|22:00)
        temp_dict = {}
        for index, row in df.iterrows():
            movie_name = row['Movie']
            cinema_id = row['Cinema']
            date = str(row["Time"].date())
            time = "{:d}:{:02d}".format(row["Time"].hour, row["Time"].minute)
            session_id = row['SessionID']

            # Convert movie name to internal movie ID
            if movie_name not in self.movie_title_to_id:
                idx = len(self.movie_title_to_id) + 1
                self.movie_title_to_id[movie_name] = f"M{idx}" # HLEN, HSET
                self.movie_id_to_title[f"M{idx}"] = movie_name
            movie_id = self.movie_title_to_id[movie_name] # HGET

            key = self.serialize_db_key(movie_id, date)
            value = self.serialize_db_val(provider_id, cinema_id, time, session_id)
            if key in temp_dict:
                temp_dict[key].append(value)
            else:
                temp_dict[key] = [value]

        print(temp_dict)
        for key, value in temp_dict.items():
            if key in self.db:
                value = json.loads(self.db[key]) + value
            self.db[key] = json.dumps(value)
        with open('db_data.json', 'w') as f:
            json.dump(self.db, f)
            f.close()
        with open('movie_id_to_title.json', 'w') as f:
            json.dump(self.movie_id_to_title, f)
            f.close()
        with open('movie_title_to_id.json', 'w') as f:
            json.dump(self.movie_title_to_id, f)
            f.close()

    # Returns the value corresponding to key
    def get_val(self, movie_id, date):
        serialized_key = self.serialize_db_key(movie_id, date)
        val = json.loads(self.db[serialized_key]) # What if key does not exist?
        result = list(map(lambda ele: self.deserialize_db_val(ele), val))
        return pd.DataFrame(result, columns=["Provider", "Cinema", "Time", "SessionID"])

    # Movie ID to movie title methods

    def get_movies(self):
        # HKEYS in Redis
        return list(self.movie_id_to_title.keys())

    def get_movie_title(self, movie_id):
        # HGET in Redis
        return self.movie_id_to_title[movie_id]

    # Cinema ID to cinema name methods

    def save_cinema_id_to_name(self, cinema_id_to_name, provider_id):
        # HSET in Redis
        self.cinema_id_to_name[provider_id] = cinema_id_to_name
        with open('cinema_id_to_name.json', 'w') as f:
            json.dump(self.cinema_id_to_name, f)
            f.close()

    def get_cinema_name(self, cinema_id, provider_id):
        # HGET in Redis
        return self.cinema_id_to_name[provider_id][cinema_id]
