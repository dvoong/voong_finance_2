import os
import datetime
import simplejson as json
import flask
import psycopg2
import numpy as np
import pandas as pd
import dev
import models
import logging
from functools import wraps
from flask import Flask, render_template, g, request, redirect, url_for, session, jsonify
from flask_oauthlib.client import OAuth

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

app = Flask(__name__)

app.config['GOOGLE_ID'] = "413758236293-n6fje92c58kt43gq1fviektuid1q0svl.apps.googleusercontent.com"
app.config['GOOGLE_SECRET'] = "RHMdMjhYFgzQ3xtpqYouim39"
app.secret_key = b'\x91)|EYN\xfeV\x021\xc80\x9ca\xde\x8bOS\xe5\x1cP\x05\x00\x01'

oauth = OAuth(app)
google = oauth.remote_app(
    'google',
    consumer_key=app.config.get('GOOGLE_ID'),
    consumer_secret=app.config.get('GOOGLE_SECRET'),
    request_token_params={
        'scope': 'email'
    },
    base_url='https://www.googleapis.com/oauth2/v1/',
    request_token_url=None,
    access_token_method='POST',
    access_token_url='https://accounts.google.com/o/oauth2/token',
    authorize_url='https://accounts.google.com/o/oauth2/auth',
)
    
connection = psycopg2.connect(
    user=os.environ['VOONG_FINANCE_DB_USER'], #'voong_finance',
    password=os.environ['VOONG_FINANCE_DB_PASSWORD'], #testdb
    host=os.environ['VOONG_FINANCE_DB_HOST'], #localhost
    database=os.environ['VOONG_FINANCE_DB_NAME'], #voong_finance_db
    port=os.environ['VOONG_FINANCE_DB_PORT'] # '5432'
)

cursor = connection.cursor()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'google_token' in session:
            me = google.get('userinfo')
            if 'verified_email' in me.data and me.data['verified_email'] == True:
                return f(*args, **kwargs)
        session['next'] = request.url
        return redirect(url_for('login'))
    return decorated_function

@app.route('/')
@login_required
def index():
    today = datetime.date.today()
    return render_template('home.html', today=today)


@app.route('/login')
def login(next='/'):
    return google.authorize(callback=url_for('authorized', _external=True))


@app.route('/logout')
def logout():
    session.pop('google_token', None)
    return 'Logged Out'


@app.route('/login/authorized')
def authorized(next='/'):
    resp = google.authorized_response()
    if resp is None:
        return 'Access denied: reason=%s error=%s' % (
            request.args['error_reason'],
            request.args['error_description']
        )
    session['google_token'] = (resp['access_token'], '')
    return redirect(session['next'])


@google.tokengetter
def get_google_oauth_token():
    return session.get('google_token')

@app.route('/get-balance')
@login_required
def get_balance():
    logging.debug('/get-balance')
    try:
        end = datetime.datetime.strptime(request.args['end'], '%Y-%m-%d').date()
    except:
        end = datetime.date.today()
    start = request.args.get('start', end - datetime.timedelta(days=14))
    user_id = google.get('userinfo').data['email']
    
    logger.debug('start: {}'.format(start))
    logger.debug('end: {}'.format(end))
    logger.debug('user_id: {}'.format(user_id))
    
    user_info = dev.get_user_info(user_id, connection)
    
    balance_entries = pd.DataFrame([[datetime.date(2017, 9, 27), 10]], columns=['date', 'balance'])
    
    if user_info == None:
        logger.debug('new_user')
        balance_entries = pd.DataFrame(pd.date_range(start, end), columns=['date'])
        balance_entries['balance'] = 0
    else:
        if user_info.start <= start and user_info.end >= end:
            start_balance = dev.get_balance(user_info, start, connection)
        else:
            pass
    
