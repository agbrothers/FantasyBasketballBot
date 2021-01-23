# FantasyBasketballBot
  This is a bot I built to automate retrieving stats, making roster decisions, and setting my lineup for weekly matchups.  
  This code fully automates the entire process from logging in to actually moving players into the correct positions to 
  optimize weekly points.  

  The code is organized into two modules, (FantasyBasketballBot.py) containing classes that make up the bot, 
  and (otp.py) containing methods for retrieving one-time-passcodes from the gmail account linked to the user's 
  espn account utilizing the gmail API.
  
  Please keep in mind that bot is still a work in progress and a lot of code has yet to be cleaned up / optimized.  
  That being said, it still works fully as intended on MacOS.  Let me know if you encounter and bugs / oversights.  



# SETUP
  The bot utilizes chromedriver to connect and interact with espn.com. Downloads for chromedriver can be found here:
  https://sites.google.com/a/chromium.org/chromedriver/downloads
  
  To get personal credentials for the gmail API and to authorize this program to access gmail, follow the steps at the following link:
  https://developers.google.com/gmail/api/quickstart/python
  
  Following the instructions there will generate a "credentials.json" file which you should place in the same directory as the files in this repository.

  Alternatively, if you don't want to give the program gmail access, if you have trouble getting the gmail API setup, or if your ESPN account 
  isn't linked to a gmail account, you can modify the code to enable manual logins within FantasyBasketballBot.py > Eyes class > _login method

  To do this you can remove the line: 

          one_time_passcode = otp.get_espn(user_id=self.un)

  and replace it with:

          one_time_passcode = input(f'Please enter the one-time-passcode sent to {self.un}')

  enabling you to manually input the passcode into the console to log in.  This line is already commented out in the code for convenience.  



# FUTURE FEATURES 
   Evaluate the weekly opponent's team, determine their optimal lineup for the week, predict their score, and calculate a probability of winning/losing.  

   Suggest actions to take if the opponent has a higher probability of winning.

   Smarter algorithm for determining the optimal lineup (Potentially using a regression model to predict player performance per game).  The current decision making process is naive and only utilizes 7-day avg scores.  
