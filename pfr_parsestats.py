import os
import json
import pandas as pd
import read_pfr as rp
import time
import sys


# File locations
gamelistpath = '/home/welced12/googledrive/nfl_data/devl/pfr_gamedata.json'
boxscore_path = '/home/welced12/git/football_analytics/pfr_pages/boxscores'
injuries_path = '/home/welced12/git/football_analytics/pfr_pages/injuries'
parsedstats_dir = '/home/welced12/googledrive/nfl_data/devl/parsed_ind_stats/'


usage = 'Proper usage:\npython pfr_parsestats.py [season]\nOR\npython pfr_parsestats.py [start_season] [end_season]'

if len(sys.argv) == 3:
	try:
		start_season = int(sys.argv[1])
		end_season = int(sys.argv[2])
	except:
		print(usage)
		sys.exit()
elif len(sys.argv) == 2:
	try:
		start_season = int(sys.argv[1])
		end_season = int(sys.argv[1])
	except:
		print(usage)
		sys.exit()
else:
	print(usage)
		
	
teamids = ['mia','nwe','buf','nyj','pit','rav','cin','cle','jax','oti',
           'htx','clt','kan','sdg','rai','den','phi','dal','was','nyg',
           'min','det','gnb','chi','nor','car','atl','tam','ram','sea',
           'crd','sfo']
team_to_id = {x.upper():x for x in teamids}
team_to_id['LAC'] = 'sdg'
team_to_id['LAR'] = 'ram'
team_to_id['STL'] = 'ram'
team_to_id['IND'] = 'clt'
team_to_id['BAL'] = 'rav'
team_to_id['TEN'] = 'oti'
team_to_id['OAK'] = 'rai'
team_to_id['ARI'] = 'crd'
team_to_id['HOU'] = 'htx'


def get_homeaway(gameinfo_df, gid):
    return_dict = {}
    bl = [True if gid in str(x) else False for x in gameinfo_df.boxscore_word_href.values]
    game_row = gameinfo_df[bl]
    
    # If game_location == @, then winner is visiting team.
    if len(game_row.index) == 1:
        idx = game_row.index[0]
        if game_row.loc[idx,'game_location'] == "@":
            vis = game_row.loc[idx,'winner_href'].split('/')[2]
            home = game_row.loc[idx,'loser_href'].split('/')[2]
        else:
            vis = game_row.loc[idx,'loser_href'].split('/')[2]
            home = game_row.loc[idx,'winner_href'].split('/')[2]
        # Get 3-letter short-form team name for home and visitor
        return_dict['home'] = rp.three_letter_code[home+game_row.loc[idx,'season']].upper()
        return_dict['vis'] = rp.three_letter_code[vis+game_row.loc[idx,'season']].upper()

        return return_dict
    

def get_snaps(g_dict, gameinfo_df, gid):
    snaps_tables = [
        pd.DataFrame(g_dict[x]) for x in ('home_snap_counts',
                                          'vis_snap_counts')
    ]
    
    # Add team column
    homeaway = get_homeaway(gameinfo_df, gid)
    if 'home' in homeaway:
        snaps_tables[0]['team'] = homeaway['home']
    if 'vis' in homeaway:
        snaps_tables[1]['team'] = homeaway['vis']
    
    snaps_df = pd.concat(snaps_tables,sort=False)
    #print(snaps_df)
    return snaps_df


def merge_snaps(stats_df, snaps_df):
    # Create merged DataFrame
    merged = stats_df.merge(
        snaps_df,
        how='right',
        left_on='player_href',
        right_on='player_href',
        suffixes=('_y','')
    )
    # Clean up columns
    merged_df = merged.drop( columns=['player_a_y'] )
    
    # Keep only players with offensive snaps
    bl = [True if int(x) > 0 else False for x in merged_df.offense.values]
    merged_df = merged_df[ bl ]
    
    return merged_df


def parse_pfr_ind_stats(g_dict, gameinfo_df, gid):
    offense_stats_df = pd.DataFrame(g_dict['player_offense'])
    
    # Drop rows with nan for player id
    stats_df = offense_stats_df.dropna(subset=['player_href'])
    
    # Drop columns that are now unused (column is filled with nan's)
    stats_df = stats_df.dropna(axis=1, how='all')
    
    # Fill remaining nan values with 0
    stats_df = stats_df.fillna(0)
    stats_df = stats_df.replace('',0)
    
    if 'home_snap_counts' in g_dict:
        # pull DataFrame with snaps data from game dict
        snaps_df = get_snaps(g_dict, gameinfo_df, gid)
        # Merge snaps data with stats dataframe
        stats_df = merge_snaps(stats_df, snaps_df)

    return stats_df


