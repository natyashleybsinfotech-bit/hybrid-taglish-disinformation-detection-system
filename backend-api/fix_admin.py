import mysql.connector
from mysql.connector import Error

DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "",
    "database": "taglish_db",
}

def fix_admin():
    try:
        # 1. Connect and create DB if missing
        conn = mysql.connector.connect(host=DB_CONFIG["host"], user=DB_CONFIG["user"], password=DB_CONFIG["password"])
        cur = conn.cursor()
        cur.execute(f"CREATE DATABASE IF NOT EXISTS {DB_CONFIG['database']}")
        conn.commit()
        cur.close()
        conn.close()

        # 2. Connect to the DB
        conn = mysql.connector.connect(**DB_CONFIG)
        cur = conn.cursor()

        # 3. Create table if missing
        cur.execute("""
            CREATE TABLE IF NOT EXISTS tblUsers (
                user_id INT NOT NULL AUTO_INCREMENT,
                username VARCHAR(50) NOT NULL,
                password VARCHAR(255) NOT NULL,
                full_name VARCHAR(100),
                role VARCHAR(20),
                is_active TINYINT(1) DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_login DATETIME,
                PRIMARY KEY (user_id),
                UNIQUE KEY uq_username (username)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)

        # 4. Upsert admin user
        cur.execute("SELECT * FROM tblUsers WHERE username = 'admin'")
        user = cur.fetchone()
        
        if user:
            print("Admin user found. Updating password to 'admin123' and ensuring it is active.")
            cur.execute("UPDATE tblUsers SET password = %s, is_active = 1 WHERE username = %s", ("admin123", "admin"))
        else:
            print("Admin user not found. Creating 'admin' with password 'admin123'.")
            cur.execute("INSERT INTO tblUsers (username, password, role, is_active) VALUES (%s, %s, %s, %s)", ("admin", "admin123", "admin", 1))
        
        conn.commit()
        print("Success! You can now log in with: admin / admin123")
        
        cur.close()
        conn.close()
    except Error as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    fix_admin()
