import logging
from telegram import Bot, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler

import requests
import json
import datetime
from pymongo import MongoClient
from os import environ
from geopy.distance import vincenty
from bs4 import BeautifulSoup

from credentials import TOKEN, APP_URL, MLABS_DATABASE

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

#non-bot stuff

#for sorting the list of busses
def sortName(bus):
    return bus["name"]


#returns object containing array of bus stops data
def getStopsList():
    url = 'http://nextbus.comfortdelgro.com.sg/testMethod.asmx/GetBusStops'
    result = requests.get(url)

    soup = BeautifulSoup(result.content, 'html.parser')
    result = json.loads(soup.text)

    return result["BusStopsResult"]


#gets a dictionary that maps the stopID to its name
def getStopsDict():
    stopsDict = {}
    for stop in stopsList:
        stopsDict[stop["name"]] = stop["caption"]
        stopsDict[stop["caption"]] = stop["name"]

    return stopsDict


#does the ajax call to the API
def getArrivals(stopID):
    url = 'http://nextbus.comfortdelgro.com.sg/testMethod.asmx/GetShuttleService?busstopname=' + stopID
    result = requests.get(url)

    soup = BeautifulSoup(result.content, 'html.parser')
    data = json.loads(soup.text)

    return data["ShuttleServiceResult"]


#returns the text to be printed for the user
def getArrivalsText(stopID):
    result = getArrivals(stopID)
    arrivals = result["shuttles"]
    text = "Bus arrival timings for " + result["caption"] + "\n\n" #text to be displayed to user

    #sort busses according to alphabetical order
    arrivals = sorted(arrivals, key=sortName)

    for bus in arrivals:
        busID = bus["name"]
        arrivalTime = bus["arrivalTime"]
        nextArrivalTime = bus["nextArrivalTime"]

        text = text + busID + "\n" #append busID
        text = text + "Next: " + arrivalTime + "\n" #append next arrival time
        if arrivalTime != "-": #show subsequent only if there is a there is a bus arriving next
            text = text + "Subsequent: " + nextArrivalTime + "\n" #append subsequent arrival time
        text = text + "\n"

    text = text.rstrip() #rstrip removes the additional \n characters from the back of the string

    return text


#returns array of nearest stops objects
#uses the global variable stopsList
def getNearestStops(queryPoint):
    nearestStops = [] #insert closest at the front, furthest at the back
    nearestDistances = []

    for stop in stopsList:
        stopLocation = (stop["latitude"], stop["longitude"])
        currentDistance = vincenty(queryPoint, stopLocation).meters

        if len(nearestStops) == 0: #initialise reference values
            nearestDistances.append(currentDistance)
            nearestStops.append(stop)
        else: #insert to array maintaining ascending order
            index = 0
            for distance in nearestDistances:
                if (currentDistance < distance):
                    nearestDistances.insert(index, currentDistance)
                    nearestStops.insert(index, stop)
                    break
                index = index + 1

            if len(nearestStops) == 6:
                #remove the furthest
                del nearestStops[5]
                del nearestDistances[5]

    return nearestStops


def getStopName(stop_id):
    return stopsDict[stop_id]


def getStopID(stop_name):
    return stopsDict[stop_name]


def formatMessage(message_text):
    message_text.replace(" ", "")
    message_text = message_text.lower()

    return message_text

def getCustomKeyboard(chat_id):
    keyboard = []
    custom_stops = getUserStopsList(chat_id)
    for stop in custom_stops:
        keyboard.append([getStopName(stop)])

    sendLocationButton = KeyboardButton(text="Get nearest stops", request_location=True)
    keyboard.append(["/listallstops", sendLocationButton])
    keyboard.append(["/customise"])

    return keyboard

#bot functions

