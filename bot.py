import logging
from telegram import (Bot,
                      InlineKeyboardButton,
                      InlineKeyboardMarkup,
                      KeyboardButton,
                      ReplyKeyboardMarkup)
from telegram.ext import (CallbackQueryHandler,
                          CommandHandler,
                          Filters,
                          MessageHandler,
                          Updater)

import datetime
import json
from pymongo import MongoClient
from os import environ

from bus_stop_list import BusStopList
from utils import getNNearestStops
from credentials import TOKEN, APP_URL, DATABASE_URL

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO)

# non-bot stuff


# uses global variable bus_stops
def getCustomKeyboard(chat_id):
    keyboard = []
    # custom_stops is a list of bus stop names
    custom_stops = getUserStopsList(chat_id)
    for stop_name in custom_stops:
        keyboard.append([bus_stops.getStopCaption(stop_name)])

    sendLocationButton = KeyboardButton(
        text="Get nearest stops", request_location=True)
    keyboard.append(["/listallstops", sendLocationButton])
    keyboard.append(["/customise"])

    return keyboard

# bot functions


# sends a welcome message to the user
# also initialises the customised ReplyKeyboard
def start(bot, update):
    chat_id = update.message.chat_id

    # check if user is already in the database
    existing_data = db.user_settings.find_one({"chat_id": chat_id})

    if not existing_data:
        # add user to database
        payload = {
            "chat_id": chat_id,
            "date_initialised": datetime.datetime.utcnow()
        }

        db.user_settings.insert_one(document=payload)

    keyboard = getCustomKeyboard(chat_id)
    reply_markup = ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

    text = ""
    text += "Hello! This is a telegram bot for getting the arrival timings"
    text += " of NUS buses."
    bot.sendMessage(chat_id=chat_id,
                    text=text,
                    reply_markup=reply_markup)


# uses the global variable bus_stops
def listAllStops(bot, update):
    chat_id = update.message.chat_id

    # craft inline keyboard
    keyboard = []
    # temporary variable name
    # TODO sort out naming conflict and remove temp var name
    ls = bus_stops.getBusStopList()
    for bus_stop in ls:
        button_text = bus_stop.getCaption()
        data = {
            "user_state": "get_timing",
            "stop_name": bus_stop.getName()
        }
        payload = json.dumps(data)
        keyboard.append([InlineKeyboardButton(
            button_text, callback_data=payload)])

    reply_markup = InlineKeyboardMarkup(keyboard)
    text = "Pick a stop:"

    bot.sendMessage(chat_id=chat_id, text=text, reply_markup=reply_markup)


# gives user a list of 5 nearest bus stops
def location(bot, update):
    chat_id = update.message.chat_id
    latitude = update.message.location.latitude
    longitude = update.message.location.longitude

    query_point = (latitude, longitude)

    # get nearest stops
    nearest_stops = getNNearestStops(query_point, bus_stops)

    # craft the inlinekeyboard buttons
    keyboard = []
    for bus_stop in nearest_stops:
        stop_caption = bus_stop.getCaption()
        button_text = stop_caption
        data = {
            "user_state": "get_timing",
            "stop_name": bus_stop.getName()
        }
        payload = json.dumps(data)
        keyboard.append([InlineKeyboardButton(
            button_text, callback_data=payload)])

    reply_markup = InlineKeyboardMarkup(keyboard)
    text = "Here are the closest bus stops:"

    bot.sendMessage(chat_id=chat_id, text=text, reply_markup=reply_markup)


# gives user the bus arrival timings based on the stop selected
def button(bot, update):
    query = update.callback_query
    chat_id = query.message.chat_id
    message_id = query.message.message_id

    content = json.loads(query.data)
    # TODO user state handler class
    user_state = content["user_state"]

    if user_state == "get_timing":
        stop_name = content["stop_name"]

        # Disable the keyboard while the information is being retrieved
        text = "Loading...\n"
        bot.editMessageText(chat_id=chat_id, text=text, message_id=message_id)

        text = bus_stops.getBusStopData(stop_name)

        bot.editMessageText(chat_id=chat_id, text=text, message_id=message_id)

    if user_state == "settings_add":
        text = "Add stops"
        bot.editMessageText(chat_id=chat_id, text=text, message_id=message_id)
        showAddStops(chat_id)

    if user_state == "add_new_stop":
        stop_name = content["stop_name"]
        stop_caption = bus_stops.getStopCaption(stop_name)
        text = stop_caption + " was added"
        bot.editMessageText(chat_id=chat_id, text=text, message_id=message_id)
        addStop(chat_id, stop_name)

    if user_state == "settings_remove":
        text = "Remove stops"
        bot.editMessageText(chat_id=chat_id, text=text, message_id=message_id)
        showRemoveStops(chat_id)

    if user_state == "remove_stop":
        stop_name = content["stop_name"]
        stop_caption = bus_stops.getStopCaption(stop_name)
        text = stop_caption + " was removed"
        bot.editMessageText(chat_id=chat_id, text=text, message_id=message_id)
        removeStop(chat_id, stop_name)

    if user_state == "settings_reorder":
        text = "Reorder stops"
        bot.editMessageText(chat_id=chat_id, text=text, message_id=message_id)
        showReorderStopsList(chat_id)

    if user_state == "reorder_stop":
        stop_name = content["stop_name"]
        stop_caption = bus_stops.getStopCaption(stop_name)
        text = stop_caption + " shifted to the top"
        bot.editMessageText(chat_id=chat_id, text=text, message_id=message_id)
        reorderStop(chat_id, stop_name)

    if user_state == "edit_done":
        text = "Done"
        bot.editMessageText(chat_id=chat_id, text=text, message_id=message_id)
        showSettings(chat_id)

    if user_state == "exit_settings":
        text = "Changes have been saved"
        bot.editMessageText(chat_id=chat_id, text=text, message_id=message_id)

        # initialise user's custom keyboard
        keyboard = []
        custom_stops = getUserStopsList(chat_id)
        for stop_name in custom_stops:
            stop_caption = bus_stops.getStopCaption(stop_name)
            keyboard.append([stop_caption])

        sendLocationButton = KeyboardButton(
            text="Get nearest stops", request_location=True)
        keyboard.append(["/listallstops", sendLocationButton])
        keyboard.append(["/customise"])

        reply_markup = ReplyKeyboardMarkup(
            keyboard=keyboard, resize_keyboard=True)

        text = "Custom keyboard has been updated"
        bot.sendMessage(chat_id=chat_id,
                        text=text,
                        reply_markup=reply_markup)


# allow the user to add in their own custom keyboard
def settings(bot, update):
    chat_id = update.message.chat_id
    showSettings(chat_id)


def showSettings(chat_id):
    keyboard = []

    data = {"user_state": "settings_add"}
    payload = json.dumps(data)
    add_button = InlineKeyboardButton("Add stops", callback_data=payload)
    payload = json.dumps({"user_state": "settings_remove"})
    remove_button = InlineKeyboardButton("Remove stops", callback_data=payload)
    payload = json.dumps({"user_state": "settings_reorder"})
    reorder_button = InlineKeyboardButton(
        "Reorder stops", callback_data=payload)
    data = {"user_state": "exit_settings"}
    payload = json.dumps(data)
    done_button = InlineKeyboardButton("Done", callback_data=payload)

    text = ""
    custom_list_text = getCustomKeyboardText(chat_id)
    if custom_list_text:
        text += "Here are the stops in your list:\n"
        text += custom_list_text

        keyboard.append([add_button, remove_button])
        keyboard.append([reorder_button, done_button])
    else:
        text += "Your list is currently empty\n"
        text += "Try adding some stops!\n"

        keyboard.append([add_button])
        keyboard.append([done_button])

    text += "Choose an option:"
    reply_markup = InlineKeyboardMarkup(keyboard)

    bot.sendMessage(chat_id=chat_id,
                    text=text,
                    reply_markup=reply_markup,
                    parse_mode="Markdown")


def getCustomKeyboardText(chat_id):
    custom_stops = getUserStopsList(chat_id)
    text = ""
    for index, stop_name in enumerate(custom_stops):
        stop_caption = bus_stops.getStopCaption(stop_name)
        stop_text = "*" + str(index + 1) + ". " + stop_caption + "*\n"
        text += stop_text

    return text


# returns an array of the user custom stops
def getUserStopsList(chat_id):
    # retrieve user's current custom list from db
    existing_data = db.user_settings.find_one({"chat_id": chat_id})

    if "custom_stops" in existing_data:
        # load into array
        custom_stops = existing_data["custom_stops"]
    else:
        custom_stops = []

    return custom_stops


# TODO move this to UserState class
# uses global variable bus_stops
# current user state must be "settings_add"
def showAddStops(chat_id):
    # get user's current custom list of stops
    custom_stops = getUserStopsList(chat_id)

    # craft inline keyboard
    keyboard = []

    # TODO resolve temp conflicting var name
    ls = bus_stops.getBusStopList()
    if len(custom_stops) != len(ls):
        for bus_stop in ls:
            if bus_stop.getName() not in custom_stops:
                button_text = bus_stop.getCaption()
                data = {
                    "user_state": "add_new_stop",
                    "stop_name": bus_stop.getName()
                }
                payload = json.dumps(data)
                keyboard.append([InlineKeyboardButton(
                    button_text, callback_data=payload)])

        # add a done button
        # brings the user back to settings
        data = {
            "user_state": "edit_done"
        }
        payload = json.dumps(data)
        keyboard.append([InlineKeyboardButton("Done", callback_data=payload)])

        reply_markup = InlineKeyboardMarkup(keyboard)
        text = "Pick a stop to *add*:"

        bot.sendMessage(chat_id=chat_id,
                        text=text,
                        reply_markup=reply_markup,
                        parse_mode="Markdown")
    else:
        text = "No more stops to add"
        bot.sendMessage(chat_id=chat_id,
                        text=text,
                        parse_mode="Markdown")
        showSettings(chat_id)


# current user state must be "settings_add_new_stop"
# brings user back to showAddStops
def addStop(chat_id, stop_name):
    custom_stops = getUserStopsList(chat_id)
    custom_stops.append(stop_name)

    payload = {
        "custom_stops": custom_stops
    }

    # update user_state and custom_stops in database
    db.user_settings.update_one(filter={'chat_id': chat_id},
                                update={'$set': payload},
                                upsert=True)

    showAddStops(chat_id)


def showRemoveStops(chat_id):
    # get user's current custom list of stops
    custom_stops = getUserStopsList(chat_id)

    # craft the keyboard
    keyboard = []

    if custom_stops:
        for stop_name in custom_stops:
            button_text = bus_stops.getStopCaption(stop_name)
            data = {
                "user_state": "remove_stop",
                "stop_name": stop_name
            }
            payload = json.dumps(data)
            keyboard.append([InlineKeyboardButton(
                button_text, callback_data=payload)])

        # add a done button
        # brings the user back to settings
        data = {
            "user_state": "edit_done"
        }
        payload = json.dumps(data)
        keyboard.append([InlineKeyboardButton("Done", callback_data=payload)])

        reply_markup = InlineKeyboardMarkup(keyboard)
        text = "Pick a stop to *remove*:"

        bot.sendMessage(chat_id=chat_id,
                        text=text,
                        reply_markup=reply_markup,
                        parse_mode="Markdown")
    else:
        text = "No more stops to remove"
        bot.sendMessage(chat_id=chat_id,
                        text=text,
                        parse_mode="Markdown")
        showSettings(chat_id)


