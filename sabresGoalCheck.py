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
import sys

matplotlib.use('agg')

# opens the sabresGoalSong file that points to each player's music file. Not fully up to date with the deadline
# acquisitions. Also initializes pygame and the pygame mixer which is used to play the goal music
sabresGoalSong = json.loads(open('./audioFiles/SabresGoalSongs.json', "r").read())
SABRES_TEAM_ID = 7


# Function that checks for a game on the present day. NHL api only passes data a week at a time so we need to parse
# the entire week.
def checkForGame(url):
    """Checks for a game on the present day
        url is the address of the NHL API
    """
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


# Function that pauses the code until the game starts. It also handles plotting the shot and goal data if the game
# has already started.
def startGameUpdate(gameTimeLocal, opName, gameURL, gameRosters):
    """
    Determine how long until the game starts and print information about the game.

    Parameters:
    - gameTimeLocal (datetime): The local start time of the game.
    - opName (str): The name of the opposing team.
    - gameURL (str): The URL to fetch game events data.
    - gameRosters (list): List of player rosters with information like playerId, sweaterNumber, etc.

    Returns:
    Tuple (pd.DataFrame, pd.DataFrame): A tuple containing two Pandas DataFrames:
        1. sabresShots: DataFrame with columns 'x' and 'y' representing Sabres' shots on goal coordinates.
        2. sabresGoals: DataFrame with columns 'x', 'y', 'SN' (sweater number), and 'EN' (event order),
           representing Sabres' goals coordinates and scorer information.

    Note:
    The function uses the gameTimeLocal to calculate the time remaining until the game starts,
    fetches game events using the provided URL, and extracts relevant information about Sabres' shots
    and goals. The information is returned as Pandas DataFrames.
    """

    # Determine how long until the game starts and then prints some information about the game.
    tD = (gameTimeLocal - datetime.datetime.now())
    print('The game today is between the Sabres and the ' + str(opName) + '. It starts at ' +
          str(gameTimeLocal.strftime("%H:%M:%S")) + ' local time')
    # If the start time of the game has not passed, wait until 15 seconds before it starts.
    if datetime.datetime.now() < gameTimeLocal:
        time.sleep(tD.seconds - 15)
        playsound.playsound('./audioFiles/SabreDance.mp3')
        return -1, -1, -1, -1, -1
    else:
        events = requests.get(gameURL).json()['plays']
        scorerNumber = -1
        sabresShots = []
        sabresGoals = []
        opShots = []

        if events:
            for event in events:
                if event['typeDescKey'] == 'shot-on-goal':
                    data = event['details']
                    if data['eventOwnerTeamId'] == 7:
                        sabresShots.append(np.array([data['xCoord'], data['yCoord'], event['sortOrder']]))
                    else:
                        opShots.append(np.array([data['xCoord'], data['yCoord'], event['sortOrder']]))
                elif event['typeDescKey'] == 'goal':
                    data = event['details']
                    if data['eventOwnerTeamId'] == 7:
                        for player in gameRosters:
                            if data['scoringPlayerId'] == player['playerId']:
                                scorerNumber = player['sweaterNumber']
                        sabresGoals.append(np.array([data['xCoord'], data['yCoord'], scorerNumber, event['sortOrder']]))

        period = events[-1]['period']
        timeRemaining = events[-1]['timeRemaining']

        sabresShots = pd.DataFrame(sabresShots, columns=['x', 'y', 'EN'])
        opShots = pd.DataFrame(opShots, columns=['x', 'y', 'EN'])
        sabresGoals = pd.DataFrame(sabresGoals, columns=['x', 'y', 'SN', 'EN'])
        return sabresShots, sabresGoals, opShots, period, timeRemaining


