from Scrapers.Structs.Cinema import Cinema
from Scrapers.Structs.Movie import Movie
from Scrapers.Structs.Showtime import Showtime
from datetime import time, datetime
import pandas as pd
import re
from time import sleep

import os
from os.path import dirname
from selenium import webdriver


class CathayScraper:
    def __init__(self):
        self.cinema_id_to_name = {}

    def parse_movie_title(self, raw_movie_title, movie_id):
        # Assumption: Raw movie titles are of the format <MovieTitle> <Rating> with an optional asterisk (*)
        pattern = r'^([\s\S]+)\s(R21|M18|NC16|PG13|PG|G){1}(\s[*])?$'
        title_groups = re.match(pattern, raw_movie_title).groups()
        return Movie(title_groups[0], title_groups[1], movie_id)

    # Cleans a cinema name and returns a Cinema object
    def parse_cinema_name(self, raw_cinema_name, cinema_id):
        # Assumption: Raw cinema names are already clean
        self.cinema_id_to_name[cinema_id] = raw_cinema_name
        return Cinema(raw_cinema_name, cinema_id)

    # Uses dropdown lists to get movies, cinemas and time
    # Not working as of 4 January 2022
    def scrape_backup(self, browser):
        select_movie_dropdown_xpath = '/html/body/div/form/div/div/div[8]/div[1]/select'
        select_cinema_dropdown_xpath = '/html/body/div/form/div/div/div[8]/div[2]/select'
        select_date_dropdown_xpath = '/html/body/div/form/div/div/div[8]/div[3]/select'
        select_time_dropdown_xpath = '/html/body/div/form/div/div/div[8]/div[4]/select'

        browser.get("https://www.cathaycineplexes.com.sg/movies/")

        movie_titles_html = browser.find_elements_by_xpath(select_movie_dropdown_xpath + '/*')[1:]

        output = []
        #for movie_choice in movie_titles_html:
        for i in range(len(movie_titles_html)):
            movie_choice = browser.find_elements_by_xpath(select_movie_dropdown_xpath + '/*')[1+i]
            movie_choice.click()
            movie_object = self.parse_movie_title(movie_choice.text, movie_choice.get_attribute("value"))
            print(movie_object)
            sleep(1)
            cinema_names_html = browser.find_elements_by_xpath(select_cinema_dropdown_xpath + '/*')[1:]
            #for cinema_choice in cinema_names_html:
            for j in range(len(cinema_names_html)):
                cinema_choice = browser.find_elements_by_xpath(select_movie_dropdown_xpath + '/*')[1+j]
                cinema_choice.click()
                cinema_object = self.parse_cinema_name(cinema_choice.text, cinema_choice.get_attribute("value"))
                print(cinema_object)
                sleep(1)
                dates_html = browser.find_elements_by_xpath(select_date_dropdown_xpath + '/*')[1:]
                #for date_choice in dates_html:
                for k in range(len(dates_html)):
                    date_choice = browser.find_elements_by_xpath(select_date_dropdown_xpath + '/*')[1+k]
                    date_choice.click()
                    session_date = date_choice.get_attribute("value").split(' ')[0]
                    session_date = datetime.strptime(session_date, "%d/%m/%Y").date()
                    print(session_date)
                    sleep(2)
                    times_html = browser.find_elements_by_xpath(select_time_dropdown_xpath + '/*')[1:]
                    for time_choice in times_html:
                        session_id = time_choice.get_attribute("value")
                        session_time = time_choice.text.split(' ')[0]
                        session_time = time.fromisoformat(session_time)
                        print(session_time)
                        timestamp = datetime.combine(session_date, session_time)
                        output.append(Showtime(movie_object, cinema_object, timestamp, session_id))

        output = pd.DataFrame(output, columns=['Object'])
        output['Movie'] = output['Object'].apply(lambda showtime: showtime.get_movie().get_title())
        output['Cinema'] = output['Object'].apply(lambda showtime: showtime.get_cinema().get_id())
        output['Time'] = output['Object'].apply(lambda showtime: showtime.get_session_time())
        output['SessionID'] = output['Object'].apply(lambda showtime: showtime.get_session_id())
        return output

    def scrape(self, browser):
        def parse_movie_title(raw_movie_title):
            # Assumption: Raw movie titles are of the format <MovieTitle> <Rating> with an optional asterisk (*)
            pattern = r'^([\s\S]+)\s(R21|M18|NC16|PG13|PG|G){1}(\s[*])?\s\(Dolby\sDigital\)$'
            return re.match(pattern, raw_movie_title).group(1)

        select_date_dropdown_xpath = '/html/body/div/form/div/div/div[8]/div[3]/select'
        browser.get("https://www.cathaycineplexes.com.sg/")

        output = []
        dates_html = browser.find_elements_by_xpath(select_date_dropdown_xpath + '/*')[1:]
        for i in range(len(dates_html)):
            date_choice = browser.find_elements_by_xpath(select_date_dropdown_xpath + '/*')[1+i]
            session_date = date_choice.get_attribute("value").split(' ')[0]
            date_url = f"https://www.cathaycineplexes.com.sg/showtimes.aspx?day={session_date}"
            browser.get(date_url)
            for cinema_html in browser.find_elements_by_xpath('//div[@id="showtimes"]/div')[2:-1]:
                cinema = cinema_html.find_element_by_xpath('./ul/li/div').text # XPATH: //div[@id="showtimes"]/div[3]/ul/li/div
                cinema_html = cinema_html.find_elements_by_xpath('.//div[@aria-labelledby="tab_title_link_1"]/div') # XPATH: //div[@id="showtimes"]/div[3]//div[@aria-labelledby="tab_title_link_1"]/div
                for movie_html in cinema_html:
                    movie_title = movie_html.find_element_by_xpath('.//a').text
                    movie_title = parse_movie_title(movie_title)
                    showtimes_html = movie_html.find_elements_by_xpath('.//div[@class="showtimeitem_time_pms"]') # XPATH: //div[@id="showtimes"]/div[3]//div[@aria-labelledby="tab_title_link_1"]/div[1]//div[@class="showtimeitem_time_pms"]
                    for showtime_html in showtimes_html:
                        booking_link = showtime_html.find_element_by_xpath('./a').get_attribute('data-href-stop')
                        booking_time = showtime_html.find_element_by_xpath('./a').get_attribute('title')
                        cinema_id, session_id = re.search(r'^https:\/\/booking.cathaycineplexes.com.sg\/Ticketing\/visSelectSeats.aspx\?cinemacode=(\d{4})&txtSessionId=(\d{5,6})&visLang=1$', booking_link).groups()
                        self.cinema_id_to_name[cinema_id] = cinema
                        booking_time = datetime.strptime(booking_time, '%d/%m/%Y %H:%M:%S %p')
                        output.append((movie_title, cinema_id, booking_time, session_id))
        return pd.DataFrame(output, columns=['Movie', 'Cinema', 'Time', 'SessionID'])

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
