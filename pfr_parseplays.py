import read_pfr as rp
import pandas as pd
import json
import os


#boxscore_path = '/home/welced12/googledrive/nfl_data/devl/pfr_boxscores'
boxscore_path = '/home/welced12/git/football_analytics/pfr_pages/boxscores'
#gamelistpath = '/home/welced12/googledrive/nfl_data/devl/pfr_gamedata.json'
gamelistpath = '/home/welced12/git/football_analytics/pfr_pages/pfr_gamedata.json'
pbp_filename = '/home/welced12/googledrive/nfl_data/devl/pfr_parsedplays.csv'
#pbp_filename = '/tmp/test_pfr_parsedplays.csv'

debug_game = ''

def get_secs_rem(df):
    # Get column for seconds remaining
    qtr = df['quarter'].values
    time_rem = df['qtr_time_remain_a'].values
    secs_rem= []
    
    for q, tr in zip(qtr, time_rem):
        try:
            [mins, secs] = tr.split(":")
            sr = 900*(4-int(q)) + 60*int(mins) + int(secs)
            secs_rem.append(sr)
        except:
            if 3600 in secs_rem:
                secs_rem.append(secs_rem[-1])
            else:
                secs_rem.append(3600)
                
    return secs_rem


def parse_possession( game_page ):
    df = pd.DataFrame(game_page['pbp'])
    # Get a list of which players are on which team.
    # This will be useful for determining possession later
    off_df = pd.DataFrame(game_page['player_offense'])
    def_df = pd.DataFrame(game_page['player_defense'])
    kick_df = pd.DataFrame(game_page['kicking'])
    cs = ['team','player_href']
    plyrs_df = pd.concat([ off_df[cs], def_df[cs], kick_df[cs] ])
    
    # Get home/away teams. Away team listed first for individual stats.
    home = off_df.team.values[-1]
    away = off_df.team.values[1]

    home_bool = [True if str(x)==home else False for x in plyrs_df.team]
    away_bool = [True if str(x)==away else False for x in plyrs_df.team]
    home_plyrs = plyrs_df[home_bool].player_href.values
    away_plyrs = plyrs_df[away_bool].player_href.values
    # If we have snap counts tables, those are even better
    if 'home_snap_counts' in game_page.keys():
        home_plyrs = pd.DataFrame(game_page['home_snap_counts']).player_href.values
        away_plyrs = pd.DataFrame(game_page['vis_snap_counts']).player_href.values
    
    # Make sure player names are lowercase
    home_plyrs = [str(x).lower() for x in home_plyrs]
    away_plyrs = [str(x).lower() for x in away_plyrs]
    
    # Go through play-by-play and track possession changes
    poss = []
    for i, (rc, plyrs, det) in enumerate(zip(df['rowclass'].values,
                                             df['detail_href'].values,
                                             df['detail_text'].values)):
        det = str(det).lower()
        # If rowclass is divider or score (or previous row is oncell),
        # ball is probably controlled by team of first player mentioned
        if poss == []:  # First entry in play-by-play
            poss.append(home)
        elif str(plyrs) == 'nan':
            # Continue possession from previous play
            poss.append(poss[-1])
        else:
            # First player mentioned probably started with possession
            prev_rc = df.rowclass.values[i-1]
            plyr1 = plyrs.split(", ")[0].lower()
            
            # If "No Play" and defensive pre-snap penalty in detail, 
            # continue possession from previous play
            if ("no play" in det) & ('offside' in det):
                poss.append(poss[-1])
                
            elif plyr1 in home_plyrs:
                poss.append(home)
            elif plyr1 in away_plyrs:
                poss.append(away)
            else:
                #print("Couldn't match player",plyr1,"to a team")
                poss.append(poss[-1])
    
    return poss


def get_defense( pbp_df ):
    home = pbp_df.home.values[1]
    away = pbp_df.away.values[1]
    poss = pbp_df.poss.values

    defense = [home if off==away else away for off in poss]
    return defense


def get_poss_changes( pbp_df ):
    poss = pbp_df.poss.values
    pc = []
    for i, play in enumerate(poss[:-1]):
        if play == poss[i+1]:
            pc.append(False)
        else:
            pc.append(True)
    pc.append(False)
    return pc


