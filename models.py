import pandas as pd

def get_balance_entries(user_id, start, end, connection):
    
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
    
    return df

def get_previous_entry(user_id, date, connection):
    sql = ''' 
    with previous_entry as (
        select
            user_id,
            max(date) as date

        from balances

        where user_id = '{user_id}'
            and date < '{date}'

        group by 1

    )

    select balance from balances join previous_entry using (user_id, date)

    '''.format(user_id=user_id, date=date)

    previous_entry = pd.read_sql(sql, connection)
    previous_entry = previous_entry.loc[0]['date'] if len(previous_entry) == 1 else None
    return previous_entry
