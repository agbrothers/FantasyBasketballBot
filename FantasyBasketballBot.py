import re
import sys
import otp
import time
import datetime
import numpy as np
import pandas as pd
from collections import deque
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains


class WebBot():
    """
    
    Fundamental Bot Superclass
    -------     
     : Contains basic webdriver methods for chrome browser access with selenium
          
    """
    def __init__(self):
        self.driver = webdriver.Chrome(executable_path="/usr/local/bin/chromedriver")
        
    def relaunch(self):
        self.driver = webdriver.Chrome(executable_path="/usr/local/bin/chromedriver")
        
    def back(self):
        self.driver.execute_script("window.history.go(-1)")

    def go(self, url, wait=3):
        # Smarter nav + optional delay to avoid bot detection
        if self.driver.current_url != url:
            self.driver.get(url)
            time.sleep(wait)    
          
        

class Eyes(WebBot):
    """
    
    The Eyes of the Bot
    -------
     : Superclass for the Fantasy Basketball Bot 
     
     : Inherits the WebBot Class
     
     : Contains Methods for reading data from ESPN's fantasy site
     
     : Stores data for later decision making
     
    -------
    Assumptions
        A gmail account was used to create the ESPN account (Necessary for automating login process)
    
    """
    
    def __init__(self, username, password, team_url):
        WebBot.__init__(self)
        self.un = username
        self.pw = password
        self.team_url = team_url
        self.login_url = 'https://www.espn.com/login'
        self.day = datetime.datetime.today().weekday()
        
        # Initializing Methods
        self._check_url()
        self._login()
        self.team_name = self.fetch_name()
        self.score = self.fetch_score()
        self.games_played, self.max_games = self.fetch_games()
        self.roster = self.fetch_stats('Roster')
        # self.free_agents = self.fetch_stats('Free Agents')


    def _check_url(self):      
        """
        
        Verifies that the team url passed to the bot is 
        valid and reformats it in-place for future use
        -------

        """
        
        base = 'https://fantasy.espn.com/basketball/team?'
        try:
            league = re.findall('leagueId=\d{8}', self.team_url)[0]
            season = re.findall('seasonId=\d{4}', self.team_url)[0]
            team = re.findall('teamId=\d+', self.team_url)[0]
            self.team_url = base + league + '&' + season + '&' + team
            self.free_agents_url = 'https://fantasy.espn.com/basketball/players/add?' + league
        except Exception:
            sys.exit('''Error: There is an issue with the team url provided.  Please use a link of the form:\n 
                     https://fantasy.espn.com/basketball/team?leagueId=12345678&seasonId=2021&teamId=1''')
    
    
    def _login(self):
        """
        
        Logs in to the ESPN account using the credentials provided
        -------

        """
        try:
            self.driver.get(self.login_url) 
            iframe = self.driver.find_elements_by_tag_name('iframe')[0]
            self.driver.switch_to.frame(iframe)
            
            # Enter Login Credentials
            un_element = self.driver.find_element_by_xpath('//input[@type="email"]')
            un_element.send_keys(self.un)
            pw_element = self.driver.find_element_by_xpath('//input[@type="password"]')
            pw_element.send_keys(self.pw)          
            pw_element.send_keys(Keys.ENTER)
            
            # Get the One Time Password from the given gmail account to login
            try:
                time.sleep(20)
                one_time_passcode = otp.get_espn(user_id=self.un)
                # one_time_passcode = input(f'Please enter the one-time-passcode sent to {self.un}')
                otp_element = self.driver.find_element_by_xpath('//input[@name="code"]')
                otp_element.send_keys(one_time_passcode)
                otp_element.send_keys(Keys.ENTER)
                time.sleep(5)     
            except Exception:
                return      
            
        except Exception:
            sys.exit(f'Error: There was an issue logging in to {self.login_url}.  Please check the credentials provided and retry.')


    def _load_tables(self):
        """
        
        Returns all <table> elements present on a given page as single DataFrame
        -------

        """
        try:
            html = self.driver.page_source
            soup=BeautifulSoup(html,'html.parser')
            div=soup.select_one("div")
            tables=pd.read_html(str(div))
            df = tables[0]
            for i in range(1,len(tables)):
                df = df.join(tables[i])
            return df
        except Exception:
            print(f'[ERROR] No Tables found on {self.driver.current_url}')


    def fetch_name(self):
        """
        
        Returns the team's name
        -------
        
        """
        self.go(self.team_url)     
        team_name = self.driver.find_element_by_xpath('//span[@class="teamName truncate"]').text
        return team_name
    
    
    def fetch_score(self):
        """
        
        Returns the current matchup score
        -------
        
        """
        self.go(self.team_url)     
        away = '//li[@class="ScoreboardScoreCell__Item flex items-center relative pb2 ScoreboardScoreCell__Item--away"]/div/div/a/div'
        home = '//li[@class="ScoreboardScoreCell__Item flex items-center relative pb2 ScoreboardScoreCell__Item--home"]/div/div/a/div'
        try:
            if self.driver.find_element_by_xpath(away).text == self.team_name:
                score = self.driver.find_element_by_xpath(away[:-10] + '[2]').text
            elif self.driver.find_element_by_xpath(home).text == self.team_name:
                score = self.driver.find_element_by_xpath(home[:-10] + '[2]').text
            else:
                print('[ERROR] Current Score Element couldn\'t be found!')
                return
            return score
        except Exception:
            print('[ERROR] An exception occurred while querying for the current score')
            
            
    def fetch_games(self):
        """
        
        IF the league has game limits:
            Returns the current number of games played and the weekly game limit
        -------
        ELSE:
            Returns the 0 games played and inf for the weekly limit
        
        """
        # Open current matchup page
        xpath = '//a[@class="AnchorLink matchup-link"]'
        link_element = self.driver.find_elements_by_xpath(xpath)[-1]
        link = link_element.get_attribute('href')
        self.go(link)
        
        # Find and grab current number of games played
        try:
            name_element = self.driver.find_element_by_xpath(f"//span[@title='{self.team_name}']")       
            game_element = name_element.find_element_by_xpath("../../../../../../descendant::td[contains(text(), 'games played')]")
            
            games = game_element.text
            games = games.split(' ')[1]
            games_played = int(games.split('/')[0])  
            max_games = int(games.split('/')[1])  
            
        except Exception:
            games_played = 0
            max_games = np.inf
            
        return games_played, max_games
    
    
    def fetch_lineup(self, current_page=True):
        """
        
        Returns the roster of players and their current corresponding slots
        -------
        
        """
        if not current_page: self.go(self.team_url)
        roster = self._load_tables()
        
        # Fix multi-index column names
        roster.columns = [col[1] for col in roster.columns]
        roster = roster[['Player','SLOT']]     
        
        # Fix Player Column Formatting
        roster = self._split_players(roster.copy())
        
        # Ignore IR Slot
        roster = roster.drop(len(roster)-1) 
        
        return roster
        
            
    def fetch_stats(self, target='Roster'):
        """
        
        Returns the roster of players, their 7-day statistics, 
        and season projections as a DataFrame
        -------
        
        """
        if target == 'Roster':
            url = self.team_url
        else:
            url = self.free_agents_url
                
        stat_ext = '&statSplit=last7'
        proj_ext = '&view=stats&statSplit=projections'
        sched_ext = '&view=schedule'
        
        # Scrape the stats tables
        self.go(url + stat_ext)
        roster = self._load_tables()
        roster.columns = [col[1] for col in roster.columns]
        roster.drop(columns=['action','opp','STATUS'], inplace=True)
        
        # Fix the player column formatting
        roster = self._split_players(roster.copy())
        
        # Scrape the 2021 Projections
        self.go(url + proj_ext)
        projections = self._load_tables()['Fantasy Pts']
        projections.rename(columns={'tot':'proj_tot','avg':'proj_avg'}, inplace=True)
        roster = roster.join(projections)
        
        # Scrape the schedule tables
        self.go(url + sched_ext)
        sched = self._load_tables()
        
        # Add schedule data only if in the current week's matchup
        dates = ['opp'] + list(sched['Upcoming Schedule'].columns)
        sched.columns = [col[1] for col in sched.columns]
        for i in range(7-self.day):
            roster[f'D{i+1+self.day}'] = [0 if val=='--' else 1 for val in sched[dates[i]]]
            
        # Ignore IR Slot
        roster = roster.drop(len(roster)-1) 
        return roster


    def _split_players(self, roster):
        """
        
        Fixes Player Column Formatting
        -------
        Splits player column strings into their individual components
        i.e.  Player, Inj, Team, Pos1, Pos2
        
        -------
        EX :  Player                        Player           Inj    Team  Pos1  Pos2
              "DeMar DeRozanOSASG, SF"  ->  "DeMar DeRozan"  "OUT"  "SA"  "SG"  "SF"
        
        -------
        Returns modified DataFrame
        
        """
        
        for i in range(len(roster)): 
            player_str =  roster.loc[i, 'Player']
            if player_str == 'Empty': 
                continue
            elif type(player_str) == float:
                roster = roster.drop(i)
                continue
                
            # Extract Player Second Position
            player_str = player_str.split(', ')
            roster.loc[i, 'Pos2'] = player_str[-1] if len(player_str)==2 else None
            player_str = player_str[0]
    
            # Extract Player First Position            
            k = -1 if player_str[-1]=='C' else -2
            roster.loc[i, 'Pos1'] = player_str[k:]
            player_str = player_str[:k]   
    
            # Extract Player Name
            name = re.findall('[A-Z][^A-Z]', player_str[::-1])[0]
            name_index = -1 * (player_str[::-1].index(name)+1)
            roster.loc[i, 'Player'] = player_str[:name_index]  
            
            # Extract Player Team & Injury Status
            status = player_str[name_index:]
            if 'DTD' in status:
                roster.loc[i, 'Team'] = status.replace('DTD','')
                roster.loc[i, 'Inj'] = 'DTD'
            elif status[0]=='O' and status[:3] not in ['Orl', 'OKC']:
                roster.loc[i, 'Team'] = status[1:]
                roster.loc[i, 'Inj'] = 'OUT'    
            else:
                roster.loc[i, 'Team'] = status
                roster.loc[i, 'Inj'] = 0 
                
        roster = roster.reset_index(drop=True)
        return roster
    
    
    
