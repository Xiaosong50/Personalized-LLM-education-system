import pymysql

def get_db_connection():
    return pymysql.connect(
        host='localhost',
        user='admin',
        password='Lxs,123321',  # ← 修改为你的 MySQL 密码
        database='Personalized_LLM_education_system',  # ← 修改为你的数据库名
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )