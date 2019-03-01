# Scrape pfr

This repo contains scripts that I use to scrape NFL data from <http://pro-football-reference.com>, as well as scripts to parse the raw tables and produce data files for analysis.

## Summary and proper usage
* `pfr_update_season.py [season]`

  Script for scraping one complete season of NFL games and adding/creating a .json file containing the results.

* `pfr_scrape_week.py [season] [week]`

  Script for scraping PFR pages for one week of NFL games. For each game, the script scrapes all tables from the corresponding boxscore page. Outputs one .json file for each game in the selected week.

* `pfr_scrape_injuries.py [season]`

  Scrape each team's injury designations for a particular season. [Example](https://www.pro-football-reference.com/teams/clt/2018_injuries.htm)

* `pfr_parseplays.py`

  Parse detailed play-by-play tables from all boxscore files currently available. Outputs one .csv file

* `pfr_parsestats.py [season]`

  Parse individual player stats from all boxscore files currently available for a given season. Outputs a .csv file for a the given season.