#sends a welcome message to the user
#also initialises the customised ReplyKeyboard
def start(bot, update):
    chat_id = update.message.chat_id

    #check if user is already in the database
    existing_data = db.user_settings.find_one({"chat_id": chat_id})

    if not existing_data:
        #add user to database
        payload = {
            "chat_id": chat_id,
            "date_initialised": datetime.datetime.utcnow()
        }

        db.user_settings.insert_one(document=payload)

    keyboard = getCustomKeyboard(chat_id)
    reply_markup = ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

    text = "Hello! This is a telegram bot for getting the arrival timings of NUS busses."
    bot.sendMessage(chat_id=chat_id, text=text, reply_markup=reply_markup)


#uses the global variable stopsList
def listallstops(bot, update):
    chat_id = update.message.chat_id

    #craft inline keyboard
    keyboard = []
    for stop in stopsList:
        buttonText = stop["caption"]
        data = {
            "user_state": "get_timing",
            "stopID": stop["name"]
        }
        payload = json.dumps(data)
        keyboard.append([InlineKeyboardButton(buttonText, callback_data=payload)])

    reply_markup = InlineKeyboardMarkup(keyboard)
    text = "Pick a stop:"

    bot.sendMessage(chat_id=chat_id, text=text, reply_markup=reply_markup)


#gives user a list of 5 nearest bus stops
def location(bot, update):
    chat_id = update.message.chat_id
    latitude = update.message.location.latitude
    longitude = update.message.location.longitude

    query_point = (latitude, longitude)

    #get nearest stops
    nearestStops = getNearestStops(query_point)

    #craft the inlinekeyboard buttons
    keyboard = []
    for stop in nearestStops:
        buttonText = stop["caption"]
        data = {
            "user_state": "get_timing",
            "stopID": stop["name"]
        }
        payload = json.dumps(data)
        keyboard.append([InlineKeyboardButton(buttonText, callback_data=payload)])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = "Here are the closest bus stops:"

    bot.sendMessage(chat_id=chat_id, text=text, reply_markup=reply_markup)


#gives user the bus arrival timings based on the stop selected
def button(bot, update):
    query = update.callback_query
    chat_id = query.message.chat_id
    message_id = query.message.message_id

    content = json.loads(query.data)
    user_state = content["user_state"]

    if user_state == "get_timing":
        stop_id = content["stopID"]

        #Disable the keyboard while the information is being retrieved
        text = "Loading...\n"
        bot.editMessageText(chat_id=chat_id, text=text, message_id=message_id)

        text = getArrivalsText(stop_id)

        bot.editMessageText(chat_id=chat_id, text=text, message_id=message_id)


    if user_state == "settings_add":
        text = "Add stops"
        bot.editMessageText(chat_id=chat_id, text=text, message_id=message_id)
        showAddStops(chat_id)

    if user_state == "add_new_stop":
        stop_id = content["stopID"]
        text = getStopName(stop_id) + " was added"
        bot.editMessageText(chat_id=chat_id, text=text, message_id=message_id)
        addStop(chat_id, stop_id)

    if user_state == "settings_remove":
        text = "Remove stops"
        bot.editMessageText(chat_id=chat_id, text=text, message_id=message_id)
        showRemoveStops(chat_id)

    if user_state == "remove_stop":
        stop_id = content["stopID"]
        text = getStopName(stop_id) + " was removed"
        bot.editMessageText(chat_id=chat_id, text=text, message_id=message_id)
        removeStop(chat_id, stop_id)

    if user_state == "settings_reorder":
        text = "Reorder stops"
        bot.editMessageText(chat_id=chat_id, text=text, message_id=message_id)
        showReorderStopsList(chat_id)

    if user_state == "reorder_stop":
        stop_id = content["stopID"]
        text = getStopName(stop_id) + " shifted to the top"
        bot.editMessageText(chat_id=chat_id, text=text, message_id=message_id)
        reorderStop(chat_id, stop_id)

    if user_state == "edit_done":
        text = "Done"
        bot.editMessageText(chat_id=chat_id, text=text, message_id=message_id)
        showSettings(chat_id)

    if user_state == "exit_settings":
        text = "Changes have been saved"
        bot.editMessageText(chat_id=chat_id, text=text, message_id=message_id)

        #initialise user's custom keyboard
        keyboard = []
        custom_stops = getUserStopsList(chat_id)
        for stop in custom_stops:
            keyboard.append([getStopName(stop)])

        sendLocationButton = KeyboardButton(text="Get nearest stops", request_location=True)
        keyboard.append(["/listallstops", sendLocationButton])
        keyboard.append(["/customise"])

        reply_markup = ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

        text = "Custom keyboard has been updated"
        bot.sendMessage(chat_id=chat_id, text=text, reply_markup=reply_markup)


