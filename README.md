# NHL Game Score Tracker

This is a Python script that tracks and provides live updates for Buffalo Sabres NHL hockey games. It uses the NHL API to fetch game information and updates, allowing you to keep track of Sabres games and hear their goal songs when they score.

## Prerequisites

Before running this script, make sure you have the following dependencies installed:

- Python 3.x

You can install the required libraries using the `requirements.txt` file provided:

```bash
pip install -r requirements.txt
```

## Usage

1. Clone this repository or download the `sabres_game_tracker.py` file.

2a. Manually run the script using the following command:

```bash
python sabres_game_tracker.py
```
2b. Automatically run the script (if it is in your documents folder) by running "SabreLamp.command."

## How It Works

The script works by:

1. Checking if there is a Buffalo Sabres game on the current day by using the NHL API.

2. If a game is found, it retrieves the game information, opponent details, and game start time.

3. It then waits for the game to start and provides information about the game, including the opponent and start time.

4. During the game, it continuously checks for score updates and plays the appropriate goal song when the Sabres score a goal.

5. It provides live score updates throughout the game until it's over.

6. After the game is finished, it waits until the next day to check for new games.

## Important Notes

- The script assumes that the Sabres are in the Eastern Time Zone (ET) and calculates game start times accordingly. It may need adjustments for other time zones.

- Ensure that your audio files (goal songs) are in the correct format and their paths are correctly specified in the `SabresGoalSongs.json` file.

- The `audioFiles` folder should be included when you clone the GitHub repository.

- The script uses the NHL API, which may have rate limits and may require an API key for extensive use.

- This script provides basic functionality and can be expanded upon for further customization or integration into other applications.

## License

This script is provided under the MIT License. See the [LICENSE](LICENSE) file for more details.

Feel free to contribute to this project or customize it to meet your specific needs. Enjoy tracking Buffalo Sabres games with their goal songs!
