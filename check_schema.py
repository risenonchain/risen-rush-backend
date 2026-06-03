import sqlite3

def check_table(table_name):
    try:
        conn = sqlite3.connect('risen_rush.db_v2')
        cursor = conn.cursor()
        cursor.execute(f"PRAGMA table_info({table_name});")
        columns = cursor.fetchall()
        print(f"Columns for {table_name}:")
        for col in columns:
            print(col)
        conn.close()
    except Exception as e:
        print(f"Error checking {table_name}: {e}")

check_table('game_sessions')
print("\n")
check_table('league_challenges')