#allow the user to add in their own custom keyboard
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
    reorder_button = InlineKeyboardButton("Reorder stops", callback_data=payload)
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

    bot.sendMessage(chat_id=chat_id, text=text, reply_markup=reply_markup, parse_mode="Markdown")


def getCustomKeyboardText(chat_id):
    custom_stops = getUserStopsList(chat_id)
    text = ""
    for index, stop in enumerate(custom_stops):
        stop_text = "*" + str(index + 1) + ". " + getStopName(stop) + "*\n"
        text += stop_text

    return text


#returns an array of the user custom stops
def getUserStopsList(chat_id):
    #retrieve user's current custom list from db
    existing_data = db.user_settings.find_one({"chat_id": chat_id})

    if "custom_stops" in existing_data:
        #load into array
        custom_stops = existing_data["custom_stops"]
    else:
        custom_stops = []

    return custom_stops


#current user state must be "settings_add"
def showAddStops(chat_id):
    #get user's current custom list of stops
    custom_stops = getUserStopsList(chat_id)

    #craft inline keyboard
    keyboard = []

    if len(custom_stops) != len(stopsList):
        for stop in stopsList:
            if stop["name"] not in custom_stops:
                buttonText = stop["caption"]
                data = {
                    "user_state": "add_new_stop",
                    "stopID": stop["name"]
                }
                payload = json.dumps(data)
                keyboard.append([InlineKeyboardButton(buttonText, callback_data=payload)])

        #add a done button
        #brings the user back to settings
        data = {
                "user_state": "edit_done"
            }
        payload = json.dumps(data)
        keyboard.append([InlineKeyboardButton("Done", callback_data=payload)])

        reply_markup = InlineKeyboardMarkup(keyboard)
        text = "Pick a stop to *add*:"

        bot.sendMessage(chat_id=chat_id, text=text, reply_markup=reply_markup, parse_mode="Markdown")
    else:
        text = "No more stops to add"
        bot.sendMessage(chat_id=chat_id, text=text, parse_mode="Markdown")
        showSettings(chat_id)


#current user state must be "settings_add_new_stop"
#brings user back to showAddStops
def addStop(chat_id, stop_id):
    custom_stops = getUserStopsList(chat_id)
    custom_stops.append(stop_id)

    payload = {
        "custom_stops": custom_stops
    }

    #update user_state and custom_stops in database
    db.user_settings.update_one(filter={'chat_id' : chat_id},
                                update={'$set': payload},
                                upsert=True)

    showAddStops(chat_id)


def showRemoveStops(chat_id):
    #get user's current custom list of stops
    custom_stops = getUserStopsList(chat_id)

    #craft the keyboard
    keyboard = []

    if custom_stops:
        for stop in custom_stops:
            buttonText = getStopName(stop)
            data = {
                "user_state": "remove_stop",
                "stopID": stop
            }
            payload = json.dumps(data)
            keyboard.append([InlineKeyboardButton(buttonText, callback_data=payload)])

        #add a done button
        #brings the user back to settings
        data = {
                "user_state": "edit_done"
            }
        payload = json.dumps(data)
        keyboard.append([InlineKeyboardButton("Done", callback_data=payload)])

        reply_markup = InlineKeyboardMarkup(keyboard)
        text = "Pick a stop to *remove*:"

        bot.sendMessage(chat_id=chat_id, text=text, reply_markup=reply_markup, parse_mode="Markdown")
    else:
        text = "No more stops to remove"
        bot.sendMessage(chat_id=chat_id, text=text, parse_mode="Markdown")
        showSettings(chat_id)