# Function that does most of the updating throughout the game, checks if the Sabres or their opponent has scored
# a goal
def duringGameUpdate(SabresHomeOrAway, OpHomeOrAway, LiveGame_url, Rosters, sleepTime):
    """
    Update function for ongoing hockey games, checking if the Sabres or their opponent scored a goal.

    Parameters:
    - SabresHomeOrAway (str): Indicates whether the Sabres are playing at home or away ('home' or 'away').
    - OpHomeOrAway (str): Indicates whether the opponent is playing at home or away ('home' or 'away').
    - LiveGame_url (str): The URL to fetch live game data.
    - Rosters (list): List of player rosters with information like playerId, sweaterNumber, etc.
    - sleepTime (int): The amount of time that the app should wait between polling

    Returns:
    Tuple (bool, bool, int, int, bool, dict, list): A tuple containing the following information:
        1. Sabres scored (bool): True if Sabres scored a goal during the update, False otherwise.
        2. Opponent scored (bool): True if the opponent scored a goal during the update, False otherwise.
        3. New Sabres score (int): The updated score of the Sabres.
        4. New Opponent score (int): The updated score of the opponent.
        5. Game over (bool): True if the game is over, False otherwise.
        6. Sabres goal information (dict): Dictionary with information about the latest Sabres goal with keys:
            - 'x': x-coordinate of the goal.
            - 'y': y-coordinate of the goal.
            - 'SN': Sweater number of the goal scorer.
            - 'EN': Event order of the goal.
        7. Sabres shots (list): List of arrays representing Sabres' shots on goal with columns 'x', 'y', and 'EN'.

    Note:
    The function fetches live game data, compares the scores before and after a brief delay, and checks for goal events.
    If Sabres or the opponent scores, it prints information about the goal and plays the corresponding goal song.
    The function returns relevant information about the game status.
    """

    def playGoalSong(goalData_priv, URL):
        """
        Play the goal song associated with the latest goal-scoring event in a hockey game and print goal information.

        Parameters:
        - goalData_priv (list): List of goal-scoring events data for the current game.
        - URL (str): The URL to fetch the latest game events data.

        Returns:
        dict: Dictionary containing information about the latest goal event with keys:
            - 'x': x-coordinate of the goal.
            - 'y': y-coordinate of the goal.
            - 'SN': Sweater number of the goal scorer.
            - 'EN': Event order of the goal.

        Note:
        The function uses the provided goal data and URL to fetch the latest goal-scoring event information.
        It extracts details about the scorer, assists, and plays the corresponding goal song. The goal information
        is then printed to the screen.
        """
        # Initialize variables and iterate to find the latest goal-scoring event
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

        # Extract information about the scorer and assists
        scorerID = goalData_priv[i + 1]['details']['scoringPlayerId']
        assist1ID = goalData_priv[i + 1]['details'].get('assist1PlayerId', -1)
        assist2ID = goalData_priv[i + 1]['details'].get('assist2PlayerId', -1)

        # Iterate through player rosters to find names and numbers
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

        # Determine the goal song based on the scorer's name
        goalSong = sabresGoalSong.get(scorerName, sabresGoalSong["default"])

        # Print goal information to the screen
        printStatement = f'Buffalo Sabres Score! Scored by number {scorerNumber}, {scorerName}.'

        if not assist2ID == -1:
            printStatement += f' Assists to number {assist1Number}, {assist1Name}, and number {assist2Number}, {assist2Name}.'
        elif not assist1ID == -1:
            printStatement += f' Assists to number {assist1Number}, {assist1Name}.'

        print(printStatement)

        # Play the goal song for twenty seconds and then stop it
        playsound.playsound(goalSong)
        time.sleep(20)

        # Return information about the goal
        return {'x': goalData_priv[i + 1]['details']['xCoord'],
                'y': goalData_priv[i + 1]['details']['yCoord'],
                'SN': scorerNumber,
                'EN': goalData_priv[i + 1]['sortOrder']}

    sabresGoalInfo = {'x': -1, 'y': -1, 'SN': -1, 'EN': -1}
    sabresShot = []
    opShot = []

    # Gets the current score of the game and number of plays
    LIVEGAME_response = requests.get(LiveGame_url).json()
    sabres_score = LIVEGAME_response[SabresHomeOrAway]['score']
    opScore = LIVEGAME_response[OpHomeOrAway]['score']
    numPlays = len(LIVEGAME_response['plays'])

    # Sleeps for 10 seconds to avoid overloading the NHL API
    time.sleep(sleepTime)

    # Gets the new score after a brief delay
    LIVEGAME_response = requests.get(LiveGame_url).json()
    newSabresScore = LIVEGAME_response[SabresHomeOrAway]['score']
    newOpScore = LIVEGAME_response[OpHomeOrAway]['score']
    newNumPlays = len(LIVEGAME_response['plays'])

    # Checks if the Sabres had scored, opponent scored, or if the game has ended
    sabreScoreBool = sabres_score < newSabresScore
    opScoreBool = opScore < newOpScore
    playsBool = numPlays < newNumPlays
    gameOver = LIVEGAME_response['gameState'] == "FINAL"

    if opScoreBool:
        playsound.playsound('./audioFiles/losing_horn.mp3')

    if sabreScoreBool:
        LIVEGAME_response = requests.get(LiveGame_url).json()
        goalData = LIVEGAME_response["plays"]
        sabresGoalInfo = playGoalSong(goalData, LiveGame_url)

    if playsBool:
        print(newNumPlays, sabres_score, newSabresScore)
        i = numPlays
        while i < newNumPlays:
            i += 1
            event = LIVEGAME_response['plays'][i - 1]
            print(event['typeDescKey'])
            if event['typeDescKey'] == 'shot-on-goal':
                if event['details']['eventOwnerTeamId'] == SABRES_TEAM_ID:
                    sabresShot.append(
                        np.array([event['details']['xCoord'], event['details']['yCoord'], event['sortOrder']]))
                else:
                    opShot.append(
                        np.array([event['details']['xCoord'], event['details']['yCoord'], event['sortOrder']]))

    period = LIVEGAME_response['plays'][-1]['period']
    timeRemaining = LIVEGAME_response['plays'][-1]['timeRemaining']

    return sabreScoreBool, opScoreBool, newSabresScore, newOpScore, gameOver, sabresGoalInfo, sabresShot, opShot, period, timeRemaining


