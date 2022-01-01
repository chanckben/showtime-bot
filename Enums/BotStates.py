from enum import Enum

class BotState(Enum):
    AWAIT_MOVIE = 1
    AWAIT_DATE = 2
    AWAIT_ACTION = 3
    AWAIT_CINEMA = 4
    AWAIT_TIME = 5