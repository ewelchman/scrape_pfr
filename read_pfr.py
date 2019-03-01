import pandas as pd
import numpy as np
from selenium import webdriver
from lxml import etree
import time
import json
import os


# Make a dictionary to store what three-letter code each 
# team used in a given season
three_letter_code = {}
# Most teams don't change, but some do
tms = [
    'atl','nor','car','tam','nyg','dal','phi','was',
    'min','gnb','det','chi','sea','sfo','crd','ram',
    'pit','cle','cin','rav','buf','nyj','mia','nwe',
    'jax','htx','oti','clt','den','kan','rai','sdg',
    'lac'
]
tlcs = {k:[k] for k in tms}
tlcs['crd'].append('ari')
tlcs['ram'].append('lar')
tlcs['ram'].append('stl')
tlcs['rav'].append('bal')
tlcs['oti'].append('ten')
tlcs['clt'].append('ind')
tlcs['htx'].append('hou')
tlcs['rai'].append('oak')
tlcs['sdg'].append('lac')
tlcs['lac'].append('sdg')
for tm in tms:
    for yr in range(2000,2019):
        k = '{}{}'.format(tm,yr)
        three_letter_code[k] = tm
# Arizona Cardinals
for yr in range(2000,2019):
    k = 'crd{}'.format(yr)
    three_letter_code[k] = 'ari'
# St Louis Rams
    # 2016-17 - lar
    # 2000-15 - stl
three_letter_code['ram2017'] = 'lar'
three_letter_code['ram2016'] = 'lar'
for yr in range(2000,2016):
    k = 'ram{}'.format(yr)
    three_letter_code[k] = 'stl'
# Baltimore Ravens
for yr in range(2000,2019):
    k = 'rav{}'.format(yr)
    three_letter_code[k] = 'bal'
# Oilers/Titans
for yr in range(2000,2019):
    k = 'oti{}'.format(yr)
    three_letter_code[k] = 'ten'
# Indianapolis Colts
for yr in range(2000,2019):
    k = 'clt{}'.format(yr)
    three_letter_code[k] = 'ind'
# Texans
for yr in range(2000,2019):
    k = 'htx{}'.format(yr)
    three_letter_code[k] = 'hou'
# Raiders
for yr in range(2000,2019):
    k = 'rai{}'.format(yr)
    three_letter_code[k] = 'oak'
# Chargers
three_letter_code['sdg2017'] = 'lac'
for yr in range(2000,2018):
    k = 'sdg{}'.format(yr)
    three_letter_code[k] = 'sdg'


def read_table( html_tree, 
                tablename ):
    
    # Make list to house dictionaries for each row
    rows = []
    tablepath = '//table[@id="{0}"]/tbody/tr'.format(tablename)
    
    # Split table into rows
    for row in html_tree.xpath(tablepath):
        
        # Make a dictionary to store each cell in the row
        rd = {}
        rowclass = row.xpath('./@class')
        try:
            rd["rowclass"] = rowclass[0]
        except:
            pass
        try:
            cells = [e for e in row.xpath('./td|./th')]
            for i, cell in enumerate(cells):
                
                # Depending on cell contents, add cell to row dict
                try:
                    txt = cell.xpath('./text()')
                    a_text = [x.text for x in cell.findall(".//a[@href]")]
                    a_href = [x.get("href") for x in cell.findall(".//a[@href]")]
                    stat = cell.xpath('./@data-stat')
                    tip = cell.xpath('./@data-tip')
                
                    # Logic map for cell contents
                    if (len(tip) >= 1):
                        # Have a data-tip. This may be an injury report page
                        rd[stat[0]] = tip
                    elif (len(txt) >= 1) and (len(a_text) >= 1):
                        # Have both links and standard text. Save both
                        rd[stat[0]+"_text"] = "brk, ".join(txt)
                        rd[stat[0]+"_a"] = ", ".join(a_text)
                        rd[stat[0]+"_href"] = ", ".join(a_href)
                    elif len(a_text) >= 1:
                        # Have just text from a link
                        rd[stat[0]+"_a"] = a_text[0]
                        rd[stat[0]+"_href"] = a_href[0]
                    else:
                        try:
                            # Maybe we just have text
                            rd[stat[0]] = txt[0]
                        except:
                            # If all fails, then we probably have no text
                            rd[stat[0]] = ""
                                        
                except:
                    print("Couldn't parse a cell")
                    print(etree.tostring(cell, pretty_print=True))
            
            
            # Add row dictionary to list of rows
            rows.append(rd)

        except:
            pass
        
    return rows


# One function to take an element tree and parse all of the tables on it
def get_tables(url):
    
    options = webdriver.ChromeOptions()
    options.add_argument('headless')

    driver = webdriver.Chrome(chrome_options=options)
    try:
        driver.get(url)
        page_html = driver.page_source
        tree = etree.HTML(page_html)
        tablenames = tree.xpath('//table/@id')
        
    except:
        print("webdriver failed to get url",url)
        tablenames = [""]
    driver.quit()
    
    tables = {}
    for tab in tablenames:
        try:
            tables[tab] = read_table(tree, tab)
        except:
            print("Failed to read table",tab)
            tables[tab] = ""
            
    return tables


def read_season_sched( season ):
    url = "https://pro-football-reference.com/years/"+str(season)+"/games.htm"
    print("Reading",url)
    season_dict = {"":""}
    tries = 1
    while (tries < 5) and ( season_dict == {"":""} ):
        season_dict = get_tables(url)
        tries += 1
        time.sleep(0.1) 
    return season_dict


def read_game_page( gid ):
    url = "http://pro-football-reference.com"+str(gid)
    print("Trying to read",url)
    game_dict = {"":""}
    tries = 1
    while (tries < 5) and ( game_dict == {"":""} ):
        game_dict = get_tables(url)
        tries += 1
        time.sleep(0.1)
    return game_dict


def read_inj_page( team, season ):
    url = 'https://www.pro-football-reference.com/teams/{}/{}_injuries.htm'.format(team,season)
    print("Trying to read",url)
    page_dict = {"":""}
    tries = 1
    while (tries < 5) and (page_dict == {"":""}):
        page_dict = get_tables(url)
        tries += 1
        time.sleep(0.1)
    return page_dict
