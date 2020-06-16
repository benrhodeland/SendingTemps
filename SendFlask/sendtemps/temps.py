from sendtemps import app
from flask import render_template, request
import wtforms
from wtforms.fields.html5 import DateField
import datetime
import random
import math

import sqlalchemy as sa
import pandas as pd

import markdown
import io
from pathlib import Path

from flask import make_response, url_for, Markup
import json

#from .MVP_model import ModelIt
from sqlalchemy import create_engine
from sqlalchemy_utils import database_exists, create_database

from .model import model_now

import psycopg2
import pickle
import numpy as np
#import xgboost as xgb

# Python code to connect to Postgres
# You may need to modify this based on your OS, 
# as detailed in the postgres dev setup materials.

#user = 'djjohnson' #add your Postgres username here      
#host = 'localhost'
#dbname = 'birth_db'
#db = create_engine('postgres://%s%s/%s'%(user,host,dbname))
con = None
#con = psycopg2.connect(database = dbname, user = user)

def nearest_crags(lat, lon, limit=3):
    ascents = pickle.load(open('./data/ascent_west_latlon_stations.pkl',mode='rb'))
    crags = ascents[['station_id','latitude','longitude','crag']].drop_duplicates()
    crags['distance'] = 6367*2*np.arcsin(np.sqrt(np.sin((np.radians(\
                    crags['latitude'].astype(float))\
                    - math.radians(lat))/2)**2 + math.cos(math.radians(lat))\
                    * np.cos(np.radians(crags['latitude'].astype(float))) \
                    * np.sin((np.radians(crags['longitude'].astype(float)) \
                    - math.radians(lon))/2)**2))
    minn = crags['distance'].argsort()
    closest = crags.iloc[minn[:limit]]
    return closest

class TheForm(wtforms.Form):
    date = DateField('Date', format='%Y-%m-%d',
            default=datetime.date.today)
    lat = wtforms.FloatField('Lat', id='lat')
    lng = wtforms.FloatField('Lng', id='lng')

@app.route('/')
@app.route('/result',methods=['GET', 'POST'])
def index():
    form = TheForm(request.form)
    ascents = pickle.load(open('./data/ascent_west_latlon_stations.pkl',mode='rb'))
    crags = ascents[['station_id','latitude','longitude','crag']].drop_duplicates()
    if request.method == 'POST' and form.validate():
        now = form.date.data
        params = dict (
                date=now,
                lat=form.lat.data,
                lon=form.lng.data,
                )
        nearby_crags = nearest_crags(params['lat'],params['lon'])
        sendy = []
        probs = []
        for row in nearby_crags.itertuples():
            suggestion, prob = model_now(row.station_id, params['date'],row.latitude,row.longitude)
            sendy.append(suggestion)
            probs.append(prob)
        nearby_crags['suggestion'] = sendy
        nearby_crags['probability'] = probs
        
        return render_template("toclimb.html",
                               params = params,
                               title = "Estimate for {date}".format(date=now),
                               crags = list(nearby_crags.itertuples())
                              )

    
    
    return render_template("input.html",
      form=form,
      crags=list(crags.itertuples())
                           
      )

# @app.route('/result',methods=['GET', 'POST'])
# def toclimb():
#     xg = pickle.load(open('./data/xgmodel_MVP.pkl',mode='rb'))
#     data = pickle.load(open('./data/fullxy_5day.pkl',mode='rb'))
#     x = data[0]
#     y = data[1] > 0
#     y = y.astype('int')
    
#     now=form.date.data
    
#     sample = np.random.choice(np.arange(0,len(x)));
#     probs = xg.predict_proba(np.array([x[sample,:]]))
    
#     pred_class = np.argmax(probs)
#     prob = (np.max(probs) * 100.0)
#     actual = y[sample]
#     #---
#     start_date = datetime.date(1998, 1, 1)
#     end_date = datetime.date(2018, 2, 1)

#     time_between_dates = end_date - start_date
#     days_between_dates = time_between_dates.days
#     number_of_days = random.randrange(days_between_dates)
#     this_date = start_date + datetime.timedelta(days=number_of_days)

