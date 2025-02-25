import pandas as pd
import datetime

def clean_and_process_csv(file_path):
    
    df = pd.read_csv(file_path, skiprows=2)

    
    expected_columns = ['date', 'posting_date', 'amount', 'description']
    if len(df.columns) == len(expected_columns):
        df.columns = expected_columns
    else:
        raise ValueError(f"Expected {len(expected_columns)} columns, but got {len(df.columns)} columns.")

    
    df['date'] = pd.to_datetime(df['date'], format='%Y%m%d').dt.strftime('%Y-%m-%d')
    df['posting_date'] = pd.to_datetime(df['posting_date'], format='%Y%m%d').dt.strftime('%Y-%m-%d')

    
    df['amount'] = pd.to_numeric(df['amount'], errors='coerce')

    
    df['transaction_type'] = df['amount'].apply(lambda x: 'Income' if x < 0 else 'Expense')

   
    df['amount'] = df['amount'].abs()

    
    df = df[~((df['description'].str.contains("PAYMENT RECEIVED - THANK YOU", case=False, na=False)) & (df['transaction_type'] == "Income"))]

    
    df['month_year'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m')

    return df