def get_turnovers( pbp_df ):
    tos = [False for l in pbp_df.index]
    poss_changes = pbp_df.poss_change.values
    kickoffs = pbp_df.is_kickoff.values
    fgs = pbp_df.is_fieldgoal.values
    punts = pbp_df.is_punt.values
    for i, (pc, kick, punt, fg) in enumerate(zip(poss_changes, kickoffs, punts, fgs)):
        if ( pc and not (kick | punt | fg) ):
            tos[i] = True
    return tos


def get_fieldposition( pbp_df ):
    # Fieldposition from the offense's perspective
    off_fp = []
    for off, defense, loc in zip(pbp_df.poss.values, pbp_df['def'].values, pbp_df.location.values):
        if '50' in str(loc):
            off_fp.append(0)
        elif (
            (str(loc) in ['','nan']) or
            ("Location" in str(loc) )
        ):
            off_fp.append(0)
        elif len(loc) >= 4:
            side = loc.split()[0].lower()
#            tmside = rp.three_letter_code[side.lower()+str(pbp_df.season.values[0])]
            ydline = int(loc.split()[1])
            if off.lower() in rp.tlcs[side]:
                # Offense is on own side of field. fieldpos is negative
                off_fp.append( -1*(50-ydline) )
            elif defense.lower() in rp.tlcs[side]:
                #print(defense.lower(),rp.tlcs[side])
                off_fp.append( 50-ydline )
            else:
                # Offense is in opponent's territory
                off_fp.append( 50-ydline )
        else:
            print("not sure how to parse fieldpos",loc)
            off_fp.append(0)
            
    return off_fp


def found_pass(detail):
    d = detail.lower()
    pass_terms = ["pass", "sacked", "scramble",
                  "interception", "intercepted"]
    for term in pass_terms:
        if term in d:
            return True
    return False

def found_scramble(detail):
    d = detail.lower()
    if "scramble" in d:
        return True
    return False
    
def found_run(detail):
    d = detail.lower()
    run_terms = [
        "run ", "rush", "left tackle ","right tackle ",
        "up the middle ","middle for", "left end ", "right end ",
        "left guard ", "right guard ", "kneel"
    ]
    if not "scramble" in d:
        for term in run_terms:
            if term in d:
                return True
    return False

        
def found_punt(detail):
    d = detail.lower()
    if " punts " in d:
        return True
    elif " punt return" in d:
        return True
    return False
    
def found_fieldgoal(detail):
    d = detail.lower()
    if " field goal" in d:
        return True
    return False

def found_penalty(detail):
	d = detail.lower()
	if "penalty" in d:
		return True
	return False

def found_kickoff(detail):
    d = detail.lower()
    kickoff_terms = ["kicks off", 'kickoff', 'onside kicks']
    for kt in kickoff_terms:
        if kt in d:
            return True
    return False

def yds_run( detail ):
    words = detail.lower().split()
    # look for yardage in format "for X yards"
    for j, w in enumerate(words):
        if w == "for" and len(words) > j+2:
            if words[j+2].rstrip(".,") in ("yd","yds","yrd","yrds","yard","yards"):
                return int(words[j+1])
            # or "for no gain"
            elif "no" in words[j+1] and "gain" in words[j+2]:
                return 0
        
        # or "X yard run/rush"
        elif w in ("yd","yds","yrd","yrds","yard","yards") and len(words) >= j+2:
            if words[j+1].rstrip(".,") in ("run","rush"):
                return int(words[j-1])
        
    return "x"
    
def yds_passed( detail ):
    words = detail.lower().split()
    # look for yardage in format "for X yards"
    for j, w in enumerate(words):
        if w == "for" and len(words) > j+2:
            if words[j+2].rstrip(".,") in ("yd","yds","yrd","yrds","yard","yards"):
                return int(words[j+1])
            # or "for no gain"
            elif "no" in words[j+1] and "gain" in words[j+2]:
                return 0
            
        # or "X yard pass"
        elif w in ("yd","yds","yrd","yrds","yard","yards") and len(words) >= j+2:
            if words[j+1].rstrip(".,") in ("pass"):
                return int(words[j-1])

    # Or maybe pass went incomplete
    if "incomplete" in detail.lower():
        return 0
    
    # Or maybe pass was intercepted. In this case, just say yds_gained is zero
    elif ("intercepted" in detail.lower()) or ("interception" in detail.lower()):
        return 0
    
    return "x"