def removeStop(chat_id, stop_name):
    custom_stops = getUserStopsList(chat_id)
    custom_stops.remove(stop_name)

    payload = {
        "custom_stops": custom_stops
    }

    # update user_state and custom_stops in database
    db.user_settings.update_one(filter={'chat_id': chat_id},
                                update={'$set': payload},
                                upsert=True)

    showRemoveStops(chat_id)


def showReorderStopsList(chat_id):
    custom_stops = getUserStopsList(chat_id)

    # craft the keyboard
    keyboard = []

    for stop_name in custom_stops:
        button_text = bus_stops.getStopCaption(stop_name)
        data = {
            "user_state": "reorder_stop",
            "stop_name": stop_name
        }
        payload = json.dumps(data)
        keyboard.append([InlineKeyboardButton(
            button_text, callback_data=payload)])

    # add a done button
    # brings the user back to settings
    data = {
        "user_state": "edit_done"
    }
    payload = json.dumps(data)
    keyboard.append([InlineKeyboardButton("Done", callback_data=payload)])

    reply_markup = InlineKeyboardMarkup(keyboard)
    text = "Pick a stop to *shift it to the top*:"

    bot.sendMessage(chat_id=chat_id,
                    text=text,
                    reply_markup=reply_markup,
                    parse_mode="Markdown")


def reorderStop(chat_id, stop_name):
    custom_stops = getUserStopsList(chat_id)

    # shift stop to the front
    custom_stops.insert(0, custom_stops.pop(custom_stops.index(stop_name)))

    payload = {
        "custom_stops": custom_stops
    }

    # update user_state and custom_stops in database
    db.user_settings.update_one(filter={'chat_id': chat_id},
                                update={'$set': payload},
                                upsert=True)

    showReorderStopsList(chat_id)


# TODO try catch
def processMessage(bot, update):
    chat_id = update.message.chat_id
    message_text = update.message.text
    stop_name = bus_stops.getStopName(message_text)

    text = bus_stops.getBusStopData(stop_name)

    bot.sendMessage(chat_id=chat_id, text=text)


def help(bot, update):
    chat_id = update.message.chat_id
    text = "*The bus will come when it comes.*\n\n"
    text = text + "Please report any bugs to shaohui@u.nus.edu"

    bot.sendMessage(chat_id=chat_id, text=text, parse_mode="Markdown")


def error(bot, update, error):
    logging.warning('Update "%s" caused error "%s"' % (update, error))


def main():
    # load list of stops
    global bus_stops
    bus_stops = BusStopList()
    bus_stops.update()

    # initialise database
    client = MongoClient(DATABASE_URL)
    global db
    db = client.nusbusarrivalbot  # select the database

    # Create the Updater and pass it your bot's token.
    updater = Updater(TOKEN)

    # initialise bot
    global bot
    bot = Bot(token=TOKEN)

    # setup webhook
    # PORT = int(environ.get('PORT', '5000'))
    # updater.start_webhook(listen="0.0.0.0", port=PORT, url_path=TOKEN)
    # updater.bot.setWebhook(APP_URL + TOKEN)

    # Use long polling (disabled when webhooks are enabled)
    updater.start_polling()

    # add handlers
    updater.dispatcher.add_handler(CommandHandler('start', start))
    updater.dispatcher.add_handler(
        CommandHandler('listallstops', listAllStops))
    updater.dispatcher.add_handler(MessageHandler(Filters.location, location))
    updater.dispatcher.add_handler(CallbackQueryHandler(button))
    updater.dispatcher.add_handler(CommandHandler('customise', settings))
    updater.dispatcher.add_handler(CommandHandler('help', help))
    updater.dispatcher.add_handler(
        MessageHandler(Filters.text, processMessage))
    updater.dispatcher.add_error_handler(error)

    # Run the bot until the user presses Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT
    updater.idle()


if __name__ == "__main__":
    main()