def fix_columns(ind_stats_df):
    # Sort resulting dataframe
    ind_stats_df.sort_values(
        by=['player_href','season','week'],
        ascending=[True,True,True],
        inplace=True
    )
    # Re-order, rename columns
    ind_stats_df.rename(
        index=str, 
        columns={
            'offense':'snaps_off', 'off_pct':'snaps_off_pct',
            'defense':'snaps_def', 'def_pct':'snaps_def_pct',
            'special_teams':'snaps_st', 'st_pct':'snaps_st_pct'
        },
        inplace=True
    )
    column_order = [
        'season','week','gid','team','player_href','player_a','pos',
        'pass_att','pass_cmp','pass_yds','pass_long','pass_td','pass_int',
        'pass_sacked','pass_rating',
        'rush_att','rush_yds','rush_td','rush_long','fumbles','fumbles_lost',
        'targets','rec','rec_yds','rec_td','rec_long',
        'snaps_off','snaps_off_pct','snaps_def','snaps_def_pct','snaps_st','snaps_st_pct'
    ]
    cols = [c for c in column_order if c in ind_stats_df.columns]
    return ind_stats_df[cols]


def fill_season_stats(df):
    # Define columns that will be zeroed vs. NaN for missing weeks
    stat_columns = [
        'pass_att','pass_cmp','pass_yds','pass_long','pass_td','pass_int',
        'pass_sacked','pass_rating',
        'rush_att','rush_yds','rush_td','rush_long','fumbles','fumbles_lost',
        'targets','rec','rec_yds','rec_td','rec_long'
    ]
    
    print("Filling out stats for missing weeks for all players")
    
    # Make a copy of stats_df to write in. Keep original for faster querying
    write_df = df.copy(deep=True)
    
    t1 = time.time()
    # Get player's stats, sorted by season, week
    for i, player in enumerate(df.player_href.unique()):
        plyr_rows = df[df.player_href==player]
        name = plyr_rows['player_a'].values[0]
        for yr in plyr_rows['season'].unique():
            ssn_rows = plyr_rows[plyr_rows.season==yr]
            ssn_tms = ssn_rows[['week','team']].set_index('week').to_dict()
            # Get first team player is listed as playing for this season
            for wk in range(1,18):
                try:
                    current_team = ssn_tms['team'][str(wk)]
                    break
                except:
                    pass
            #print(current_team)
            #print(ssn_tms)
            for wk in range(1,18):
                # Check for an entry from a particular week
                qry = plyr_rows[
                    (plyr_rows.season == str(yr)) &
                    (plyr_rows.week == str(wk))
                ]
                # Check if current team changes
                if str(wk) in ssn_tms['team']:
                    current_team = ssn_tms['team'][str(wk)]
                if not len(qry.index) >= 1:
                    # Add a row to the DataFrame for this week
                    row = {k:0 for k in stat_columns}
                    row['player_href'] = player
                    row['player_a'] = name
                    row['season'] = str(yr)
                    row['week'] = str(wk)
                    row['team'] = current_team
                    if 'pos' in plyr_rows.columns:
                        row['pos'] = plyr_rows.pos.values[0]
                    write_df = write_df.append(pd.Series(row), ignore_index=True)
                    
        if ((i+1)%200 == 0):
            t2 = time.time() - t1
            total_plyrs = len(df.player_href.unique())
            txt = ' - Finished {} of {} players in {:.1f} seconds'.format(i+1,total_plyrs,t2)
            print(txt)
            
    print(' - Finished in {} seconds'.format(time.time()-t0))
                    
    return write_df


