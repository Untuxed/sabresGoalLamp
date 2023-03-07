# Sabres Goal Lamp Code

I am by no means a software engineer and there are definitly more efficient ways to do this but I wanted to make it available to anyone that wanted to try it out. This code will update every morning to check if there is a Buffalo Sabres game and wait until the game starts. Then when the Sabres score a goal the goal scorers goal song will play. This is version one of this code and in the future I plan to update it to include hardware support. 

It uses the NHL api and is about 30 seconds behind cable but I think I have it as close as it can be as I poll the api as often as allowed by the NHL. 

This should work on all operating systems (tried on MacOS, Windows, and Ubuntu). This code requires Python 3. To use this code, download this repository and navigate to the installed folder using the command line (terminal on MacOS, cmd on Windows) and install the required libraryies use the requirements.txt file.

```pip3 install -r requirements.txt```

Once in the downloaded folder and all the external libraries are installed used the command in your terminal window: 

```python3 /path-to-code/sabresGoalCheck.py```

Then press enter/return and the code will begin running. It will run until you stop it by pressing control+c or closing the terminal window. 