def parse_details(df):
    # Make a bunch of lists to be populated with details in-loop    
    df_len = len(df.down.values)
    is_parseable = [False for i in range(df_len)]
    is_run = [False for i in range(df_len)]
    is_scramble = [False for i in range(df_len)]
    is_pass = [False for i in range(df_len)]
    is_punt = [False for i in range(df_len)]
    is_fieldgoal = [False for i in range(df_len)]
    is_kickoff = [False for i in range(df_len)]
    is_penalty = [False for i in range(df_len)]
    yds_gained = ['x' for i in range(df_len)]
    
    # Loop through details, use logic tree to classify plays
    for i, (down, 
            detail_text, 
            detail_plyrs) in enumerate(zip(df.down.values,
                                           df.detail_text.values,
                                           df.detail_href.values)):
        detail_text = str(detail_text).lower()
        
        # Look for plays in downs 1-4
        if (str(down) != 'nan') and (str(down) != ''):
            
#            print("parsing",detail_text)
            # Try and classify the play and parse yards gained
            if found_scramble(detail_text):
                is_scramble[i] = True
                yds_gained[i] = yds_run(detail_text)
                
            if found_run(detail_text):
                is_run[i] = True
                yds_gained[i] = yds_run(detail_text)
                
            if found_pass(detail_text):
                is_pass[i] = True
                yds_gained[i] = yds_passed(detail_text)
                
            elif found_punt(detail_text):
                is_punt[i] = True
                
            elif found_fieldgoal(detail_text):
                is_fieldgoal[i] = True

            # Catch stuff that wasn't caught elsewhere
            elif yds_run(detail_text) != 'x':
                try:
                    yds_gained[i] = yds_run(detail_text)
                    is_run[i] = True
                except:
                    pass

        # Also check for kickoffs and penalties
        elif found_kickoff(detail_text):
            is_kickoff[i] = True
    
        if found_penalty(detail_text):
            is_penalty[i] = True
    
    for i, yds in enumerate(yds_gained):
        if (is_run[i] or is_pass[i] or is_scramble[i]) and (yds != 'x'):
            is_parseable[i] = True
        elif is_punt[i]:
            is_parseable[i] = True
        elif is_fieldgoal[i]:
            is_parseable[i] = True
            
    # Now write columns to the end of the DataFrame
    df['is_parseable'] = is_parseable
    df['is_run'] = is_run
    df['is_pass'] = is_pass
    df['is_scramble'] = is_scramble
    df['is_punt'] = is_punt
    df['is_fieldgoal'] = is_fieldgoal
    df['is_penalty'] = is_penalty
    df['is_kickoff'] = is_kickoff
    df['yds_gained'] = yds_gained
                            
    return df


def clean_yds_to_go( df ):
    y2g = []
    to_go = df['yds_to_go'].values
    ydline = df['off_fieldpos'].values
    for tg, yd in zip(to_go, ydline):
        if "goal" in str(tg).lower():
            y2g.append( 50 - int(yd) )
        else:
            y2g.append(tg)
            
    return y2g


def read_success( df ):
    frac = { 1:0.45, 2:0.65, 3:1.0, 4:1.0 }
    success = []
    tup = zip(
        df.is_parseable, df.down.values, 
        df.dist.values, df.yds_gained.values
    )
    for parseable, down, dist, gain in tup:
        if str(parseable) == 'True':
            # Play is 'success' if team gains
            # more yards than a particular fraction of the distance to 1st down
            try:
                if int(gain) >= frac[int(down)]*int(dist):
                    success.append(1)
                else:
                    success.append(0)
            except:
                success.append(0)
        else:
            success.append('nan')
            
    return success


def get_home_score_before( df ):
    scores = df.pbp_score_hm.shift(-1).values
    scores[0] = 0
    return scores

def get_away_score_before( df ):
    scores = df.pbp_score_aw.shift(-1).values
    scores[0] = 0
    return scores


def get_off_lead( df ):
    hm = df.home.values[0]
    aw = df.away.values[0]
    off_lead = [
        0 if (score_hm in [hm,''])
        else int(score_hm) - int(score_aw) if hm == off
        else int(score_aw) - int(score_hm) if aw == off
        else 0 for (off, score_hm, score_aw) in zip(
            df.poss.values, df.score_b4_hm.fillna(0).values, df.score_b4_aw.fillna(0).values
        )
    ]
    return off_lead
 

