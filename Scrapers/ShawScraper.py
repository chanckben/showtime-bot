#from Scrapers.Structs.Cinema import Cinema
#from Structs.Movie import Movie
#from Scrapers.Structs.Showtime import Showtime
from datetime import time, datetime
import pandas as pd
import re
from time import sleep
from selenium import webdriver
import os
from os.path import dirname

class ShawScraper:
    def __init__(self):
        self.movie_id_to_title = {}
        self.cinema_id_to_name = {}

    def parse_movie_title(self, raw_movie_title):
        # Assumption: Raw movie titles are of the format <MovieTitle>, optionally followed by a single letter denoting language enclosed in round brackets
        if re.search("\s\(([A-Z])\)$", raw_movie_title):
            clean_title = raw_movie_title[:-4]
        else:
            clean_title = raw_movie_title
        return clean_title

    def parse_showtime(self, raw_showtime):
        # Assumption: Raw showtimes are of the format <HH:MM> (AM|PM)(*)?(+)?
        # +: Chinese subtitles
        # *: English subtitles
        time_groups = re.search(r'^(\d{1,2}:\d{1,2})\s(AM|PM)(\*)?(\+)?$', raw_showtime)
        return datetime.strptime(f"{time_groups.group(1)} {time_groups.group(2)}", "%I:%M %p").time()

    def parse_cinema_name(self, raw_cinema_name):
        # Assumption: Raw cinema name is of the format "Shaw Theatres <CinemaName>"
        return re.search(r'^Shaw Theatres\s(.*)$', raw_cinema_name).group(1)

    def scrape(self, browser):
        select_date_dropdown_xpath = '/html/body/div[1]/div/div[2]/div[1]/div/div/div/div/div[1]/div/div[1]/div/div/select'
        select_movie_dropdown_xpath = '/html/body/div[1]/div/div[2]/div[1]/div/div/div/div/div[1]/div/div[2]/div/div/select'
        select_cinema_dropdown_xpath = '/html/body/div[1]/div/div[2]/div[1]/div/div/div/div/div[1]/div/div[3]/div/div/select'

        browser.get("https://shaw.sg/")

        # Populate movie_id_to_title
        movies_html = browser.find_elements_by_xpath(select_movie_dropdown_xpath + '/*')[1:]
        for movie_html in movies_html:
            self.movie_id_to_title[movie_html.get_attribute('value')] = self.parse_movie_title(movie_html.text)

        # Populate cinema_id_to_name
        cinemas_html = browser.find_elements_by_xpath(select_cinema_dropdown_xpath + '/*')[1:]
        for cinema_html in cinemas_html:
            self.cinema_id_to_name[cinema_html.get_attribute('value')] = self.parse_cinema_name(cinema_html.text)

        dates_html = browser.find_elements_by_xpath(select_date_dropdown_xpath + '/*')
        dates = []
        for date_html in dates_html:
            date = date_html.get_attribute('value')
            date = datetime.fromisoformat(date).date()
            dates.append(date)

        output = []
        for date in dates:
            date_url = f"https://shaw.sg/Showtimes/{date}/All/All"
            browser.get(date_url)
            location_area_persist = browser.find_elements_by_xpath('//*[@class="location-area-persist"]')
            for location_html in location_area_persist:
                cinema_id = location_html.find_element_by_xpath('.//div/a').get_attribute('href').split('/')[-1]
                for movie_html in location_html.find_elements_by_xpath('.//div[@class="movies_item-movie row block-list-showtimes"]'):
                    movie_id = movie_html.find_element_by_xpath('.//div[@class="title"]/a').get_attribute('href').split('/')[-1]
                    showtimes_html = movie_html.find_elements_by_xpath('.//div[2]/div/a')
                    for showtime_html in showtimes_html:
                        showtime = datetime.combine(date, self.parse_showtime(showtime_html.text))
                        session_id = showtime_html.get_attribute('href').split('/')[-1]
                        output.append((self.movie_id_to_title[movie_id], cinema_id, showtime, session_id))
        return pd.DataFrame(output, columns=['Movie', 'Cinema', 'Time', 'SessionID'])

    def get_cinema_id_to_name(self):
        return self.cinema_id_to_name

    def get_provider_id(self):
        return "SW"

    @staticmethod
    def get_provider_name():
        return "Shaw Theatres"

    @staticmethod
    def get_booking_link(cinema_id, session_id):
        return f"https://shaw.sg/seat-selection/{session_id}"
