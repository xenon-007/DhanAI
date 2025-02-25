import os
import psycopg2
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv("POSTGRES_HOST")
DB_PORT = os.getenv("POSTGRES_PORT")
DB_USER = os.getenv("POSTGRES_USER")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD")
DB_NAME = os.getenv("POSTGRES_DB")

def get_db_connection():
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        dbname=DB_NAME
    )

def create_table():
    query = """
    CREATE TABLE IF NOT EXISTS bank_transactions (
        id SERIAL PRIMARY KEY,
        name VARCHAR(50) NOT NULL,
        date DATE NOT NULL,
        posting_date DATE NOT NULL,
        amount DECIMAL(10,2) NOT NULL,
        transaction_type VARCHAR(10) NOT NULL CHECK (transaction_type IN ('Income', 'Expense')),
        description TEXT NOT NULL,
        month_year VARCHAR(7) NOT NULL
    );
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(query)
    conn.commit()
    cursor.close()
    conn.close()

def insert_transactions(df):
    create_table()

    conn = get_db_connection()
    cursor = conn.cursor()

    insert_query = """
    INSERT INTO bank_transactions (name, date, posting_date, amount, transaction_type, description, month_year)
    VALUES (%s, %s, %s, %s, %s, %s, %s);
    """

    records = df[['Name', 'date', 'posting_date', 'amount', 'transaction_type', 'description', 'month_year']].values.tolist()

    cursor.executemany(insert_query, records)
    conn.commit()

    cursor.close()
    conn.close()

def get_transactions(name):
    conn = get_db_connection()
    cursor = conn.cursor()

    query = "SELECT * FROM bank_transactions WHERE name = %s ORDER BY date DESC"
    cursor.execute(query, (name,))
    records = cursor.fetchall()

    columns = ['id', 'name', 'date', 'posting_date', 'amount', 'transaction_type', 'description', 'month_year']
    df = pd.DataFrame(records, columns=columns)

    cursor.close()
    conn.close()
    
    return df

def insert_manual_entry(entry):
    create_table()

    conn = get_db_connection()
    cursor = conn.cursor()

    insert_query = """
    INSERT INTO bank_transactions (name, date, posting_date, amount, transaction_type, description, month_year)
    VALUES (%s, %s, %s, %s, %s, %s, %s);
    """

    cursor.execute(insert_query, (
        entry["name"], entry["date"], entry["posting_date"], entry["amount"],
        entry["transaction_type"], entry["description"], entry["month_year"]
    ))
    conn.commit()

    cursor.close()
    conn.close()
