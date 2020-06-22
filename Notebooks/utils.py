import numpy as np
import pandas as pd
import datetime

import requests
import json

fr_grade = {13:'3a',
            21:'4a',
            23:'4b',
            25:'4c',
            29:'5a',
            31:'5b',
            33:'5c',
            36:'6a',
            38:'6a+',
            40:'6b',
            42:'6b+',
            44:'6c',
            46:'6c+',
            49:'7a',
            51:'7a+',
            53:'7b',
            55:'7b+',
            57:'7c',
            59:'7c+',
            62:'8a',
            64:'8a+',
            66:'8b',
            68:'8b+',
            70:'8c',
            72:'8c+'}

yds_grade ={13:'4',
            21:'5',
            23:'6',
            25:'7',
            29:'8',
            31:'9',
            33:'10a',
            36:'10b',
            38:'10c',
            40:'10d',
            42:'11a',
            44:'11b',
            46:'11c',
            49:'11d',
            51:'12a',
            53:'12b',
            55:'12c',
            57:'12d',
            59:'13a',
            62:'13b',
            64:'13c',
            66:'13d',
            68:'14a',
            70:'14b',
            72:'14c',
            74:'14d',
            75:'15a'}


def extract_recent_past(df, date, colname='date', time_range=5, units='days'):
    trange = pd.Timedelta(value=time_range, unit=units)
    return df.loc[(df[colname] < date) & (df[colname] >= date - trange)]

def build_train_array(weather_df, ascent_df, time_range=12, features=['date','prcp','snow','tmax','tmin']):
    if 'date' in features:
        feat_per_entry = len(features)-1
    else:
        feat_per_entry = len(features)
    
    feature_array = np.empty(shape=(len(ascent_df),feat_per_entry*time_range))
    feature_array[:] = np.nan
    ascents = ascent_df.values 
    
    for idx, row in zip(tqdm(ascent_df.index),range(len(ascent_df))):
        recent_past = extract_recent_past(weather_df, \
                                          pd.to_datetime(idx),\
                                          time_range=time_range)
        
        recent_past = recent_past[['prcp','snow','tmax','tmin']]
        rp_vals = recent_past.stack().values
        if rp_vals != []:
            try: feature_array[row,:] = rp_vals
            except: print('Oops on row',row)
        #feature_array[row,:] = recent_past.stack().values
        #print(row,recent_past.stack().values)
        
    return feature_array, ascents

def chop_nans(x,y):
    return x[~np.isnan(x).any(axis=1)], y[~np.isnan(x).any(axis=1)]

def build_sendless_array(weather_df, ascent_df, time_range=12, features=['date','prcp','snow','tmax','tmin']):
    if 'date' in features:
        feat_per_entry = len(features)-1
    else:
        feat_per_entry = len(features)
    
    feature_array = np.empty(shape=(len(ascent_df),feat_per_entry*time_range))
    feature_array[:,:] = np.nan
    ascents = ascent_df.values 
    
    for idx, row in zip(ascent_df.index,range(len(ascent_df))):
        recent_past = extract_recent_past(weather_df, \
                                          pd.to_datetime(idx),\
                                          time_range=time_range)
        
        recent_past = recent_past[['prcp','snow','tmax','tmin']]
        rp_vals = recent_past.stack().values
        if rp_vals != []:
            try: feature_array[row,:] = rp_vals
            except: print('Oops on row',row)
        #feature_array[row,:] = recent_past.stack().values
        #print(row,recent_past.stack().values)
        
    return feature_array, ascents

def gen_new_date(weather_df, weekday_prob):
    # draw a day of the week
    weekday = np.random.choice([0,1,2,3,4,5,6], p = weekday_prob.sort_index(axis=0).values)
    return weather_df[pd.to_datetime(weather_df.date).dt.weekday == weekday].sample(n=1).date

def gen_sendfree_list(weather_df, ascent_df, weekday_prob, num=2800):
    #nosend_dates = np.empty(shape=[len(ascent_df),], dtype='datetime64')
    nosend_dates = pd.DataFrame(data = None,
                                columns = None,
                                dtype = 'object')
    #for idx in tqdm(range(len(ascent_df))):
    for idx in tqdm(range(num)):
        new_date = gen_new_date(weather_df, weekday_prob)
        while pd.to_datetime(new_date.array)[0] in pd.to_datetime(ascent_df.index):
            #print(new_date)
            new_date = gen_new_date(weather_df, weekday_prob)
        #nosend_dates.iloc[idx] = new_date.array.date
        nosend_dates = nosend_dates.append({'date':str(pd.to_datetime(new_date.values[0]).date())},ignore_index=True)
    
    newdf = pd.Series(0, index=pd.Index(nosend_dates['date']))
    
    return newdf

