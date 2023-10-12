import requests
import datetime
import time
import json
import pygame

# Setting of the global variables. Potentially in the future this can be updated to be usable for all teams
global SABRES_TEAM_ID
global sabresGoalSong

# opens the sabresGoalSong file that points to each player's music file. Not fully up to date with the deadline
# acquisitions. Also initializes pygame and the pygame mixer which is used to play the goal music
sabresGoalSong = json.loads(open('./audioFiles/SabresGoalSongs.json', "r").read())
SABRES_TEAM_ID = 7
pygame.init()
pygame.mixer.init()


# Function that checks if there is a Buffalo Sabres game on the current day. Takes input today in the date format
# YYYY-MM-DD. Called once per day.
def checkForGame(today):
    # Collects all games from the NHL api and formats into .json format
    CHECKGAME_URL = f"https://statsapi.web.nhl.com/api/v1/schedule?date={today}"
    CHECKGAME_response = requests.get(CHECKGAME_URL).json()

    # Finds the timezone of the current user. Tested in eastern time on Windows, macOS, and Ubuntu. Only supports US
    # timezones at present
    timeZone = time.tzname
    timeZoneOffset = {'EST': -4, 'Eastern Standard Time': -4, 'CST': -5, 'Central Standard Time': -5,
                      'MST': -6, 'Mountain Standard Time': -6, 'PST': -7, 'Pacific Standard Time': -7}

    # Gets all games on today
    dates = CHECKGAME_response["dates"]

    for date in dates:
        # Get all the games that are happening today in the NHL and iterate through those games
        games = date["games"]
        for game in games:
            awayTeamID = game["teams"]["away"]["team"]["id"]  # Gets the away team ID
            homeTeamID = game["teams"]["home"]["team"]["id"]  # Gets the home team ID

            # Checks if the Sabres are involved with the game and assigns if they are home or away
            if awayTeamID == SABRES_TEAM_ID or homeTeamID == SABRES_TEAM_ID:
                if awayTeamID == SABRES_TEAM_ID:
                    SabresHomeOrAway = "away"
                    OpHomeOrAway = "home"
                else:
                    SabresHomeOrAway = "home"
                    OpHomeOrAway = "away"

                # Determine the start time of the game in local time
                gameTimeLocal = datetime.datetime.fromisoformat(game["gameDate"][:-1]) \
                                + datetime.timedelta(hours=timeZoneOffset[timeZone[0]])

                # if the Sabres are involved in a game today then the data for the game is returned
                return game["gamePk"], SabresHomeOrAway, OpHomeOrAway, gameTimeLocal
    # Return default values if Sabres are not involved in the game
    return ['-1', -1, -1, '-1']


# Function that pauses the code until the game starts.
def startGameUpdate(gameTimeLocal, opName):
    # Determine how long until the game starts and then prints some information about the game.
    tD = (gameTimeLocal - datetime.datetime.now())
    print('The game today is between your Buffalo Sabres and the ' + str(opName) + '. It starts at ' +
          str(gameTimeLocal.strftime("%H:%M:%S")) + ' local time')
    # If the start time of the game has not passed, wait until 200 seconds before it starts.
    if datetime.datetime.now() < gameTimeLocal:
        print("True")
        time.sleep(tD.seconds - 200)