class Limbs(Eyes):
    """
    
    The Limbs of the Bot
    -------
     : Superclass for the Fantasy Basketball Bot 
     
     : Inherits the Eyes Class
     
     : Contains methods for interacting with page elements
       
     : Executes instructions to move players
     
    """
        
    # super(MyModel, self).__init__()
    def __init__(self, username, password, team_url):
        Eyes.__init__(self, username, password, team_url)
                            
    def move_player(self, move):
        try: # Hide any navigation banners that may obstruct button presses
            js = '''\
                document.getElementsByClassName('jsx-1647358489 NavSecondary fba')[0].setAttribute("hidden","");
                document.getElementsByClassName('navigation__container sticky top-0 Site__Header')[0].setAttribute("hidden","");
                '''
            self.driver.execute_script(js)
            time.sleep(0.25)
        except Exception:
            pass
        button = self.driver.find_element_by_xpath(f'//button[@aria-label="Select {move[0]} to move"]')
        actions = ActionChains(self.driver) # For scrolling to buttons
        actions.move_to_element(button).perform()
        button.click()
        time.sleep(0.25)
        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);var lenOfPage=document.body.scrollHeight;return lenOfPage;")

        pos_titles = {'C':'Center',
             'PF':'Power Forward',
             'SF':'Small Forward',
             'PG':'Point Guard',
             'SG':'Shooting Guard',
             'G':'Guard',
             'F':'Forward',
             'U0':'Util',
             'U1':'Util',
             'U2':'Util',
             'Bench':'Bench'
             }
        i = 0
        if 'U' in move[1]:
            i = int(move[1][1])
        elif move[1] == 'Bench':
            i = -1
        pos_title = pos_titles[move[1]]
        pos_div = self.driver.find_elements_by_xpath(f"//div[@title='{pos_title}']")[i]        
        pos_button = pos_div.find_element_by_xpath("../../descendant::button")
        
        actions = ActionChains(self.driver) # For scrolling to buttons
        actions.move_to_element(pos_button).perform()
        pos_button.click()        
        
        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);var lenOfPage=document.body.scrollHeight;return lenOfPage;")
        time.sleep(1.25)
    
    
    def _set_lineup(self, moves):
        # Initially move everyone to the bench  
        existing_lineup = self.fetch_lineup()
        for i,player in existing_lineup.iterrows():
            if player['SLOT'] != 'Bench' and player['Player'] != 'Empty': 
                moves.appendleft((player['Player'],'Bench'))
                
        for move in moves:
            self.move_player(move)
        return moves
    


