import read_pfr as rp
import sys
import json


injuries_dir = './data/pfr_pages/injuries'


if len(sys.argv) != 2:
	print("Proper usage:\n pfr_scrape_injuries.py [season]")
	sys.exit()

try:
	season = int(sys.argv[1])
except ValueError:
	print("Proper usage:\n pfr_scrape_injuries.py [season]\nseason must be an integer!")
	sys.exit()


teamids = ['mia','nwe','buf','nyj','pit','rav','cin','cle','jax','oti',
           'htx','clt','kan','sdg','rai','den','phi','dal','was','nyg',
           'min','det','gnb','chi','nor','car','atl','tam','ram','sea',
           'crd','sfo']


for tm in teamids:
    
    # Scrape injury page for this team this season
    page_dict = rp.read_inj_page(tm, season)
    
    # Store the resulting dict of tables as a json file
    inj_file = '{}{}{}.json'.format(injuries_dir,season,tm)
    with open(inj_file, 'w') as f:
        json.dump(page_dict, f)