def printScoreUpdate(opTeamAbbreviation, opTeamName, opTeamScore, sabresScoreTotal, bufScore, isFinal):
    """
    Print score updates based on game events.

    Parameters:
    - opTeamAbbreviation (str): Abbreviation of the opponent team.
    - opTeamName (str): Name of the opponent team.
    - opTeamScore (int): Opponent team's score.
    - sabresScoreTotal (int): Total score of the Buffalo Sabres.
    - bufScore (bool): True if Buffalo Sabres scored, False otherwise.
    - isFinal (bool): True if the game is over, False otherwise.

    Returns:
    None

    Note:
    This function prints score updates based on game events, indicating if the game is over or if the opponent has scored.
    """
    if isFinal:
        print(f"The game is over. The final score was BUF: {sabresScoreTotal} {opTeamAbbreviation}: {opTeamScore}")
    elif not bufScore:
        print(
            f"{opTeamName} scored. The score of the game is now BUF: {sabresScoreTotal} {opTeamAbbreviation}: {opTeamScore}")


def argumentHandling(arg, args):
    """
    Handle command-line arguments by finding the value associated with a specific argument.

    Parameters:
    - arg (str): The argument to search for.
    - args (list): List of command-line arguments.

    Returns:
    str or None: The value associated with the given argument, or None if the argument is not found or has no value.
    """
    try:
        index = args.index(arg)
        if index + 1 < len(args):
            return args[index + 1]
    except ValueError:
        pass
    return None


