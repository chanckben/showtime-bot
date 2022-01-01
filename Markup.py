from telegram import InlineKeyboardButton
from telegram import InlineKeyboardMarkup

# callback_map: Map from elements in lst to respective callback values
def build_keyboard(lst, callback_map):
    result = []
    for ele in lst:
        button = InlineKeyboardButton(ele, callback_data=callback_map[ele])
        result.append([button])
    result = InlineKeyboardMarkup(result)
    return result