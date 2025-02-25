import os
import psycopg2
import requests
import re
import time

DB_CONFIG = {
    "dbname": os.getenv("POSTGRES_DB"),
    "user": os.getenv("POSTGRES_USER"),
    "password": os.getenv("POSTGRES_PASSWORD"),
    "host": os.getenv("POSTGRES_HOST"),
    "port": os.getenv("POSTGRES_PORT"),
}

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "deepseek-r1:8b"

def get_pg_connection():
    try:
        return psycopg2.connect(**DB_CONFIG)
    except psycopg2.Error as e:
        return None

def query_ollama(prompt):
    payload = {"model": MODEL, "prompt": prompt, "stream": False}
    try:
        response = requests.post(OLLAMA_URL, json=payload)
        response.raise_for_status()
        response_data = response.json()
        return response_data.get("response", "").strip()
    except requests.RequestException:
        return None

def clean_sql_response(sql_response):
    think_match = re.search(r"<think>(.*?)</think>", sql_response, flags=re.DOTALL)
    think_text = think_match.group(1).strip() if think_match else None

    sql_match = re.search(r"```sql(.*?)```", sql_response, flags=re.DOTALL)
    sql_query = sql_match.group(1).strip() if sql_match else None

    if not sql_query:
        return None, None, "Failed to extract SQL query from AI response."

    return sql_query, think_text, None

def execute_sql(sql):
    conn = get_pg_connection()
    if not conn:
        return (None, None), "Database connection failed."

    try:
        with conn.cursor() as cur:
            cur.execute(sql)
            column_names = [desc[0] for desc in cur.description] if cur.description else []
            rows = cur.fetchall() if column_names else []
            return (column_names, rows), None
    except psycopg2.Error as e:
        return None, str(e)
    finally:
        conn.close()

def refine_sql_with_feedback(sql, error_msg):
    feedback_prompt = f"""
    The following SQL query failed to execute:

    ```sql
    {sql}
    ```

    The error message returned was:
    "{error_msg}"

    Please generate only the corrected SQL query with no additional explanation or comments.
    """

    refined_sql_response = query_ollama(feedback_prompt)

    return refined_sql_response

def format_human_response(user_question, columns, rows):
    if not rows:
        return "No relevant expense transactions found."

    if len(columns) == 1 and len(rows) == 1 and isinstance(rows[0][0], (int, float)):
        result_text = f"The {columns[0].replace('_', ' ')} is {rows[0][0]}."
    else:
        result_text = f"### Results for: *{user_question}*\n\n"
        result_text += f"| {' | '.join(columns)} |\n"
        result_text += f"| {' | '.join(['-' * len(col) for col in columns])} |\n"

        for row in rows:
            result_text += f"| {' | '.join(map(str, row))} |\n"

    insights_prompt = f"""
    You are an expert in financial analysis. Based on the retrieved data below, derive some useful insights:

    ### User's Question:
    {user_question}

    ### Retrieved Data:
    - **Columns:** {columns}
    - **Result/Answer for the question:** {rows}

    ### Instructions:
    - Identify **patterns**, **outliers**, or **trends**.
    - Highlight **high spending areas**, **frequent transactions**, or **unusual activity**.
    - Keep it concise but **valuable**.
    - Do **not** restate the table—just provide **useful insights**.
    - Do **not** do financial analysis if the result set is COUNT or SUM and returns a single record. Instead just state that plainly

    Provide your insights below:
    """
    
    ai_insights = query_ollama(insights_prompt)

    ai_insights = re.sub(r"<think>.*?</think>", "", ai_insights, flags=re.DOTALL).strip()

    return result_text + "\n\n### AI Insights:\n" + ai_insights

MAX_RETRIES = 3

import time

MAX_RETRIES = 3

