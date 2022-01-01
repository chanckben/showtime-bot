from Scrapers.Structs.Cinema import Cinema
from Scrapers.Structs.Movie import Movie
from Scrapers.Structs.Showtime import Showtime
from datetime import time, datetime
import pandas as pd
import re
from time import sleep


class CathayScraper:
    def __init__(self):
        self.movie_id_to_title = {}
        self.cinema_id_to_name = {}

    def parse_movie_title(self, raw_movie_title, movie_id):
        # Assumption: Raw movie titles are of the format <MovieTitle> <Rating> with an optional asterisk (*)
        pattern = r'^([\s\S]+)\s(R21|M18|NC16|PG13|PG|G){1}(\s[*])?$'
        title_groups = re.match(pattern, raw_movie_title).groups()
        self.movie_id_to_title[movie_id] = title_groups[0]
        return Movie(title_groups[0], title_groups[1], movie_id)

    # Cleans a cinema name and returns a Cinema object
    def parse_cinema_name(self, raw_cinema_name, cinema_id):
        # Assumption: Raw cinema names are already clean
        self.cinema_id_to_name[cinema_id] = raw_cinema_name
        return Cinema(raw_cinema_name, cinema_id)

    def scrape(self, browser):
        select_movie_dropdown_xpath = '/html/body/div/form/div/div/div[8]/div[1]/select'
        select_cinema_dropdown_xpath = '/html/body/div/form/div/div/div[8]/div[2]/select'
        select_date_dropdown_xpath = '/html/body/div/form/div/div/div[8]/div[3]/select'
        select_time_dropdown_xpath = '/html/body/div/form/div/div/div[8]/div[4]/select'

        browser.get("https://www.cathaycineplexes.com.sg/movies/")

        movie_titles_html = browser.find_elements_by_xpath(select_movie_dropdown_xpath + '/*')[1:]

        output = []
        for movie_choice in movie_titles_html:
            movie_choice.click()
            movie_object = self.parse_movie_title(movie_choice.text, movie_choice.get_attribute("value"))
            sleep(2)
            cinema_names_html = browser.find_elements_by_xpath(select_cinema_dropdown_xpath + '/*')[1:]
            for cinema_choice in cinema_names_html:
                cinema_choice.click()
                cinema_object = self.parse_cinema_name(cinema_choice.text, cinema_choice.get_attribute("value"))
                sleep(2)
                dates_html = browser.find_elements_by_xpath(select_date_dropdown_xpath + '/*')[1:]
                for date_choice in dates_html:
                    date_choice.click()
                    session_date = date_choice.get_attribute("value").split(' ')[0]
                    session_date = datetime.strptime(session_date, "%d/%m/%Y").date()
                    sleep(2)
                    times_html = browser.find_elements_by_xpath(select_time_dropdown_xpath + '/*')[1:]
                    for time_choice in times_html:
                        session_id = time_choice.get_attribute("value")
                        session_time = time_choice.text.split(' ')[0]
                        session_time = time.fromisoformat(session_time)
                        timestamp = datetime.combine(session_date, session_time)
                        output.append(Showtime(movie_object, cinema_object, timestamp, session_id))

        output = pd.DataFrame(output, columns=['Object'])
        output['Movie'] = output['Object'].apply(lambda showtime: showtime.get_movie().get_title())
        output['Cinema'] = output['Object'].apply(lambda showtime: showtime.get_cinema().get_id())
        output['Time'] = output['Object'].apply(lambda showtime: showtime.get_session_time())
        output['SessionID'] = output['Object'].apply(lambda showtime: showtime.get_session_id())
        return output

    def get_movie_id_to_title(self):
        return self.movie_id_to_title

    def get_cinema_id_to_name(self):
        return self.cinema_id_to_name

    def get_provider_id(self):
        return "CA"

    @staticmethod
    def get_provider_name():
        return "Cathay"

    @staticmethod
    def get_booking_link(cinema_id, session_id):
        return f"https://booking.cathaycineplexes.com.sg/Ticketing/visSelectSeats.aspx?cinemacode={cinema_id}&txtSessionId={session_id}&visLang=1"
