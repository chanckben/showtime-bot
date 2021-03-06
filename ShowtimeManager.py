# Manages all scrapers and receives requests from frontend

from Scrapers.CathayScraper import CathayScraper
from Scrapers.ShawScraper import ShawScraper
from Database.DatabaseManager import DatabaseManager
import datetime
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
        self.scrapers.append(ShawScraper())
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

    def shutdown(self):
        self.browser.quit()
        self.db_manager.close_conn()

    # To be done at a fixed time every day
    def start_scraping(self):
        '''if os.path.exists('./db_data.json') and os.path.exists('./movie_id_to_title.json') and os.path.exists('./movie_title_to_id.json') and os.path.exists('./cinema_id_to_name.json'):
            self.db_manager.db = json.load(open('db_data.json'))
            self.db_manager.movie_id_to_title = json.load(open('movie_id_to_title.json'))
            self.db_manager.movie_title_to_id = json.load(open('movie_title_to_id.json'))
            self.db_manager.cinema_id_to_name = json.load(open('cinema_id_to_name.json'))
        else:'''
        for scraper in self.scrapers:
            scraped_result = scraper.scrape(self.browser)
            # Save scraped results in database
            self.db_manager.save_df_to_db(scraped_result, scraper.get_provider_id())
            self.db_manager.save_cinema_id_to_name(scraper.get_cinema_id_to_name(), scraper.get_provider_id())

    def get_movies(self):
        return self.db_manager.get_movie_ids()

    def get_sorted_movies(self):
        return sorted(self.db_manager.get_movie_titles())

    def get_movie_title(self, movie_id):
        return self.db_manager.get_movie_title(movie_id)

    def get_movie_dates(self, movie_id):
        return self.db_manager.get_movie_dates(movie_id)

    def get_showtimes(self, movie_id, date, provider_id=None, cinema_id=None):
        if provider_id and cinema_id:
            return self.db_manager.get_cinema_showtimes(movie_id, date, provider_id, cinema_id)
        else:
            return self.db_manager.get_showtimes(movie_id, date)

    def get_booking_link(self, movie_id, date, provider_id, cinema_id, time):
        dt = datetime.datetime.combine(date, time)
        session_id = self.db_manager.get_session_id(movie_id, provider_id, cinema_id, dt)
        booking_link = self.provider_id_to_scraper[provider_id].get_booking_link(cinema_id, session_id)
        return booking_link

    def get_cinema_name(self, cinema_id, provider_id):
        return self.db_manager.get_cinema_name(cinema_id, provider_id)

    def get_provider_name(self, provider_id):
        return self.provider_id_to_scraper[provider_id].get_provider_name()