def parse_teamyear_injuries(stats_df, yr, tm):
    # Filter for stats for this team, this season
    tmyr_filter = [
        True if ((team_to_id[t] == tm) & (ssn == yr))
        else False for (t,ssn) in zip(stats_df.team.values,
                                      stats_df.season.values)
    ]
    tmyr_df = stats_df[ tmyr_filter ]

    # Load injury tables for this team, this season
    inj_file = '{}/{}{}.json'.format(injuries_path, yr, tm)
    with open(inj_file, 'r') as f:
        inj_dict = json.load(f)
    inj_df = pd.DataFrame(inj_dict['team_injuries'])
    playrate_df = pd.DataFrame(inj_dict['team_injuries_totals'])
    rates = {
        inj: pct for (inj, pct) in zip(playrate_df.injury_type.values,
                                       playrate_df.pct.values)
    }
    for k in rates:
        rates[k] = float(str(rates[k]).strip("%"))/100.0

    # For each player who has stats, check for a row in inj_df
    for plyr in tmyr_df.player_href.unique():
        plyr_inj = inj_df[ inj_df.player_href == plyr ]

        # If you find a row, add injury to stats_df
        if len(plyr_inj.index) >= 1:

            # Get index of relevant row in injury DataFrame
            inj_idx = plyr_inj.index[0]

            # Get table of just that player's stats
            plyr_stats = tmyr_df[tmyr_df.player_href==plyr]

            # For index of each row in that stats table, get relevant injury status
            for stats_idx in plyr_stats.index:
                try:
                    wk_col = 'week_'+str(stats_df.loc[stats_idx,'week'])
                    status = inj_df.loc[ inj_idx, wk_col ][0]

                    stats_df.loc[ stats_idx, 'inj' ] = status

                    prob_of_playing = rates[ status.split(':')[0] ]
                    stats_df.loc[ stats_idx, 'playrate' ] = prob_of_playing
                except:
                    # No injury for this player this week. Add nothing to stats_df
                    pass

                
    return stats_df


def add_injuries(stats_df, yr):
    
    print("Adding injury status to player stat lines")

    for tm in [team_to_id[tm] for tm in stats_df.team.unique()]:
        if int(yr) >= 2009:
            stats_df = parse_teamyear_injuries(stats_df, yr, tm)

    return stats_df


### Re-configured MAIN from above
t0 = time.time()

# Load game history DF
with open(gamelistpath, 'r') as f:
    gamehist_dict = json.load(f)
season_dfs = []
for ssn in gamehist_dict.keys():
    season_df = pd.DataFrame(gamehist_dict[ssn]['games'])
    season_df['season'] = ssn
    season_dfs.append(season_df)
gamehist_df = pd.concat(season_dfs, sort=False)

for season in [str(s) for s in range(start_season,end_season+1)]:
#	print(season)
#for season in [s for s in gamehist_df['season'].unique()][-1:]:
    
    print("Working on games from",season)

    # Select rows for just this season from the game history
    bl = [
        True if ((ssn == season) & 
                 (str(box) != 'nan') &
                 (wk in [str(n) for n in range(18)] ) ) 
        else False
        for (ssn, wk, box) in zip(gamehist_df.season.values,
                                  gamehist_df.week_num.values,
                                  gamehist_df.boxscore_word_href.values)
    ]
    games_to_lookup = gamehist_df[ bl ]
        
    # Get individual stats tables from each of the games from this season
    season_game_dfs = []
    for (box_link, wk) in zip(games_to_lookup.boxscore_word_href.values,
                              games_to_lookup.week_num.values):
        try:
            gid = str(box_link).split('/')[2].split('.')[0]
            fname = boxscore_path+'/'+gid+'.json'
            
            # Read stats for this particular game
            g_dict = {}
            with  open(fname, 'r') as f:
                g_dict = json.load(f)
                
            # Pull stats tables and snaps data from the game page
            df = parse_pfr_ind_stats(g_dict, games_to_lookup, gid)
            df['gid'] = gid
            df['season'] = season
            df['week'] = wk
            
            season_game_dfs.append(df)
            
        except:
            print("Failed to get player stats from",box_link)
            

    # Concat stats tables from individual games into one table for the whole season
    ind_stats_df = pd.concat(season_game_dfs, sort=False)
    
    # Sort resulting DataFrame and fix column names/order
    ind_stats_df = fix_columns(ind_stats_df)

    # Fill in additional rows for missing weeks
    ind_stats_df = fill_season_stats(ind_stats_df)
    ind_stats_df = fix_columns(ind_stats_df)

    # Add in column for injury report status
    ind_stats_df = add_injuries(ind_stats_df, season)

    # Write resulting dataframe to a file
    fname = parsedstats_dir+'{}.csv'.format(season)
    print('Writing',fname)
    ind_stats_df.to_csv(fname)
    
    print("")