class FantasyBasketballBot(Limbs):
    """
    
    The Brain of the Bot
    -------     
     : Inherits the Limbs Class
    
     : Contains decision making methods for setting lineups based on the current matchup
      
    """
    
    # super(MyModel, self).__init__()
    def __init__(self, username, password, team_url):
        Limbs.__init__(self, username, password, team_url) 
        self.get_matchup()
    
    
    def _get_lineup(self, players):
        """
        GREEDY ALGORITHM
          Given a ranked list of players
          Fill the lineup greedily from top to bottom slot
        """
        
        index = ['PG', 'SG', 'SF', 'PF', 'C', 'G', 'F', 'U0', 'U1', 'U2']
        positions = {'PG':['PG','G','U0','U1','U2'],
                     'SG':['SG','G','U0','U1','U2'],
                     'PF':['PF','F','U0','U1','U2'],
                     'SF':['SF','F','U0','U1','U2'],
                     'C':['C','U0','U1','U2']
                     }
        
        moves = deque()        
        lineup = pd.DataFrame(columns=['Player','Pos1','Pos2'], index=index)
        
        for i,player in players.iterrows():
            possible_pos = set(positions[player['Pos1']])
            
            if not pd.isna(player['Pos2']):
                pos2 = positions[player['Pos2']]
                possible_pos = possible_pos.union(set(pos2))
            
            # loop through possible_pos vector until a slot can be filled (if possible)
            if lineup.loc[possible_pos].isnull().any()[0]:
                invalid_pos = list(set(index) - set(possible_pos))
                available_pos = lineup.drop(invalid_pos)
                available_pos = available_pos[available_pos['Player'].isnull()]
                slot = available_pos.index[0]
                
                lineup.loc[slot] = player[['Player','Pos1','Pos2']]
                moves.append((player['Player'], slot))
        return moves, lineup['Player']
    
    
    
    def get_matchup(self):
        """
        GREEDY ALGORITHM
          Move all non-game players to bench
          Move all util players to lineup
          Move all bench players to util / lineup
          return optimally ordered roster df
          
        """
        num_games = self.max_games - self.games_played
        self.go(self.team_url)
        
        # Build & Order the Potential Roster of Players for the week
        roster = self.roster.sort_values(by='avg', ascending=False, ignore_index=True).copy()
        healthy_players = roster[roster['Inj'] == 0]
        DTD_players = roster[roster['Inj'] == 'DTD']   
        potential_roster = healthy_players.append(DTD_players).reset_index(drop=True)
        
        days = [f'D{day}' for day in np.arange(self.day+1,8)]
        games = potential_roster[days].values
        
        count = 0
        for i in range(games.shape[0]):
            for j in range(games.shape[1]):
                if games[i][j]==1 and count < num_games:
                    count+=1
                else:
                    games[i][j]=0
        
        matchup = pd.DataFrame(columns=days, data=games)
        matchup[['Player','Pos1','Pos2']] = potential_roster[['Player','Pos1','Pos2']]
        
        # Get Current Scoring Period for page navigation
        xpath = '//a[@class="AnchorLink matchup-link"]'
        scoring_period_link = self.driver.find_elements_by_xpath(xpath)[-1].get_attribute('href')
        scoring_period = scoring_period_link.split('scoringPeriodId=')[-1]
        scoring_period = int(scoring_period.split('&')[0])
            
        for i,day in enumerate(days):
            # Skip current day if games have already started (hardcoded 6pm CT, change this)
            now = datetime.datetime.now()
            now = int(now.strftime("%H"))
            if i==0 and now >= 18: # make 18
                continue
            day_link = self.team_url + f'&scoringPeriodId={scoring_period + i}'
            self.go(day_link)
        
            players = matchup[matchup[day] == 1][['Player','Pos1','Pos2']]
            players = players.reset_index(drop=True)
            
            moves, lineup = self._get_lineup(players)
            if 'week_lineup' not in locals():
                week_lineup = pd.DataFrame(lineup)
            else:
                week_lineup = week_lineup.join(lineup)
            week_lineup = week_lineup.rename(columns={'Player':day})
            
            self._set_lineup(moves)
        self.matchup = week_lineup
        self.roster = self.fetch_stats()
        return    
    
        
if __name__ == '__main__':
    
    # Example login credentials, replace these with your own.  
    username = 'name@gmail.com'
    password = 'password123'
    team_url = 'https://fantasy.espn.com/basketball/team?leagueId=12345678&seasonId=2021&teamId=1'

    # The bot will set the week's lineup upon initialization
    bot = FantasyBasketballBot(username, password, team_url)        
            
