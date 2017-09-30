import os
import datetime
import simplejson as json
import flask
import psycopg2
import numpy as np
import pandas as pd
from functools import wraps
from flask import Flask, render_template, g, request, redirect, url_for, session, jsonify
from flask_oauthlib.client import OAuth


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
    print('get-balance')
    try:
        end = datetime.datetime.strptime(request.args['end'], '%Y-%m-%d').date()
    except:
        end = datetime.date.today()
    start = request.args.get('start', end - datetime.timedelta(days=14))
    user_id = google.get('userinfo').data['email']
    
    print('start:', start)
    print('end:', end)
    print('user_id:', user_id)
    
    sql = ''' 
    select
        date,
        balance
        
    from balances
    
    where user_id = '{user_id}'
        and date >= '{start}'
        and date <= '{end}'
        
    order by 1

    '''.format(start=start, end=end, user_id=user_id)
    print('sql:', sql)

    df = pd.read_sql(sql, connection)
    print('df:', df)
    
    start_ = df['date'].min()
    end_ = df['date'].max()
    
    print('start_:', start_)
    print('end_:', end_)
    
    if start_ != start:
        print('balance entry for start date not found')
        sql = ''' 
        with last_entry as (
            select
                user_id,
                max(date) as date
                
            from balances
            
            where user_id = '{user_id}'
                and date < '{start}'
            
            group by 1
            
        )
        
        select balance from balances join last_entry using (user_id, date)
        
        '''.format(user_id=user_id, start=start)
        
        df_ = pd.read_sql(sql, connection)
        
        print('last_entry:', df_)
        
        if len(df_) == 0:
            # found no previous balance
            date_range = pd.date_range(start, start_ - datetime.timedelta(days=1) if not np.isnan(start_) else end)
            df = pd.DataFrame(date_range, columns=['date'])
            df['user_id'] = user_id
            df['balance'] = 0.0
            values = ', '.join(df.apply(lambda x: '''('{}', '{}', {})'''.format(x.user_id, x.date.strftime('%Y-%m-%d'), x.balance), axis=1))
            sql = '''
            insert into balances (user_id, date, balance) values {values}
            '''.format(values=values)
            print('sql:', sql)
            cursor.execute(sql)
            connection.commit()

        # did not find start, find last entry before start and propagate to start or initialise to 0
#        pass
#        df = pd.concat([df_start, df])
#    if end_ != end:
#        pass
#        df = pd.concat([df, df_end])
        # dif not find end, find last entry before end and propagate to end
#    if(len(df) == 0):
#        print('no balance entries found for {} creating balance entries'.format(user_id))
#        date_range = pd.date_range(start, end)
#        df = pd.DataFrame()
#        df['date'] = date_range
#        df['user_id'] = user_id
#        df['balance'] = 0
#        print('df:', df)
#        values = ', '.join(df.apply(lambda x: '''('{}', '{}', {})'''.format(x.user_id, x.date.strftime('%Y-%m-%d'), x.balance), axis=1))
#        sql = '''
#        insert into balances (user_id, date, balance) values {values}
#        '''.format(values=values)
#        print('sql:', sql)
#        cursor.execute(sql)
#        connection.commit()
    
#    dates = pd.DataFrame(pd.date_range(start, end, freq='D'), columns=['date'])
#    df = dates.merge(df, how='left', on='date')
#    df = df.fillna(0)
    df['date'] = df['date'].map(lambda x: x.strftime('%Y-%m-%d'))
    
    response_json = df.to_json(orient='records')
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
    user = google.get('userinfo').data['email']
    
    print('date:', date)
    print('description:', description)
    print('transaction_size:', transaction_size)
    print('user:', user)
    
    sql = ''' 
    insert into transactions (date, user_id, description, transaction_size) values  ('{}', '{}', '{}', {}) 
    '''.format(date, user, description, transaction_size)
    
    print('sql:', sql)
    
    cursor.execute(sql)
    connection.commit()
    
    # delete future balances
    sql = ''' 
    delete from balances where user_id = '{user_id}' and date >= '{date}'
    '''
    
    cursor.execute(sql)
    connection.commit()
    
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
