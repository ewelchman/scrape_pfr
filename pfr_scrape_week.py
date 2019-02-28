import read_pfr as rp
import pandas as pd
import sys
import json
import time


### Location of game history json file
#gamelistpath = '/home/welced12/googledrive/nfl_data/devl/pfr_gamedata.json'
gamelistpath = '/home/welced12/git/football_analytics/pfr_pages/pfr_gamedata.json'


if len(sys.argv) != 3:
	print("Proper usage:\n pfr_scrape_week.py [season] [week]")
	sys.exit()

try:
	season = int(sys.argv[1])
	week = int(sys.argv[2])
except ValueError:
	print("Proper usage:\n pfr_scrape_week.py [season] [week]\nseason and week must be integers!")
	sys.exit()


# Get season/week as strings. Better for use as dict keys
yr = str(season)
wk = str(week)

# Load game history from file
t = 0
while t < 5:
    try:
        with open(gamelistpath, 'r') as f:
            games_dict = json.load(f)
        print("Took",t+1,"tries to read",gamelistpath)
        t = 5
    except:
        t += 1
        time.sleep(0.1)
        if t==5:
            print("Failed to read",gamelistpath)


# Make DataFrame of games for specified season
if yr in games_dict.keys():
    if ('games' in games_dict[yr].keys()):
        season_df = pd.DataFrame(games_dict[yr]['games'])
    elif ('all_games' in games_dict[yr].keys()):
        season_df = pd.DataFrame(games_dict[yr]['all_games'])
        
    week_df = season_df[season_df.week_num == wk]
    gameids = week_df.boxscore_word_href.values
    gameurls = ['https://www.pro-football-reference.com'+gid for gid in gameids]
    
    # Scrape boxscore page for each of the gameids.
    for gid in gameids:
        
        game_dict = rp.read_game_page( gid )
        
        # Store the resulting dictionary of tables as a json
#        basedir = '/home/welced12/googledrive/nfl_data/devl/pfr_'
        basedir = '/home/welced12/git/football_analytics/pfr_pages/'
        gamefile = basedir+gid.lstrip('/').split('.')[0]+".json"
        tries = 0
        while tries < 5:
            try:
                with open(gamefile, 'w') as f:
                    json.dump(game_dict, f)
#                print(" ^ Took",tries+1,"tries to save tables to",gamefile)
                tries = 5
            except:
                tries += 1
                time.sleep(0.1*tries)
                if tries == 5:
                    print("Failed to write tables to",gamefile)
    
else:
    print("No games on file for",yr)