def main(page: ft.Page):
    """
    Main function to run a continuous loop monitoring Buffalo Sabres hockey game updates.

    Parameters:
    - page (ft.Page): An object representing the flet page to display live updates.

    Returns:
    None

    Note:
    This function continuously checks for Buffalo Sabres hockey game updates using the NHL API.
    It fetches live game data, plots shots and goals on a rink image, and displays live score updates.
    The loop runs until the game is over, and then it waits until the next day to resume checking for games.
    """

    def guiUpdate(plotStatus):
        def plotter():
            """
            Plotting function to visualize shots and goals on a rink image.

            Parameters:
            - plot_status (int): Status flag for plotting operations:
                - 0: Initialize the plot.
                - 1: Update shots on the existing plot.
                - 2: Update goals on the existing plot.

            Returns:
            None
            """
            if plotStatus == 0:
                print('init')
                page.title = "Sabres Goal Lamp - GUI"
            elif plotStatus == 1:
                plt.cla()
                print("tried to update shots")
            else:
                plt.cla()
                print("tried to update goals")

            fig, axs = plt.subplots(1, 1)

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
            if len(sabresGoals["x"]) > 0:
                rink.text("x", "y", s="SN", ax=axs, ha="center", va="center", fontsize=14, data=sabresGoals,
                          c='#FFFFFF')
            plt.savefig('./rink.jpg', bbox_inches='tight')

        def getGoalData():
            scorers = []
            for number in sabresGoals['SN']:
                for player in rosters:
                    if number == player['sweaterNumber']:
                        statement = ft.Text(f'Number {number}, ' + player['firstName']['default'] + ' ' + \
                                            player['lastName']['default'])
                        scorers.append(statement)
            return scorers

        def valueUpdate():
            rinkImage.src = './rink.jpg'
            periodNumData.value = f'Period: {periodNum}'
            timeRemainingData.value = f'Time: {timeRemainingPeriod}'
            sabresScoreData.value = f'Sabres: {sabresScore}'
            opScoreData.value = f'{oppName}: {OpScore}'
            sabresShotData.value = f'Sabres: {len(sabresShots.index)}'
            opShotData.value = f'{oppName}: {len(opShots.index)}'

        plotter()
        getGoalData()

        if plotStatus == 0:
            rinkImage = ft.Image()
            periodNumData = ft.Text(size=15, weight=ft.FontWeight.BOLD)
            timeRemainingData = ft.Text(size=15, weight=ft.FontWeight.BOLD)
            sabresScoreData = ft.Text(size=15, weight=ft.FontWeight.BOLD)
            opScoreData = ft.Text(size=15, weight=ft.FontWeight.BOLD)
            sabresShotData = ft.Text(size=15, weight=ft.FontWeight.BOLD)
            opShotData = ft.Text(size=15, weight=ft.FontWeight.BOLD)
            valueUpdate()
            periodData = ft.Row(
                controls=[
                    ft.Column(
                        controls=[
                            periodNumData
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        width=257
                    ),
                    ft.Column(
                        controls=[
                            timeRemainingData
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        width=257
                    )
                ],
                alignment=ft.MainAxisAlignment.START
            )

            print(timeRemainingPeriod)

            gameScore = ft.Row(
                controls=[
                    ft.Column(
                        controls=[
                            sabresScoreData
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        width=257
                    ),
                    ft.Column(
                        controls=[
                            opScoreData
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        width=257
                    )
                ],
                alignment=ft.MainAxisAlignment.START
            )

            gameShots = ft.Row(
                controls=[
                    ft.Column(
                        controls=[
                            sabresShotData
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        width=257
                    ),
                    ft.Column(
                        controls=[
                            opShotData
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        width=257
                    )
                ],
                alignment=ft.MainAxisAlignment.START
            )

            print(sabresShots.index)

            rinkData = ft.Column(
                controls=[
                    ft.Text('Rink Image', size=30, weight=ft.FontWeight.BOLD),
                    rinkImage,
                    periodData,
                    gameScore,
                    gameShots
                ],
                height=page.height,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER
            )

            goalScorerData = ft.Column(
                controls=getGoalData()
            )

            goalData = ft.Column(
                controls=[
                    ft.Text('Goal Data', size=30, weight=ft.FontWeight.BOLD),
                    goalScorerData
                ],
                height=page.height,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER
            )

            mainPage = ft.Row(
                controls=[
                    rinkData,
                    goalData
                ],
                width=page.width,
                alignment=ft.MainAxisAlignment.SPACE_EVENLY
            )

            page.add(mainPage)
        else:
            valueUpdate()
            page.update()

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

            sabresGoals = pd.DataFrame(columns=['x', 'y', 'SN', 'EN'])
            sabresShots = pd.DataFrame(columns=['x', 'y', 'EN'])
            opShots = pd.DataFrame(columns=['x', 'y', 'EN'])

            if 'periodNum' not in locals():
                periodNum = 'Pre-Game'
                timeRemainingPeriod = "20:00"
                sabresScore = 0
                OpScore = 0

            if gui:
                guiUpdate(0)

            # Call start game function
            [sabresShots, sabresGoals, opShots, periodNum, timeRemainingPeriod] = startGameUpdate(GT, oppName, url,
                                                                                                  rosters)

            [_, _, sabresScore, OpScore, isOver, _, _, _, _, _] = duringGameUpdate(SHOA, OHOA, url, rosters, 0)
            # Calls the plotter function to initialize it if the user wants the GUI
            if gui:
                guiUpdate(0)

            # Print the score - if we start the program after the game has started this is a current update
            print("The score of the game is now BUF: " + str(sabresScore) + " " +
                  oppAbbreviation + ": " + str(OpScore))

            # Main loop for when the game is going on
            while not isOver:
                # Updates if the game is going on

                [didSabresScore, didOppScore, sabresScore, OpScore, isOver, sabresGoal, sabresShot, OpShot, periodNum,
                 timeRemainingPeriod] = duringGameUpdate(SHOA, OHOA, url, rosters, 10)
                # Plots if there was a sabres shot on goal
                if sabresShot and gui:
                    sabresShots = pd.concat([sabresShots, pd.DataFrame(sabresShot, columns=['x', 'y', 'EN'])],
                                            ignore_index=True)
                    guiUpdate(1)

                if OpShot and gui:
                    opShots = pd.concat([opShots, pd.DataFrame(OpShot, columns=['x', 'y', 'EN'])],
                                        ignore_index=True)
                    guiUpdate(1)

                # Prints to the screen if the sabres scored. If the GUI is active plot to the screen.
                if didSabresScore:
                    printScoreUpdate(oppAbbreviation, oppName, OpScore, sabresScore, didSabresScore, isOver)
                    if sabresGoal['SN'] != -1:
                        sabresGoals = pd.concat([sabresGoals, pd.DataFrame([sabresGoal])], ignore_index=True)
                    if gui:
                        guiUpdate(2)

                # Print score if the opponent has scored.
                if didOppScore:
                    printScoreUpdate(oppAbbreviation, oppName, OpScore, sabresScore, didSabresScore, isOver)

            # Calls print function one last time
            printScoreUpdate(oppAbbreviation, oppName, OpScore, sabresScore, didSabresScore, isOver)

        # Wait until tomorrow
        print("I'm waiting till tomorrow.")
        time.sleep((next_date - datetime.datetime.now()).seconds)


# Extract command-line arguments excluding the script name
args = sys.argv[1:]

# Check if the '-g' flag is present in the arguments
if '-g' in args:
    # Retrieve the value following the '-g' flag using the argumentHandling function
    value = argumentHandling('-g', args)

    # If the value is evaluated as True, set gui to True; otherwise, set it to False
    if eval(value):
        gui = True
    else:
        gui = False
else:
    # If the '-g' flag is not present, set gui to False by default
    gui = False

if '-w' in args:
    value = argumentHandling('-w', args)

    if eval(value):
        webUI = True
    else:
        webUI = False
else:
    webUI = False

# Check if gui mode is disabled
if gui:
    if webUI:
        # Launch the flet app with the main function as the target for visualization
        ft.app(target=main, assets_dir='./', view=ft.AppView.WEB_BROWSER)
    else:
        ft.app(target=main, assets_dir='./')
else:
    # Run the main function without visualization if gui mode is enabled
    main(-1)