def qry(q, connection = sqlite3.connect("./db1.sqlite")):
    df = pd.read_sql_query(q, connection)
    connection.close
    return df


def get_weather_multiyear(station_id, start_date, end_date, token, limit=1000, units='standard', datasetid='GHCND',**kwargs):
    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)
    if (end_date - start_date).days <= 365:
        weather_dict_list, results_dict = get_weather_between_dates(station_id, start_date, end_date, token, limit=limit, units=units, datasetid=datasetid, **kwargs)
    else:
        chunks = (end_date - start_date).days // 300 + 1 # number of 300 day chunks
        leftover = (end_date - start_date).days % 300 # leftover days after chunks-1 chunks
        
        weather_dict_list = []
        
        if leftover != 0:
            start_dates = [start_date] + [start_date + pd.to_timedelta(i * 300 + 1, unit='d') for i in range(1,chunks)]
            end_dates = [start_date + pd.to_timedelta(j * 300, unit='d') for j in range(1,chunks)] + [end_date]
        else:
            start_dates = [start_date] + [start_date + pd.to_timedelta(i * 300 + 1, unit='d') for i in range(1,chunks-1)]
            end_dates = [start_date + pd.to_timedelta(j * 300, unit='d') for j in range(1,chunks-1)] + [end_date]
        
        for sd, ed in zip(tqdm(start_dates,desc='Date Chunks'), end_dates):
            #print(sd,ed)
            wdl, results_dict = get_weather_between_dates(station_id, sd, ed, token, limit=limit, units=units, datasetid=datasetid, **kwargs)
            #print(len(wdl))
            weather_dict_list = weather_dict_list + wdl
    return weather_dict_list, results_dict

def get_weather_between_dates(station_id, start_date, end_date, token, limit=1000, units='standard', datasetid='GHCND',**kwargs):
    '''Makes an API call to NOAA from station = station_id, between start_date and end_date, with
    token = token, and addition **kwargs (such as datasetid='GHCND', units='standard')
    '''
    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)
    
    if (end_date - start_date).days > 365:
        return print("Error, too long of a gap")
    
    apicall = 'https://www.ncdc.noaa.gov/cdo-web/api/v2/data?stationid='+station_id+\
                '&datasetid='+datasetid+'&startdate='+str(start_date.date())+'&enddate='+str(end_date.date())+\
                '&units='+units+'&limit='+str(limit)
    
    if kwargs.__len__() != 0:
        for key, val in kwargs.items():
            apicall = apicall+'&'+str(key)+'='+str(val)
            
    #print(apicall)
    request = requests.get(apicall,headers={'token':Token})
    
    js = json.loads(request.text)
    
    count = js['metadata']['resultset']['count']
    
    fullresults = js['results']
    
    if count > limit:
        reps = count // limit
        
        if count % limit != 0:
            for iteration in range(reps):
                # print('offset=',iteration*limit)
                request = requests.get(apicall + '&offset=' + str((iteration + 1) * limit + 1),headers={'token':Token})
                js = json.loads(request.text)
                fullresults = fullresults + js['results']
        else:
            for iteration in range(reps-1):
                # print('offset=',iteration*limit)
                request = requests.get(apicall + '&offset=' + str((iteration + 1) * limit + 1),headers={'token':Token})
                js = json.loads(request.text)
                fullresults = fullresults + js['results']
    #else:
    #    fullresults = fullresults + js['results']
    # Check to see if ['metadata']['resultset']['count'] > ['metadata']['resultset']['limit']
    # if it is, then iterate c//l + 1 times, calling and building the df
    
    return fullresults, js['metadata']

def get_stations(token):
    limit=1000
    
    apicall = 'https://www.ncdc.noaa.gov/cdo-web/api/v2/stations?limit='+ str(limit)
    
    request = requests.get(apicall,headers={'token':Token})
    
    js = json.loads(request.text)
    
    count = js['metadata']['resultset']['count']
    
    fullresults = js['results']
    
    if count > limit:
        reps = count // limit
        
        if count % limit != 0:
            for iteration in tqdm(range(reps)):
                request = requests.get(apicall + '&offset=' + str((iteration + 1) * limit + 1),headers={'token':Token})
                js = json.loads(request.text)
                fullresults = fullresults + js['results']
        else:
            for iteration in tqdm(range(reps-1)):
                # print('offset=',iteration*limit)
                request = requests.get(apicall + '&offset=' + str((iteration + 1) * limit + 1),headers={'token':Token})
                js = json.loads(request.text)
                fullresults = fullresults + js['results']
    return fullresults, js['metadata']

