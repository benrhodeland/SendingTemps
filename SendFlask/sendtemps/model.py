import pandas as pd
import io
import requests
import datetime
import os
import pickle
import numpy as np
import glob
import time
from sendtemps import app
import json

#from .usda_hourly import get_usda_hourly
#from .engineered import make_engineered_features

#from sklearn.externals import joblib

#from pandas.core.groupby import DataError

this_dir, this_filename = os.path.split(__file__)
DATA_PATH = os.path.join(this_dir, "data")

def model_now(station_id, date,lat,lon):
    # load corresponding station model
    idpart = station_id.replace('GHCND:','')
    filename = glob.glob('./data/xgmodel_5day_1.2neg-pos*'+idpart+'.pkl')
    
    try:
        xg = pickle.load(open(filename[0],mode='rb'))
    except Exception as e:
        print('File ',filename,'does not exist :(')
        return 'Unavailable', 0
    
    # Get features of this model
    feature_dict = pickle.load(open('./data/station_features.pkl',mode='rb'))
    model_feats = feature_dict[station_id]
    
    # 
    
    # pull weather data for date from openweather
    features = []
    for iterdays in range(5,0,-1):
        query_date = date - pd.Timedelta(str(iterdays)+' days')
        print(query_date)
        build_call = 'https://api.openweathermap.org/data/2.5/onecall/timemachine?'\
        + 'lat=' + str(lat) \
        + '&lon=' + str(lon) \
        + '&dt=' + str(int(time.mktime(query_date.timetuple()))) \
        + '&units=imperial' \
        + '&appid=' + app.config['OPENTOKEN']
        r = requests.get(build_call)
        d = json.loads(r.text)
        df = pd.json_normalize(d['hourly'])
        mintemp = df['temp'].min(axis=0)
        maxtemp = df['temp'].max(axis=0)
        try:
            precip = df['rain.1h'].sum()
        except:
            precip = 0
        snow = 0.
        for feat in model_feats:
            if feat == 'tmin':
                features.append(mintemp)
            if feat == 'prcp':
                features.append(precip)
            if feat == 'tmax':
                features.append(maxtemp)
            if feat == 'snow':
                features.append(snow)
    
    # feed weather features into station model
    
    probs = xg.predict_proba(np.array([features]))
    pred_class = np.argmax(probs)
    prob = (np.max(probs) * 100.0)
    
    if pred_class == 0:
        suggestion = 'Not looking so good'
    else:
        suggestion = 'Climb on!'
    
    return suggestion, prob