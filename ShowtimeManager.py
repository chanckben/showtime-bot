# Manages all scrapers and receives requests from frontend

from Scrapers.CathayScraper import CathayScraper
from DatabaseManager import DatabaseManager
import datetime
import json
import os
from os.path import dirname
from selenium import webdriver

class ShowtimeManager:
    def __init__(self):
        # Constants
        self.GOOGLE_CHROME_PATH = '/app/.apt/usr/bin/google_chrome'
        self.CHROMEDRIVER_PATH = os.path.join(dirname(dirname(dirname(os.path.abspath(__file__)))), "Drivers", "chromedriver.exe")
        # Scrapers
        self.scrapers = []
        self.scrapers.append(CathayScraper())
        self.provider_id_to_scraper = dict((scraper.get_provider_id(), scraper.__class__) for scraper in self.scrapers)
        # Database
        self.db_manager = DatabaseManager()

    def init_webdriver(self):
        # Initialise Selenium webdriver
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--no-sandbox')
        #chrome_options.add_argument('--headless') # Added
        self.browser = webdriver.Chrome(executable_path=self.CHROMEDRIVER_PATH, options=chrome_options)

    # To be done at a fixed time every day
    def start_scraping(self):
        if os.path.exists('./db_data.json') and os.path.exists('./movie_id_to_title.json') and os.path.exists('./movie_title_to_id.json') and os.path.exists('./cinema_id_to_name.json'):
            self.db_manager.db = json.load(open('db_data.json'))
            self.db_manager.movie_id_to_title = json.load(open('movie_id_to_title.json'))
            self.db_manager.movie_title_to_id = json.load(open('movie_title_to_id.json'))
            self.db_manager.cinema_id_to_name = json.load(open('cinema_id_to_name.json'))
        else:
            for scraper in self.scrapers:
                scraped_result = scraper.scrape(self.browser)
                # Save scraped results in database
                self.db_manager.save_df_to_db(scraped_result, scraper.get_provider_id())
                self.db_manager.save_cinema_id_to_name(scraper.get_cinema_id_to_name(), scraper.get_provider_id())

    def get_movies(self):
        return self.db_manager.get_movies()

    def get_sorted_movies(self):
        return sorted(list(map(lambda movie_id: self.db_manager.get_movie_title(movie_id), self.db_manager.get_movies())))

    def get_movie_title(self, movie_id):
        return self.db_manager.get_movie_title(movie_id)

    def get_movie_dates(self, movie_id):
        result = []
        for id, date in self.db_manager.get_deserialized_keys():
            if id == movie_id and date >= datetime.date.today():
                result.append(date)
        return result

    def get_showtimes(self, movie_id, date, provider_id=None, cinema_id=None):
        showtimes = self.db_manager.get_val(movie_id, date)
        if provider_id and cinema_id:
            return showtimes[(showtimes["Provider"] == provider_id) & (showtimes["Cinema"] == cinema_id)]["Time"].values.tolist()

        showtimes_dict = {}
        for provider, cinema_time_df in showtimes.groupby("Provider"):
            showtimes_dict[provider] = {}
            for cinema, time_df in cinema_time_df.groupby("Cinema"):
                showtimes_dict[provider][cinema] = time_df["Time"].values.tolist()

        return showtimes_dict

    def get_booking_link(self, movie_id, date, provider_id, cinema_id, time):
        showtimes = self.db_manager.get_val(movie_id, date)
        session_id = showtimes[(showtimes["Provider"] == provider_id) & (showtimes["Cinema"] == cinema_id) & (showtimes["Time"] == time)]["SessionID"].values[0]
        booking_link = self.provider_id_to_scraper[provider_id].get_booking_link(cinema_id, session_id)
        return booking_link

    def get_cinema_name(self, cinema_id, provider_id):
        return self.db_manager.get_cinema_name(cinema_id, provider_id)

    def get_provider_name(self, provider_id):
        return self.provider_id_to_scraper[provider_id].get_provider_name()