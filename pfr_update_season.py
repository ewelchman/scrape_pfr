import read_pfr as rp
import json
import os
import sys


### Location of json file containing information for all games
datapath = "/home/welced12/googledrive/nfl_data/devl/pfr_gamedata.json"


if len(sys.argv) != 2:
	print("Proper usage:\n pfr_update_season.py [season]")
	sys.exit()

try:
	year = int(sys.argv[1])
except ValueError:
	print("Proper usage:\n pfr_update_season.py [season]\nseason must be an integer!")
	sys.exit()

# Read season schedule page for specified season
season_dict = rp.read_season_sched( year )

if ('games' in season_dict.keys()) or ('all_games' in season_dict.keys()):
    
    # Load existing games from json file
    games_dict = {}
    if os.path.isfile( datapath ):
        with open(datapath, 'r') as f:
            games_dict = json.load(f)                
        print("Loaded existing games")
            
    # Update value for this particular season with new table
    print("Updating game data from",year)
    games_dict[str(year)] = season_dict
    print("Writing game data to",datapath)
    
    # Write resulting overall dictionary to file
    with open(datapath, 'w') as f:
        json.dump(games_dict, f)
        
else:
    print("Page for"+str(year)+"doesn't have a 'games' table")
