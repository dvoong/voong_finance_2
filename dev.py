import pandas as pd

def get_user_info(user_id, connection):
    pass

# TODO
#def update_balance()
#
#    previous_balance = models.get_previous_entry(user_id, date, connection).balance
#    transactions = dev.get_transactions(user_id, date, date + datetime.timedelta(days=1), connection)
#    total_transaction_size = transactions.transaction_size.sum()
#    new_balance = previous_balance + total_transaction_size
#    sql = '''
#    insert into balances (
#        user_id,
#        date,
#        balance
#    )
#    
#    values (
#        '{user_id}',
#        '{date}',
#        {new_balance}
#    )
#    
#    '''.format(user_id=user_id, date=date, new_balance=new_balance)