def removeStop(chat_id, stop_id):
    custom_stops = getUserStopsList(chat_id)
    custom_stops.remove(stop_id)

    payload = {
        "custom_stops": custom_stops
    }

    #update user_state and custom_stops in database
    db.user_settings.update_one(filter={'chat_id' : chat_id},
                                update={'$set': payload},
                                upsert=True)

    showRemoveStops(chat_id)


def showReorderStopsList(chat_id):
    custom_stops = getUserStopsList(chat_id)

    #craft the keyboard
    keyboard = []

    for stop in custom_stops:
        buttonText = getStopName(stop)
        data = {
            "user_state": "reorder_stop",
            "stopID": stop
        }
        payload = json.dumps(data)
        keyboard.append([InlineKeyboardButton(buttonText, callback_data=payload)])

    #add a done button
    #brings the user back to settings
    data = {
            "user_state": "edit_done"
        }
    payload = json.dumps(data)
    keyboard.append([InlineKeyboardButton("Done", callback_data=payload)])

    reply_markup = InlineKeyboardMarkup(keyboard)
    text = "Pick a stop to *shift it to the top*:"

    bot.sendMessage(chat_id=chat_id, text=text, reply_markup=reply_markup, parse_mode="Markdown")


def reorderStop(chat_id, stop_id):
    custom_stops = getUserStopsList(chat_id)

    #shift stop to the front
    custom_stops.insert(0, custom_stops.pop(custom_stops.index(stop_id)))

    payload = {
        "custom_stops": custom_stops
    }

    #update user_state and custom_stops in database
    db.user_settings.update_one(filter={'chat_id' : chat_id},
                                update={'$set': payload},
                                upsert=True)

    showReorderStopsList(chat_id)


def processmessage(bot, update):
    chat_id = update.message.chat_id
    message_text = update.message.text
    stop_id = getStopID(message_text)
    text = getArrivalsText(stop_id)

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
    global stopsList #use global variable so it only needs to be initialised once
    stopsList = getStopsList()
    stopsList = stopsList["busstops"]
    global stopsDict
    stopsDict = getStopsDict()

    # initialise database
    client = MongoClient(MLABS_DATABASE)
    global db
    db = client.nusbusarrivalbot # select the database

    # Create the Updater and pass it your bot's token.
    updater = Updater(TOKEN)

    # initialise bot
    global bot
    bot = Bot(token=TOKEN)

    # setup webhook
    PORT = int(environ.get('PORT', '5000'))
    updater.start_webhook(listen="0.0.0.0", port=PORT, url_path=TOKEN)
    updater.bot.setWebhook(APP_URL + TOKEN)

    # Use long polling (disabled when webhooks are enabled)
    # updater.start_polling()

    # add handlers
    updater.dispatcher.add_handler(CommandHandler('start', start))
    updater.dispatcher.add_handler(CommandHandler('listallstops', listallstops))
    updater.dispatcher.add_handler(MessageHandler(Filters.location, location))
    updater.dispatcher.add_handler(CallbackQueryHandler(button))
    updater.dispatcher.add_handler(CommandHandler('customise', settings))
    updater.dispatcher.add_handler(CommandHandler('help', help))
    updater.dispatcher.add_handler(MessageHandler(Filters.text, processmessage))
    updater.dispatcher.add_error_handler(error)

    # Run the bot until the user presses Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT
    updater.idle()


if __name__ == "__main__":
    main()
