#!/usr/bin/env python3

from flask import Flask, request, jsonify, render_template, url_for
import pickle
import numpy as np
import time
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import GridSearchCV, RandomizedSearchCV, ShuffleSplit, learning_curve, train_test_split, cross_val_score
from sklearn.neighbors import KNeighborsClassifier,KNeighborsRegressor
from sklearn import preprocessing
from sklearn.metrics import r2_score, make_scorer, mean_squared_error, mean_absolute_error
from sklearn.feature_selection import SelectFromModel
import pyfireconnect
from whitenoise import WhiteNoise
import pandas as pd
import random
from sklearn.utils import shuffle
from sklearn.model_selection import ShuffleSplit, learning_curve, train_test_split
from sklearn.neighbors import KNeighborsClassifier
import os
from firebase_admin import credentials, firestore, initialize_app

# cloud database
THIS_FOLDER = os.path.dirname(os.path.abspath(__file__))
my_file = os.path.join(THIS_FOLDER, 'raspberrypi-6b521-firebase-adminsdk-rb94u-fa953a6467.json')
cred= credentials.Certificate('raspberrypi-6b521-firebase-adminsdk-rb94u-fa953a6467.json')
default_app = initialize_app(cred)
db = firestore.client()


# realtime database
config = {
  "apiKey": "AIzaSyAal-QcuayT4d32G-6YJLw8m7Um5b1BPrg",
  "authDomain": "raspberrypi-6b521.firebaseapp.com",
  "databaseURL": "https://raspberrypi-6b521.firebaseio.com",
  "storageBucket": "raspberrypi-6b521.appspot.com"
}
#
firebase = pyfireconnect.initialize(config)
datab = firebase.database()

def LatestReading(id):
    data = datab.child("sensor/"+id).get()
    for data in data.each():
        key = data.key()
        break

    data_split = []
    data_key = datab.child("sensor/"+id+"/"+key).get()
    for data in data_key.each():
        data_split.append(data.val())

    return data_split

# data_split[0] -> acc -> data_split[0][0] , data_split[0][1], data_split[0][2]
# data_split[1] -> asset id
# data_split[2] -> Temp
# data_split[3] -> time

def AssetLists():

    try:
        assets=[]
        docs=db.collection(u'Models').document(u'IPOWERFAN').collection(u'Assets').stream()
        for doc in docs:
            dic= doc.to_dict()
            dic['id']=doc.id
            assets.append(dic)

        return assets
    except google.cloud.exceptions.NotFound:
        return 'error'


updateAssetLists('IPOWERFAN001MPU',True)

app = Flask(__name__)
app.wsgi_app = WhiteNoise(app.wsgi_app)
my_static_folders = (
    'static/assets/js/',
    'static/bower_components/'
)
for static in my_static_folders:
    app.wsgi_app.add_files(static)

data = pd.read_csv("data.csv")
data = data.drop(columns=['||__time'])
data = shuffle(data)
feature_cols = data.drop(['Normality','RUL'], axis = 1).columns
X = data[feature_cols]
y = data.Normality

# split the data into test/train
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.20)
neigh = KNeighborsClassifier(n_neighbors=7)
neigh.fit(X_train, y_train)

# RUL 
y2 = data.RUL
# split the data into test/train
X_train1, X_test1, y_train1, y_test1 = train_test_split(X, y2, test_size=0.20)
neigh2 = KNeighborsRegressor(n_neighbors=7)
neigh2.fit(X_train1, y_train1)


def model(id):
    data_split = LatestReading(id)
    pred = neigh.predict([[data_split[0][0],data_split[0][1], data_split[0][2], data_split[2]]])
    prob = neigh.predict_proba([[data_split[0][0],data_split[0][1], data_split[0][2], data_split[2]]])
    string = str(prob).strip('[]').split()
    return pred, string

def RUL(id):
    data_split = LatestReading(id)
    pred2 = neigh2.predict([[data_split[0][0],data_split[0][1], data_split[0][2], data_split[2]]])
    return pred2


@app.route('/', methods=['GET', 'POST'])
def home():
    return render_template('index.html')

# ROUTE
@app.route('/myProfile.html')
def profile():
    return render_template('myProfile.html')

@app.route('/helpcenter.html')
def helpcenter():
    return render_template('helpcenter.html')

@app.route('/MyTasks.html')
def mytasks():
    return render_template('MyTasks.html')

@app.route('/registerasset.html')
def registerasset():
    return render_template('registerasset.html')

@app.route('/timeline.html')
def timeline():
    return render_template('timeline.html',data=AssetLists())

@app.route('/assets/<assetID>/<sensorID>')
def asset(assetID, sensorID):
    rul = RUL(sensorID)
    n, n_prob = model(sensorID)
    return render_template('asset.html', prob=float(n_prob[1])*100, rul=np.round(rul[0]), normality=n, assetID=assetID, sensorID=sensorID)

@app.route('/<assetID>/issues')
def issues(assetID):
    return render_template('asset-issues.html', assetID = assetID)

@app.route('/assets.html')
def assets():
    return render_template('assets.html')

@app.route('/login.html')
def login():
    return render_template('login.html')


if __name__ == "__main__":
    app.run(port=8060, debug=True)