# Parse play-by-play for one pfr page with tables in json format\
def parse_pfr_pbp( game_page ):
    
    #print(game_page.keys())
    
    # Get raw play-by-play
    pbp_df = pd.DataFrame(game_page['pbp'])

    # Get home/away teams. Away team listed first for individual stats.
    home = pd.DataFrame(game_page['player_offense']).team.values[-1]
    away = pd.DataFrame(game_page['player_offense']).team.values[1]
    pbp_df['home'] = home
    pbp_df['away'] = away

    if game_page['gid']==debug_game:
        print("Home:",home,"- Away:",away)
    # Determine team on offense/defense
    pbp_df['poss'] = parse_possession( game_page )
    pbp_df['def'] = get_defense(pbp_df)
    if game_page['gid']==debug_game:
        print("Got defense")
    # Parse fieldposition from offense's perspective
    pbp_df['off_fieldpos'] = get_fieldposition(pbp_df)
    if game_page['gid']==debug_game:
        print("Got fieldposition")
    pbp_df['dist'] = pbp_df['yds_to_go'].values
    pbp_df['yds_to_go'] = clean_yds_to_go(pbp_df)
    # Parse seconds remaining
    pbp_df['secs_rem'] = get_secs_rem(pbp_df)
    # Sort out score before and after the play
    pbp_df['score_b4_hm'] = get_home_score_before(pbp_df)
    pbp_df['score_b4_aw'] = get_away_score_before(pbp_df)
    pbp_df.rename(
        {'pbp_score_hm':'score_after_hm', 'pbp_score_aw':'score_after_aw'},
        axis='columns', inplace=True
    )
    pbp_df['offense_lead'] = get_off_lead(pbp_df)
    # Parse details
    pbp_df = parse_details(pbp_df)
    # Track possession changes and turnovers
    pbp_df['poss_change'] = get_poss_changes(pbp_df)
    pbp_df['is_turnover'] = get_turnovers(pbp_df)
    # Determine 'success' of plays
    pbp_df['success'] = read_success(pbp_df)
    
    return pbp_df

# Read & parse pbp from individual game json files
gamepages = [
    f for f in os.listdir(boxscore_path) 
    if os.path.isfile(os.path.join(boxscore_path, f))
]

# Load information about these games
season_dfs = []
with open(gamelistpath, 'r') as f:
    gamehist_dict = json.load(f)
for ssn in gamehist_dict.keys():
    season_df = pd.DataFrame(gamehist_dict[ssn]['games'])
    season_df['season'] = ssn
    season_dfs.append(season_df)
gamehist_df = pd.concat(season_dfs)
#print(gamehist_df.info())

game_dfs = []
#for i, gamefile in enumerate(g for g in gamepages[:] if g.split('.')[0]==debug_game):
for i, gamefile in enumerate(gamepages[:]):
    with open(os.path.join(boxscore_path,gamefile), 'r') as f:
        g_dict = json.load(f)

    try:
#        print(game_df.info())
        # Add info about season, week, unique ids for game and play
        gid = gamefile.split('.')[0]
        g_dict['gid'] = gid
        bool_list = [True if (gid in str(link)) else False
                     for link in gamehist_df.boxscore_word_href.values]
        game_row = pd.DataFrame(gamehist_df[bool_list])

        # Parse json object for play-by-play
        game_df = parse_pfr_pbp(g_dict)
        
        game_df['gid'] = gid
        game_df['pid'] = [gid+str(idx) for idx in game_df.index]
        game_df['season'] = game_row['season'].values[0]
        game_df['week']  = game_row['week_num'].values[0]

        game_dfs.append(game_df)
        
        if i%100 == 0:
            print("Finished parsing",i,"games")
    except Exception as e:
        print("Failed to parse",gamefile)
        print(e)
        pass


# Concatenate all play-by-play frames from individual games
all_pbp_df = pd.concat(game_dfs)
cool_cols = ['season','week','gid','home','away','detail_a','detail_text',
             'poss','off_fieldpos','down','dist','yds_to_go','yds_gained',
             'is_parseable','success']
print(all_pbp_df.info())
print(all_pbp_df[cool_cols].sample(10))

print("Saving parsed plays to",pbp_filename)
all_pbp_df.to_csv(pbp_filename)