def ask_financial_question(user_question, return_sql=False, return_result=False):
    sql_prompt = f"""
        You are an expert in SQL. Your task is to generate a valid PostgreSQL query for the given question.

        ### User Question:
        "{user_question}"

        ### Database Schema:
        The database table 'bank_transactions' contains the following columns:
        - name (VARCHAR(50), NOT NULL): The name of the person or entity associated with the transaction.
        - date (DATE, NOT NULL): The transaction date in YYYY-MM-DD format.
        - posting_date (DATE, NOT NULL): The date when the transaction was posted in YYYY-MM-DD format.
        - amount (DECIMAL(10,2), NOT NULL): The amount of the transaction.
        - transaction_type (VARCHAR(10)): The type of transaction (e.g., Expense, Income).
        - description (TEXT, NOT NULL): A detailed description of the transaction.
        - month_year (VARCHAR(7), NOT NULL): The month and year of the transaction in 'YYYY-MM' format.

        ### Output Rules:
        1. **STRICTLY output only the SQL query inside triple backticks (` ```sql ... ``` `).**
        2. **Do NOT include explanations, comments, or descriptions outside these sections.**
        3. **If the question asks for total expenses, use `SUM(amount) AS total_expense`.**
        4. **If the question asks for individual transactions, select `name, date, amount, transaction_type, description` and DO NOT use `SUM()` or `GROUP BY`.**
        5. **If the question asks for "top" or "largest" or "smallest" or "lowest" transactions, use `ORDER BY amount DESC LIMIT X`.**
        6. **If filtering by a specific month, use `EXTRACT(MONTH FROM date) = MM` instead of checking `month_year = 'YYYY-MM'`.**
        7. **Ensure the SQL query is fully executable in PostgreSQL.**
        8. **Do NOT include unnecessary placeholders or variable names—use real column names directly.**
        9. **Only return ONE SQL query. No explanations.**
        """

    print(f"\n[INFO] Processing user question: {user_question}")

    sql_response = query_ollama(sql_prompt)
    print(f"[INFO] Initial SQL response from AI: {sql_response}")

    sql, think_text, error = clean_sql_response(sql_response)

    if error:
        print(f"[ERROR] AI did not return a valid SQL query: {error}")
        return (None, "AI failed to generate a valid query.", None, None)

    all_think_texts = [think_text] if think_text else []
    if think_text:
        print(f"[THINK] AI Thought Process: {think_text}")

    for attempt in range(MAX_RETRIES):
        print(f"\n[INFO] Attempt {attempt + 1}: Executing SQL Query")
        print(f"[SQL] {sql}")

        result, error_msg = execute_sql(sql)

        if result is not None and not error_msg:
            print(f"[SUCCESS] SQL executed successfully on attempt {attempt + 1}")
            break

        print(f"[WARNING] SQL execution failed: {error_msg}")
        
        if attempt < MAX_RETRIES - 1:
            print(f"[INFO] Retrying SQL refinement (Attempt {attempt + 2})...")

            sql = refine_sql_with_feedback(sql, error_msg)
            sql, think_text, error = clean_sql_response(sql)

            if error:
                print(f"[ERROR] Failed to extract clean SQL in retry.")
                return (None, "SQL refinement failed.", None, all_think_texts)

            if think_text:
                all_think_texts.append(think_text)
                print(f"[THINK] AI Thought Process (Retry {attempt + 1}): {think_text}")

            time.sleep(1)
        else:
            print(f"[ERROR] Maximum retries reached. Failed to generate a valid SQL query.")
            return (sql, "Failed after multiple retries.", None, all_think_texts)

    columns, rows = result
    ai_response = format_human_response(user_question, columns, rows)

    print(f"[INFO] Final AI Response: {ai_response}")
    print(f"[INFO] AI Thought Process across retries: {all_think_texts}")

    return (sql, ai_response, {"columns": columns, "rows": rows}, all_think_texts) if return_sql and return_result else (ai_response, all_think_texts)

if __name__ == "__main__":
    ask_financial_question('which item is my biggest expense?')