#    balance_entries = models.get_balance_entries(user_id, start, end, connection)
#    
#    first = balance_entries['date'].min() if len(balance_entries) else None
#    last = balance_entries['date'].max() if len(balance_entries) else None
#    
#    logger.debug('first: {}'.format(first))
#    logger.debug('last: {}'.format(last))
#    
#    if first != start:
#        logger.debug('balance_entry not found for start')
#        previous_entry = models.get_previous_entry(user_id, start, connection)
#        logger.debug('previous_entry: {}'.format(previous_entry))
#        if previous_entry == None: # new user
#            logger.debug('new_user')
#            balance_entries = pd.DataFrame(pd.date_range(start, end), columns=['date'])
#            balance_entries['balance'] = 0
#        else:
#            if last 
#            # calculate balances from previous entry to start
#            balances = dev.populate_balances(previous_entry, start, connection)
#            logger.debug('balances: {}'.format(balances))
#    
    dates = pd.DataFrame(pd.date_range(start, end, freq='D'), columns=['date'])
    balance_entries = dates.merge(balance_entries, how='left', on='date')
#    df = df.fillna(0)
    balance_entries['date'] = balance_entries['date'].map(lambda x: x.strftime('%Y-%m-%d'))
    
    response_json = balance_entries.to_json(orient='records')
    print('response_json:', response_json)
    
    return app.response_class(
        response=response_json,
        status=200,
        mimetype='application/json'
    )    

@app.route('/create-transaction', methods=['POST'])
@login_required
def create_transaction():
    print('request.form:', request.form)

    date = request.form.get('date')
    description = request.form.get('description')
    transaction_size = request.form.get('transaction-size')
    user_id = google.get('userinfo').data['email']
    
    print('date:', date)
    print('description:', description)
    print('transaction_size:', transaction_size)
    print('user_id:', user_id)
    
    sql = ''' 
    insert into transactions (date, user_id, description, transaction_size) values  ('{}', '{}', '{}', {}) 
    '''.format(date, user_id, description, transaction_size)
    
    print('sql:', sql)
    
    cursor.execute(sql)
    connection.commit()
    
    # delete future balances
    sql = ''' 
    delete from balances where user_id = '{user_id}' and date >= '{date}'
    '''.format(user_id=user_id, date=date)
    
    cursor.execute(sql)
    connection.commit()
    
    # TODO: update balances
#    dev.update_balances
    
    # update user info
#    user_info = dev.get_user_info(user_id, connection)
#    
#    if user_info == None:
#        sql = ''' 
#        insert into user_info (
#            user_id, 
#            first_balance_entry, 
#            last_balance_entry
#        ) 
#            
#        values (
#            '{user_id}', 
#            '{date}', 
#            '{date}'
#        ) 
#        
#        '''
    
    return app.response_class(
        response=json.dumps({'status': 200, 'transaction': {}}),
        status=200,
        mimetype='application/json'
    )

#
#def login_required(f):
#    @wraps(f)
#    def decorated_function(*args, **kwargs):
#        print('session:', session)
#        print('google_token' in session)
#        if 'google_token' in session:
#            print(session['google_token'])
#            me = google.get('userinfo')
#            print(jsonify({"data": me.data}))
#            return f(*args, **kwargs)
#        else:
#            return redirect(url_for('login', next=request.url))
#    return decorated_function
#
#@app.route('/login')
#@login_required
#def login():
#    print(google.authorize(callback=url_for('authorized', _external=True)))
#    return google.authorize(callback=url_for('authorized', _external=True))
#
#@app.route('/login/authorized')
#def authorized():
#    resp = google.authorized_response()
#    if resp is None:
#        return 'Access denied: reason=%s error=%s' % (
#            request.args['error_reason'],
#            request.args['error_description']
#        )
#    session['google_token'] = (resp['access_token'], '')
#    me = google.get('userinfo')
#    return jsonify({"data": me.data})
#
#@google.tokengetter
#def get_google_oauth_token():
#    return session.get('google_token')
#
#@app.route('/')
#@login_required
#def home():
#    return render_template('home.html')

#@app.route('/sign-in', methods=['GET', 'POST'])
#def sign_in():
#    errors = []
#    if request.method == 'POST':
#        # authenticate
#        authenticated = False
#        if authenticated:
#            redirect(request.args.get('path', '/'))
#        else:
#            errors = ['Failed to authenticate']
#    return render_template('sign-in.html', errors=errors)

#@app.route('/')
#def index():
#    if 'google_token' in session:
#        me = google.get('userinfo')
#        return jsonify({"data": me.data})
#    return redirect(url_for('login'))
