from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telethon import TelegramClient, events
from configparser import ConfigParser
import requests
import asyncio
from datetime import datetime as dt, timedelta
import json

config = ConfigParser()
config.read('conf.ini')

API_ID = config['CONF']['API_ID']
API_HASH = config['CONF']['API_HASH']
BOT_TOKEN = config['CONF']['BOT_TOKEN']
API_KEY = config['CONF']['API_KEY']
TARGET_CHANNEL_LINK = config['CONF']['TARGET_GROUP_LINK']

client = TelegramClient('bot', API_ID, API_HASH)

scheduler = AsyncIOScheduler()

leagues = [
    'England', 'Spain', 'Germany', 'Italy', 'French'
]


@client.on(events.NewMessage)
async def messageHandler(message):
    print('New Message')


async def getAllFedrations():
    url = "https://football-prediction-api.p.rapidapi.com/api/v2/list-federations"
    headers = {
        'x-rapidapi-key': API_KEY,
        'x-rapidapi-host': "football-prediction-api.p.rapidapi.com"
    }
    response = requests.request("GET", url, headers=headers)
    return response.json()


async def getAllPredictions(date: str, market='classic'):
    url = "https://football-prediction-api.p.rapidapi.com/api/v2/predictions"
    querystring = {"iso_date": date,
                   "market": market, "federation": "UEFA"}
    headers = {
        'x-rapidapi-key': API_KEY,
        'x-rapidapi-host': "football-prediction-api.p.rapidapi.com"
    }
    response = requests.request(
        "GET", url, headers=headers, params=querystring)
    jsonRes = response.json()
    finalList = []
    for pre in jsonRes['data']:
        if pre['competition_cluster'] in leagues and not pre['is_expired']:
            finalList.append(pre)
    return finalList


async def allowedMarkets():
    url = 'https://football-prediction-api.p.rapidapi.com/api/v2/list-markets'
    headers = {
        'x-rapidapi-key': API_KEY,
        'x-rapidapi-host': "football-prediction-api.p.rapidapi.com"
    }
    response = requests.request("GET", url, headers=headers)
    print(response.json())


async def getLeaguePrediction(leagueId):
    url = f"https://football-prediction-api.p.rapidapi.com/api/v2/predictions/{leagueId}"
    headers = {
        'x-rapidapi-key': API_KEY,
        'x-rapidapi-host': "football-prediction-api.p.rapidapi.com"
    }
    response = requests.request("GET", url, headers=headers)
    return response.json()


@scheduler.scheduled_job('cron', hour=8, minute=30)
async def main():
    print(' Sending new predictions!')
    client.parse_mode = 'html'
    now = dt.now()
    predictions = await getAllPredictions(f'{now.year}-{now.month}-{now.day}')
    for pred in predictions:
        prediction = await getLeaguePrediction(pred['id'])
        predictionDetails = prediction['data'][0]
        season = predictionDetails['season']
        homeTeam = predictionDetails['home_team']
        awayTeam = predictionDetails['away_team']
        startDate = predictionDetails['start_date']
        availableMarkets = predictionDetails['available_markets']
        message = f'{homeTeam} vs {awayTeam}\n'
        if 'classic' in availableMarkets:
            status = predictionDetails['prediction_per_market']['classic']['prediction']
            if status == '1':
                p = f'{homeTeam} will win the game.'
            if status == '2':
                p = f'{awayTeam} will win the game.'
            if status == '12':
                p = f'The game will not end in draw. One Teams will win the victory.'
            if status == 'X':
                p = f'Game will end in draw.'
            if status == '1X':
                p = f'{homeTeam} will win the game or the game will end in draw.'
            if status == '2X':
                p = f'{awayTeam} will win the victory or the game will end in draw.'
            message = f'{message} \n{p}'
        if 'over_25' in availableMarkets:
            status = predictionDetails['prediction_per_market']['over_25']['prediction']
            if status == 'yes':
                p = f'There will be more than 2.5 gols scored!'
            if status == 'no':
                p = f'There will not be more than 2.5 goals scored!'
            message = f'{message} \n> {p}'
        if 'over_35' in availableMarkets:
            status = predictionDetails['prediction_per_market']['over_35']['prediction']
            if status == 'yes':
                p = f'There will be more than 3.5 goals scored!'
            if status == 'no':
                p = f'There will not be more than 3.5 goals scored!'
            message = f'{message} \n> {p}'
        if 'btts' in availableMarkets:
            status = predictionDetails['prediction_per_market']['btts']['prediction']
            if status == 'yes':
                p = 'Both tems will score the goals.'
            if status == 'no':
                p = 'Both teams will not score the goals.'
            message = f'{message} \n> {p}'

        await client.send_message(TARGET_CHANNEL_LINK, f'Preiction\n{message}')
        print('Sent')
        await asyncio.sleep(1800)


async def start():
    scheduler.start()
    while True:
        await asyncio.sleep(1000)

client.start(bot_token=BOT_TOKEN)
print(' Bot is running!')
client.loop.run_until_complete(start())