# Function that does most of the updating throughout the game, checks if the Sabres or their opponent has scored a goal
def duringGameUpdate(SabresHomeOrAway, OpHomeOrAway, LiveGame_url):
    # Private function of duringGameUpdate that plays the goal song of the Sabres' goal scorer. Takes the live data of
    # the currently active game.
    def playGoalSong(goalData_priv):
        # Gets the latest goal scoring event of the current game and the goal scorer's name.
        goalEventNumber = goalData_priv["scoringPlays"][-1]
        playerName = goalData_priv["allPlays"][goalEventNumber]["players"][0]["player"]["fullName"]

        # If the player has a known goal song we play that song otherwise we play the old Sabres' goal song "Let Me
        # Clear My Throat" -DJ Kool.
        if playerName in sabresGoalSong:
            goalSong = sabresGoalSong[playerName]
        else:
            goalSong = sabresGoalSong["default"]

        # Prints the description of the goal to the screen.
        print(goalData_priv["allPlays"][goalEventNumber]["result"]["description"])

        # Plays the song for twenty seconds and then stops it.
        pygame.mixer.music.load(goalSong)
        pygame.mixer.music.play()
        time.sleep(20)
        pygame.mixer.music.stop()

    # Gets the current score of the game for both of the teams in the game.
    LIVEGAME_response = requests.get(LiveGame_url).json()
    # print(LIVEGAME_response["gameData"]["status"]["detailedState"])
    sabres_score = LIVEGAME_response["liveData"]["linescore"]["teams"][SabresHomeOrAway]["goals"]
    opScore = LIVEGAME_response["liveData"]["linescore"]["teams"][OpHomeOrAway]["goals"]

    # Sleeps for 11 seconds. The NHL api game gets mad if you do it more often.
    time.sleep(5)

    # Gets the new score of the game after waiting eleven seconds.
    LIVEGAME_response = requests.get(url).json()
    newSabresScore = LIVEGAME_response["liveData"]["linescore"]["teams"][SabresHomeOrAway]["goals"]
    newOpScore = LIVEGAME_response["liveData"]["linescore"]["teams"][OpHomeOrAway]["goals"]

    # Checks if the game has ended.
    gameOver = LIVEGAME_response["gameData"]["status"]["detailedState"] == "Final"

    # Checks if the Sabres had scored.
    sabreScoreBool = sabres_score < newSabresScore
    opScoreBool = opScore < newOpScore

    # If the Sabres scored call the playing music function.
    if sabreScoreBool:
        LIVEGAME_response = requests.get(url).json()
        goalData = LIVEGAME_response["liveData"]["plays"]
        playGoalSong(goalData)

    if opScoreBool:
        pygame.mixer.music.load('./audioFiles/losing_horn.mp3')
        pygame.mixer.music.play()
        time.sleep(5)
        pygame.mixer.music.stop()

    # Returns the if the Sabres or Opponent scored, the current Sabres' score, their Opponents' score, whether if
    # the game is over.
    return sabreScoreBool, opScore < newOpScore, newSabresScore, newOpScore, gameOver


# Function that prints some extra information to the screen. Created this to clean up main.
def printScoreUpdate(opTeamAbbreviation, opTeamName, opTeamScore, sabresScoreTotal, bufScore, isFinal):
    # Print if Bufflo has scored
    if bufScore:
        print("Buffalo Sabres score! The score of the game is now BUF: " + str(sabresScoreTotal) + " " +
              opTeamAbbreviation + ": " + str(opTeamScore))
    # Print if the game is over
    elif isFinal:
        print("The game is over. The final score was BUF: " + str(sabresScoreTotal) + " " +
              opTeamAbbreviation + ": " + str(opTeamScore))
    # Print if the opponent has scored
    elif not bufScore:
        print(opTeamName + " score. The score of the game is now BUF: " + str(sabresScoreTotal) + " " +
              opTeamAbbreviation + ": " + str(opTeamScore))


# Main code loop
while True:
    # Get today's date and determine what time we should check tomorrow
    FullDateToday = datetime.datetime.now()
    today_date = FullDateToday.strftime("%Y-%m-%d")
    next_date = FullDateToday + datetime.timedelta(days=1)
    next_date = next_date.replace(hour=4, minute=0, second=0, microsecond=0)

    # Call check for game function and returns the gameID (GID), whether the Sabres (SHOA) and their opponent (OHOA)
    # are home or away and game time
    [GID, SHOA, OHOA, GT] = checkForGame(today_date)

    # If there is a Sabres game today do the code
    if not GID == '-1':
        # Get the data for the game opponent abbreviation and name
        url = f"https://statsapi.web.nhl.com/api/v1/game/{GID}/feed/live"
        response = requests.get(url).json()
        oppAbbreviation = response["gameData"]["teams"][OHOA]["abbreviation"]
        oppName = response["gameData"]["teams"][OHOA]["name"]

        # Call start game function
        startGameUpdate(GT, oppName)

        # Play Sabres Theme (well...the old school one anyway)
        pygame.mixer.music.load('./audioFiles/SabreDance.mp3')
        pygame.mixer.music.play()

        # print(GID)
        # Call the during game update function to initialize each of the return variables for the main loop
        [didSabresScore, didOppScore, sabresScore, OpScore, isOver] = duringGameUpdate(SHOA, OHOA, url)

        # Print the score - if we start the program after the game has started this is a current update
        print("The score of the game is now BUF: " + str(sabresScore) + " " +
              oppAbbreviation + ": " + str(OpScore))

        # Loops until the game is over, calling the game update function and printer function
        while not isOver:
            [didSabresScore, didOppScore, sabresScore, OpScore, isOver] = duringGameUpdate(SHOA, OHOA, url)
            if didSabresScore or didOppScore:
                printScoreUpdate(oppAbbreviation, oppName, OpScore, sabresScore, didSabresScore, isOver)

        # Calls print function one last time
        printScoreUpdate(oppAbbreviation, oppName, OpScore, sabresScore, didSabresScore, isOver)

    # Wait until tomorrow
    print("I'm waiting till tomorrow.")
    time.sleep((next_date - datetime.datetime.now()).seconds)