#     return render_template("toclimb.html",
#                            sample=sample,
#                            pred_class=pred_class,
#                            prob=prob,
#                            this_date=this_date,
#                            now=now,
#                            form=form,
#                            actual=actual)

# @app.route('/')
# @app.route('/index')
# def index():
#     form = TheForm(request.form)
#     return render_template("input.html",
#       form=form
#       )

# @app.route('/result',methods=['GET', 'POST'])
# def toclimb():
#     xg = pickle.load(open('./data/xgmodel_MVP.pkl',mode='rb'))
#     data = pickle.load(open('./data/fullxy_5day.pkl',mode='rb'))
#     x = data[0]
#     y = data[1] > 0
#     y = y.astype('int')
    
#     now=form.date.data
    
#     sample = np.random.choice(np.arange(0,len(x)));
#     probs = xg.predict_proba(np.array([x[sample,:]]))
    
#     pred_class = np.argmax(probs)
#     prob = (np.max(probs) * 100.0)
#     actual = y[sample]
#     #---
#     start_date = datetime.date(1998, 1, 1)
#     end_date = datetime.date(2018, 2, 1)

#     time_between_dates = end_date - start_date
#     days_between_dates = time_between_dates.days
#     number_of_days = random.randrange(days_between_dates)
#     this_date = start_date + datetime.timedelta(days=number_of_days)

#     return render_template("toclimb.html",
#                            sample=sample,
#                            pred_class=pred_class,
#                            prob=prob,
#                            this_date=this_date,
#                            now=now,
#                            form=form,
#                            actual=actual)

@app.route('/about')
def about():
    thispath = Path(__file__)
    readme_path = thispath.parent.parent.joinpath("README.md")
    with io.open(str(readme_path), 'r') as fl:
        content = Markup(markdown.markdown(fl.read()))
    return render_template("blank.html", title='About SendingTemps', content=content)
















@app.route('/db')
def birth_page():
   sql_query = """                                                                       
               SELECT * FROM birth_data_table WHERE delivery_method='Cesarean';          
               """
   query_results = pd.read_sql_query(sql_query,con)
   births = ""
   for i in range(0,10):
       births += query_results.iloc[i]['birth_month']
       births += "<br>"
   return births

@app.route('/db_fancy')
def cesareans_page_fancy():
   sql_query = """
              SELECT index, attendant, birth_month FROM birth_data_table WHERE delivery_method='Cesarean';
               """
   query_results=pd.read_sql_query(sql_query,con)
   births = []
   for i in range(0,query_results.shape[0]):
       births.append(dict(index=query_results.iloc[i]['index'], attendant=query_results.iloc[i]['attendant'], birth_month=query_results.iloc[i]['birth_month']))
   return render_template('cesareans.html',births=births)

@app.route('/input')
def cesareans_input():
   return render_template("input.html")

@app.route('/output')
def cesareans_output():
   #pull 'birth_month' from input field and store it
   patient = request.args.get('birth_month')
   #just select the Cesareans  from the birth dtabase for the month that the user inputs
   query = "SELECT index, attendant, birth_month FROM birth_data_table WHERE delivery_method='Cesarean' AND birth_month='%s'" % patient
   print(query)
   query_results=pd.read_sql_query(query,con)
   print(query_results)
   births = []
   for i in range(0,query_results.shape[0]):
      births.append(dict(index=query_results.iloc[i]['index'], attendant=query_results.iloc[i]['attendant'], birth_month=query_results.iloc[i]['birth_month']))
   the_result = ModelIt(patient,births)
   return render_template("output.html", births = births, the_result = the_result)

@app.route('/inputTest')
def addition_input():
   return render_template("inputTest.html")

@app.route('/outputTest')
def addition_output():
   num_one = float(request.args.get('first_number'))
   num_two = float(request.args.get('second_number'))
   sumofnums = num_one + num_two
   print(sumofnums)
   return render_template("outputTest.html", sumofnums = sumofnums)



