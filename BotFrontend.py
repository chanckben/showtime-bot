from telegram.ext import Updater, CallbackQueryHandler, CommandHandler, ConversationHandler
from Enums.BotStates import BotState
from Enums.Actions import Action
from Markup import build_keyboard
from ShowtimeManager import ShowtimeManager
import logging
import os
# import redis
import sys

# Enabling logging

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger()

# Set environment variables

MODE = os.environ.get('MODE') # $Env:MODE="dev"
TOKEN = os.environ.get('TOKEN') # $Env:TOKEN=<token>

if MODE == "dev":
    def run(updater):
        updater.start_polling()
elif MODE == "prod":
    def run(updater):
        PORT = int(os.environ.get('PORT', '8443'))
        updater.start_webhook(
            listen='0.0.0.0', 
            port=PORT, 
            url_path=TOKEN, 
            webhook_url='https://showtime.herokuapp.com/' + TOKEN
        )
else:
    logger.error("No MODE specified!")
    sys.exit(1)

# Connect to Redis

# r = redis.from_url(os.environ.get("REDIS_URL"))

# Initialise ShowtimeManager and start scraping

manager = ShowtimeManager()
manager.init_webdriver()
manager.start_scraping()

# Functions for commands

def get_movies(update, context):
    # Replies with a list of movies
    reply = "Now Showing:"
    for i, movie_title in enumerate(manager.get_sorted_movies()):
        reply += f"\n{i+1}. {movie_title}"
    update.message.reply_text(reply)

def choose_movie_helper():
    # Returns the reply and reply markup for choosing a movie
    callback_map = {}
    for movie_id in manager.get_movies():
        title = manager.get_movie_title(movie_id)
        callback_map[title] = movie_id

    keyboard = build_keyboard(manager.get_sorted_movies(), callback_map)
    return {"reply": "Choose a movie", "markup": keyboard}

def choose_movie(update, context):
    # Replies with an InlineKeyboard of movies
    output = choose_movie_helper()
    update.message.reply_text(output["reply"], reply_markup=output["markup"])
    
    return BotState.AWAIT_MOVIE

# Functions for callback queries

def callback_movie(update, context):
    # Store the movie, reply with an InlineKeyboard of dates
    query = update.callback_query
    query.answer()

    movie_id = query.data
    title = manager.get_movie_title(movie_id)
    reply = f"Movie chosen: {title}\nChoose a date"
    movie_dates = manager.get_movie_dates(movie_id)
    callback_map = {}
    dates = []
    for date in movie_dates:
        format_date = date.strftime("%d %B, %Y")
        callback_map[format_date] = (movie_id, date)
        dates.append(format_date)
    keyboard = build_keyboard(dates, callback_map)

    query.edit_message_text(text=reply, reply_markup=keyboard)

    return BotState.AWAIT_DATE

def callback_date(update, context):
    query = update.callback_query
    query.answer()

    # Display showtimes

    movie_id, date = query.data
    title = manager.get_movie_title(movie_id)
    reply = f'Movie chosen: {title}\nDate chosen: {date.strftime("%d %B, %Y")}'
    showtimes = manager.get_showtimes(movie_id, date)

    data = []
    for provider, loc_time_dic in showtimes.items():
        for cinema, times in loc_time_dic.items():
            cinema_name = f"{manager.get_provider_name(provider)} {manager.get_cinema_name(cinema, provider)}"
            time_str = ', '.join(times)
            reply += f"\n\n{cinema_name}:\n{time_str}"
            data.append({"provider": provider, "cinema": cinema, "movie": movie_id, "date": date})

    query.edit_message_text(text=reply)

    # Ask the user for next action

    reply = "What would you like to do?"
    callback_map = {
        "Make booking": {"action": Action.MAKE_BOOKING, "data": data},
        "View other showtimes": {"action": Action.VIEW_SHOWTIMES},
        "Nothing": {"action": Action.NOTHING}
    }
    keyboard = build_keyboard(callback_map.keys(), callback_map)
    query.message.reply_text(text=reply, reply_markup=keyboard)

    return BotState.AWAIT_ACTION

def callback_action(update, context):
    query = update.callback_query
    query.answer()

    action = query.data["action"]
    if action == Action.MAKE_BOOKING:
        # Choose cinema
        reply = "To make a booking, choose one of the cinemas below"
        cinema_names = []
        for dic in query.data["data"]:
            provider_name = manager.get_provider_name(dic["provider"])
            cinema_name = manager.get_cinema_name(dic["cinema"], dic["provider"])
            cinema_names.append(f"{provider_name} {cinema_name}")
        keyboard = build_keyboard(cinema_names, dict(zip(cinema_names, query.data["data"])))
        query.edit_message_text(text=reply, reply_markup=keyboard)
        return BotState.AWAIT_CINEMA
    elif action == Action.VIEW_SHOWTIMES:
        # Go back to choosing a movie
        output = choose_movie_helper()
        query.edit_message_text(text=output["reply"], reply_markup=output["markup"])
        return BotState.AWAIT_MOVIE
    elif action == Action.NOTHING:
        # Delete message and end conversation
        query.message.delete()
        return

def callback_cinema(update, context):
    query = update.callback_query
    query.answer()

    provider_id = query.data["provider"]
    cinema_id = query.data["cinema"]
    movie_id = query.data["movie"]
    date = query.data["date"]
    
    times = manager.get_showtimes(movie_id, date, provider_id, cinema_id)
    reply = f"Cinema chosen: {manager.get_provider_name(provider_id)} {manager.get_cinema_name(cinema_id, provider_id)}"
    reply += "\nChoose a time"
    callback_map = {}
    for time in times:
        info = {"provider": provider_id, "cinema": cinema_id, "movie": movie_id, "date": date, "time": time}
        callback_map[time] = info
    keyboard = build_keyboard(times, callback_map)
    query.edit_message_text(text=reply, reply_markup=keyboard)
    return BotState.AWAIT_TIME

def callback_time(update, context):
    query = update.callback_query
    query.answer()

    provider_id = query.data["provider"]
    cinema_id = query.data["cinema"]
    movie_id = query.data["movie"]
    date = query.data["date"]
    time = query.data["time"]

    session = manager.get_booking_link(movie_id, date, provider_id, cinema_id, time)
    reply = f"Cinema chosen: {manager.get_provider_name(provider_id)} {manager.get_cinema_name(cinema_id, provider_id)}"
    reply += f"\nTime chosen: {time}"
    reply += f"\nBooking link: {session}"
    query.edit_message_text(text=reply)
    return

def main():
    logger.info("Starting bot")
    updater = Updater(token=TOKEN, arbitrary_callback_data=True)
    dp = updater.dispatcher # Dispatcher to register handlers

    # Add handlers for commands
    dp.add_handler(CommandHandler("getmovies", get_movies))

    showtimes_handler = ConversationHandler(
        entry_points=[CommandHandler("getshowtimes", choose_movie)],
        states={
            BotState.AWAIT_MOVIE: [CallbackQueryHandler(callback_movie)],
            BotState.AWAIT_DATE: [CallbackQueryHandler(callback_date)],
            BotState.AWAIT_ACTION: [CallbackQueryHandler(callback_action)],
            BotState.AWAIT_CINEMA: [CallbackQueryHandler(callback_cinema)],
            BotState.AWAIT_TIME: [CallbackQueryHandler(callback_time)]
        },
        fallbacks=[CommandHandler("getshowtimes", choose_movie)]
    )

    dp.add_handler(showtimes_handler)

    run(updater)

    updater.idle()

if __name__ == '__main__':
    main()
