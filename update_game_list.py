import read_pfr as rp
import json
import os

datapath = "/home/welced12/googledrive/nfl_data/devl/gamedata.json"

# Load existing games from json file
games_dict = {}
if os.path.isfile( datapath ):
	with open(datapath, 'r') as f:
		games_dict = json.load(f)

for year in range(2017,2018):
	# Check whether games dictionary has results for a particular season
	if 
	season_dict = rp.read_season_sched( year )['games']


# 
