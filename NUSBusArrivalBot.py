import logging
from telegram import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler

import requests
import json
from geopy.distance import vincenty
from bs4 import BeautifulSoup

from credentials import TOKEN

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

#bot functions

#sends a welcome message to the user
#also initialises the customised ReplyKeyboard
def start(bot, update):
    chat_id = update.message.chat_id

    #initialise custom keyboard
    keyboard = []
    sendLocationButton = KeyboardButton(text="Get nearest stops", request_location=True)
    keyboard.append(["/getstops", sendLocationButton])

    reply_markup = ReplyKeyboardMarkup(keyboard)

    text = "Hello! This is a telegram bot for getting the arrival timings of NUS busses."
    bot.sendMessage(chat_id, text, reply_markup=reply_markup)

#uses the global variable stopsList
def getstops(bot, update):
    chat_id = update.message.chat_id

    #craft inline keyboard
    keyboard = []
    for stop in stopsList:
        buttonText = stop["caption"]
        keyboard.append([InlineKeyboardButton(buttonText, callback_data=stop["name"])])

    reply_markup = InlineKeyboardMarkup(keyboard)
    text = "Pick a stop:"

    bot.sendMessage(chat_id=chat_id, text=text, reply_markup=reply_markup)

#gives user a list of 5 nearest bus stops
def location(bot, update):
    chat_id = update.message.chat_id
    latitude = update.message.location.latitude
    longitude = update.message.location.longitude

    queryPoint = (latitude, longitude)

    #get nearest stops
    nearestStops = getNearestStops(queryPoint)

    #craft the inlinekeyboard buttons
    keyboard = []
    for stop in nearestStops:
        buttonText = stop["caption"]
        keyboard.append([InlineKeyboardButton(buttonText, callback_data=stop["name"])])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = "Here are the 5 closest bus stops:"

    bot.sendMessage(chat_id=chat_id, text=text, reply_markup=reply_markup)

#gives user the bus arrival timings based on the stop selected
def button(bot, update):
    query = update.callback_query
    chat_id = query.message.chat_id
    message_id = query.message.message_id

    #Disable the keyboard while the information is being retrieved
    text = "Retrieving bus arrival timings...\n"
    text = text + "Please hold on :)"
    bot.editMessageText(chat_id=chat_id, text=text, message_id=message_id)

    text = getArrivalsText(query.data)

    bot.editMessageText(chat_id=chat_id, text=text, message_id=message_id)

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
    # stopsList = getStopsList()
    #use local data for now
    with open('stops.json', 'r') as json_data:
        stopsList = json.load(json_data)
    stopsList = stopsList["busstops"]

    # Create the Updater and pass it your bot's token.
    updater = Updater(TOKEN)

    updater.dispatcher.add_handler(CommandHandler('start', start))
    updater.dispatcher.add_handler(CommandHandler('getstops', getstops))
    updater.dispatcher.add_handler(MessageHandler(Filters.location, location))
    updater.dispatcher.add_handler(CallbackQueryHandler(button))
    updater.dispatcher.add_handler(CommandHandler('help', help))
    updater.dispatcher.add_error_handler(error)

    # Start the Bot
    updater.start_polling()

    # Run the bot until the user presses Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT
    updater.idle()

if __name__ == "__main__":
    main()
