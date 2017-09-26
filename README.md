## Install
`conda create -n <envrionment_name> python=3`
`conda install simplejson`
`conda install flask`
`conda install psycopg2`
`conda install pandas`
`conda install flask-oauthlib`

### Install posgres Database
Create database with `balance` table

## Running Locally
e.g.
`env FLASK_APP=application FLASK_DEBUG=1 VOONG_FINANCE_DB_USER=dvoong VOONG_FINANCE_DB_PASSWORD=<password> VOONG_FINANCE_DB_HOST=127.0.0.1 VOONG_FINANCE_DB_NAME=voong_finance VOONG_FINANCE_DB_PORT=5432 flask run`
