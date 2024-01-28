import requests
import datetime
import time
import json
import playsound
import pandas as pd
import numpy as np
from hockey_rink import NHLRink, RinkImage
import matplotlib
import matplotlib.pyplot as plt
import flet as ft
from flet.matplotlib_chart import MatplotlibChart
import sys

matplotlib.use('agg')

# Setting of the global variables. Potentially in the future this can be updated to be usable for all teams
global SABRES_TEAM_ID
global sabresGoalSong

# opens the sabresGoalSong file that points to each player's music file. Not fully up to date with the deadline
# acquisitions. Also initializes pygame and the pygame mixer which is used to play the goal music
sabresGoalSong = json.loads(open('./audioFiles/SabresGoalSongs.json', "r").read())
SABRES_TEAM_ID = 7


def main(page: ft.Page):
    def checkForGame(url):
        CHECKGAME_response = requests.get(url).json()

        # Finds the timezone of the current user. Tested in eastern time on Windows, macOS, and Ubuntu. Only supports US
        # timezones at present
        timeZone = time.tzname
        # timeZoneOffset = {'EST': -4, 'Eastern Standard Time': -4, 'CST': -5, 'Central Standard Time': -5,
        #                   'MST': -6, 'Mountain Standard Time': -6, 'PST': -7, 'Pacific Standard Time': -7}
        timeZoneOffset_daylightSavings = {'EST': -5, 'Eastern Standard Time': -5, 'CST': -6,
                                          'Central Standard Time': -6,
                                          'MST': -7, 'Mountain Standard Time': -7, 'PST': -8,
                                          'Pacific Standard Time': -8}

        # Gets all games on today
        daysOfWeek = CHECKGAME_response["gameWeek"]

        for day in daysOfWeek:
            if day['date'] == url[-10:]:
                # Get all the games that are happening today in the NHL and iterate through those games
                games = day["games"]
                for game in games:
                    awayTeamID = game['awayTeam']['id']  # Gets the away team ID
                    homeTeamID = game['homeTeam']['id']  # Gets the home team ID

                    # Checks if the Sabres are involved with the game and assigns if they are home or away
                    if awayTeamID == SABRES_TEAM_ID or homeTeamID == SABRES_TEAM_ID:
                        if awayTeamID == SABRES_TEAM_ID:
                            SabresHomeOrAway = "awayTeam"
                            OpHomeOrAway = "homeTeam"
                        else:
                            SabresHomeOrAway = "homeTeam"
                            OpHomeOrAway = "awayTeam"

                        # Determine the start time of the game in local time
                        gameTimeLocal = datetime.datetime.fromisoformat(game["startTimeUTC"][:-1]) \
                                        + datetime.timedelta(hours=timeZoneOffset_daylightSavings[timeZone[0]])

                        # if the Sabres are involved in a game today then the data for the game is returned
                        return game["id"], SabresHomeOrAway, OpHomeOrAway, gameTimeLocal
        # Return default values if Sabres are not involved in the game
        return ['-1', -1, -1, '-1']

    # Function that pauses the code until the game starts.
    def startGameUpdate(gameTimeLocal, opName):
        # Determine how long until the game starts and then prints some information about the game.
        tD = (gameTimeLocal - datetime.datetime.now())
        print('The game today is between the Sabres and the ' + str(opName) + '. It starts at ' +
              str(gameTimeLocal.strftime("%H:%M:%S")) + ' local time')
        # If the start time of the game has not passed, wait until 200 seconds before it starts.
        if datetime.datetime.now() < gameTimeLocal:
            time.sleep(tD.seconds - 15)
            playsound.playsound('./audioFiles/SabreDance.mp3')

    # Function that does most of the updating throughout the game, checks if the Sabres or their opponent has scored
    # a goal
    def duringGameUpdate(SabresHomeOrAway, OpHomeOrAway, LiveGame_url, Rosters):
        # Private function of duringGameUpdate that plays the goal song of the Sabres' goal scorer. Takes the live data
        # of the currently active game.
        def playGoalSong(goalData_priv, URL):
            i = -1
            eventType = goalData_priv[i]['typeDescKey']
            while not eventType == 'goal':
                eventType = goalData_priv[i]['typeDescKey']
                i = i - 1
                if i <= -5:
                    i = -1
                    goalData_priv = requests.get(URL).json()["plays"]

            if i == -1:
                i = -2

            # Gets the latest goal scoring event of the current game and the goal scorer's name.
            scorerID = goalData_priv[i + 1]['details']['scoringPlayerId']

            if 'assist1PlayerId' in goalData_priv[i + 1]['details']:
                assist1ID = goalData_priv[i + 1]['details']['assist1PlayerId']
            else:
                assist1ID = -1

            if 'assist2PlayerId' in goalData_priv[i + 1]['details']:
                assist2ID = goalData_priv[i + 1]['details']['assist2PlayerId']
            else:
                assist2ID = -1

            for player in Rosters:
                if player['playerId'] == scorerID:
                    scorerName = player['firstName']['default'] + ' ' + player['lastName']['default']
                    scorerNumber = player['sweaterNumber']
                if not assist1ID == -1:
                    if player['playerId'] == assist1ID:
                        assist1Name = player['firstName']['default'] + ' ' + player['lastName']['default']
                        assist1Number = player['sweaterNumber']
                if not assist2ID == -1:
                    if player['playerId'] == assist2ID:
                        assist2Name = player['firstName']['default'] + ' ' + player['lastName']['default']
                        assist2Number = player['sweaterNumber']

            # If the player has a known goal song we play that song otherwise we play the old Sabres' goal song "Let Me
            # Clear My Throat" -DJ Kool.
            if scorerName in sabresGoalSong:
                goalSong = sabresGoalSong[scorerName]
            else:
                goalSong = sabresGoalSong["default"]

            # Prints the description of the goal to the screen.
            printStatement = 'Buffalo Sabres Score! Scored by number ' + str(scorerNumber) + ', ' + scorerName + '.'

            if not assist2ID == -1:
                printStatement = printStatement + ' Assists to number ' + str(assist1Number) + ', ' + assist1Name + \
                                 ', and number ' + str(assist2Number) + ', ' + assist2Name + '. '
            elif not assist1ID == -1:
                printStatement = printStatement + ' Assists to number ' + str(assist1Number) + ', ' + assist1Name + '.'

            print(printStatement)

            # Plays the song for twenty seconds and then stops it.
            playsound.playsound(goalSong)
            time.sleep(20)
            return {'x': goalData_priv[i + 1]['details']['xCoord'], 'y': goalData_priv[i + 1]['details']['yCoord'],
                    'SN': scorerNumber, 'EN': goalData_priv[i + 1]['sortOrder']}

        sabresGoalInfo = {'x': -1, 'y': -1, 'SN': -1, 'EN': -1}
        sabresShot = []
        # Gets the current score of the game for both of the teams in the game.
        LIVEGAME_response = requests.get(LiveGame_url).json()
        sabres_score = LIVEGAME_response[SabresHomeOrAway]['score']
        opScore = LIVEGAME_response[OpHomeOrAway]['score']
        numPlays = len(LIVEGAME_response['plays'])

        # Sleeps for 10 seconds. The NHL api game gets mad if you do it more often.
        time.sleep(10)

        # Gets the new score of the game after waiting eleven seconds.
        LIVEGAME_response = requests.get(LiveGame_url).json()
        newSabresScore = LIVEGAME_response[SabresHomeOrAway]['score']
        newOpScore = LIVEGAME_response[OpHomeOrAway]['score']
        newNumPlays = len(LIVEGAME_response['plays'])

        # Checks if the Sabres had scored.
        sabreScoreBool = sabres_score < newSabresScore
        opScoreBool = opScore < newOpScore
        playsBool = numPlays < newNumPlays

        # Checks if the game has ended.
        gameOver = LIVEGAME_response['gameState'] == "FINAL"

        if playsBool:
            print(newNumPlays, sabres_score, newSabresScore)
            if sabreScoreBool:
                LIVEGAME_response = requests.get(LiveGame_url).json()
                goalData = LIVEGAME_response["plays"]
                sabresGoalInfo = playGoalSong(goalData, LiveGame_url)
            if opScoreBool:
                playsound.playsound('./audioFiles/losing_horn.mp3')
            i = numPlays
            print(i, newNumPlays)
            while i < newNumPlays:
                i += 1
                event = LIVEGAME_response['plays'][i - 1]
                print(event['typeDescKey'])
                if event['typeDescKey'] == 'shot-on-goal' and event['details']['eventOwnerTeamId'] == SABRES_TEAM_ID:
                    sabresShot.append(np.array([event['details']['xCoord'], event['details']['yCoord']]))

        # Returns the if the Sabres or Opponent scored, the current Sabres' score, their Opponents' score, whether if
        # the game is over.
        return sabreScoreBool, opScore < newOpScore, newSabresScore, newOpScore, gameOver, sabresGoalInfo, sabresShot

    def printScoreUpdate(opTeamAbbreviation, opTeamName, opTeamScore, sabresScoreTotal, bufScore, isFinal):
        # Print if the game is over
        if isFinal:
            print("The game is over. The final score was BUF: " + str(sabresScoreTotal) + " " +
                  opTeamAbbreviation + ": " + str(opTeamScore))
        # Print if the opponent has scored
        elif not bufScore:
            print(opTeamName + " score. The score of the game is now BUF: " + str(sabresScoreTotal) + " " +
                  opTeamAbbreviation + ": " + str(opTeamScore))

    def plotter(plotStatus):
        if plotStatus == 0:
            print('init')
            fig, axs = plt.subplots(1, 1)
        elif plotStatus == 1:
            plt.close()
            print("tried to update shots")
        else:
            plt.close()
            print("tried to update goals")
        rink = NHLRink(
            sabresLogo={
                'feature_class': RinkImage,
                'image_path': 'https://upload.wikimedia.org/wikipedia/en/thumb/9/9e/Buffalo_Sabres_Logo.svg/240px'
                              '-Buffalo_Sabres_Logo.svg.png',
                "x": 0, "length": 27, "width": 27,
                "zorder": 15, "alpha": 0.5,
            }
        )
        rink.scatter('x', 'y', data=sabresShots, ax=axs, marker='X', c='#003087')
        rink.scatter("x", "y", ax=axs, facecolor="#003087", edgecolor="black", s=300, data=sabresGoals)
        rink.text("x", "y", s="SN", ax=axs, ha="center", va="center", fontsize=14, data=sabresGoals, c='#FFFFFF')
        page.add(MatplotlibChart(fig, expand=True))

    # Main code loop
    baseAPIURL = 'https://api-web.nhle.com/'
    while True:
        FullDateToday = datetime.datetime.now()
        today_date = FullDateToday.strftime("%Y-%m-%d")
        next_date = FullDateToday + datetime.timedelta(days=1)
        next_date = next_date.replace(hour=4, minute=0, second=0, microsecond=0)

        [GID, SHOA, OHOA, GT] = checkForGame(baseAPIURL + f'v1/schedule/{today_date}')

        # If there is a Sabres game today do the code
        if not GID == '-1':
            # Get the data for the game opponent abbreviation and name
            url = f"https://api-web.nhle.com/v1/gamecenter/{GID}/play-by-play"
            response = requests.get(url).json()
            oppAbbreviation = response[OHOA]["abbrev"]
            oppName = response[OHOA]["name"]['default']

            rosters = response['rosterSpots']

            # Call start game function
            startGameUpdate(GT, oppName)

            sabresGoals = pd.DataFrame(columns=['x', 'y', 'SN', 'EN'])
            sabresShots = pd.DataFrame(columns=['x', 'y', 'EN'])

            if not headless:
                plotter(0)

            [_, _, sabresScore, OpScore, isOver, _, _] = duringGameUpdate(SHOA, OHOA, url, rosters)

            # Print the score - if we start the program after the game has started this is a current update
            print("The score of the game is now BUF: " + str(sabresScore) + " " +
                  oppAbbreviation + ": " + str(OpScore))

            while not isOver:
                [didSabresScore, didOppScore, sabresScore, OpScore, isOver, sabresGoal, shots] = \
                    duringGameUpdate(SHOA, OHOA, url, rosters)
                if shots and not headless:
                    sabresShots = pd.concat([sabresShots, pd.DataFrame(shots, columns=['x', 'y'])], ignore_index=True)
                    plotter(1)

                if didSabresScore:
                    printScoreUpdate(oppAbbreviation, oppName, OpScore, sabresScore, didSabresScore, isOver)
                    if sabresGoal['SN'] != -1:
                        sabresGoals = pd.concat([sabresGoals, pd.DataFrame([sabresGoal])], ignore_index=True)
                    if not headless:
                        plotter(2)
                elif didOppScore:
                    printScoreUpdate(oppAbbreviation, oppName, OpScore, sabresScore, didSabresScore, isOver)

            # Calls print function one last time
            printScoreUpdate(oppAbbreviation, oppName, OpScore, sabresScore, didSabresScore, isOver)

        # Wait until tomorrow
        print("I'm waiting till tomorrow.")
        time.sleep((next_date - datetime.datetime.now()).seconds)


def argumentHandling(arg, args):
    try:
        index = args.index(arg)
        if index + 1 < len(args):
            return args[index + 1]
    except ValueError:
        pass
    return None


args = sys.argv[1:]
if '-h' in args:
    value = argumentHandling('-h', args)

    if eval(value):
        headless = True
    else:
        headless = False
else:
    headless = True

if not headless:
    ft.app(target=main)
else:
    main(-1)
