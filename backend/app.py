# backend/app.py
from flask import Flask, render_template, request, redirect, session
from db_config import get_db_connection
import os

app = Flask(__name__)
app.secret_key = 'your-secret-key'
app.template_folder = '../frontend'  # 设置模板路径

@app.route('/')
def index():
    return redirect('/login')

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        try:
            conn = get_db_connection()
            with conn.cursor() as cursor:
                sql = "SELECT * FROM users WHERE email = %s AND password = %s"
                cursor.execute(sql, (email, password))
                user = cursor.fetchone()

                if user:
                    session['user_id'] = user['id']
                    session['username'] = user['username']
                    return redirect('/home')
                else:
                    error = "邮箱或密码错误"
        finally:
            conn.close()

    return render_template('login.html', error=error)


@app.route('/home', methods=['GET', 'POST'])
def home():
    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            if request.method == 'POST':
                message = request.form['message']
                cursor.execute("INSERT INTO chat_history (user_id, message_from, message) VALUES (%s, 'user', %s)", (user_id, message))
                # 模拟 LLM 回复
                response = f"你刚才说：{message}"
                cursor.execute("INSERT INTO chat_history (user_id, message_from, message) VALUES (%s, 'llm', %s)", (user_id, response))
                conn.commit()

            cursor.execute("SELECT message_from AS `from`, message AS content FROM chat_history WHERE user_id = %s ORDER BY timestamp ASC", (user_id,))
            chat_history = cursor.fetchall()
    finally:
        conn.close()

    return render_template('home.html', chat_history=chat_history, username=session['username'])

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')



@app.route('/register', methods=['GET', 'POST'])
def register():
    error = None
    success = None
    if request.method == 'POST':
        username = request.form['username'].strip()
        email = request.form['email'].strip()
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if password != confirm_password:
            error = "两次输入的密码不一致"
        elif len(password) < 6:
            error = "密码长度至少为6位"
        else:
            try:
                conn = get_db_connection()
                with conn.cursor() as cursor:
                    cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
                    existing = cursor.fetchone()
                    if existing:
                        error = "该邮箱已注册，请登录"
                    else:
                        sql = "INSERT INTO users (username, email, password) VALUES (%s, %s, %s)"
                        cursor.execute(sql, (username, email, password))  # 可改为加密密码
                        conn.commit()
                        # 登录状态保留
                        session['user_id'] = cursor.lastrowid
                        session['username'] = username
                        return redirect('/info')
            finally:
                conn.close()

    return render_template('register.html', error=error, success=success)

@app.route('/info')
def info():
    if 'user_id' not in session:
        return redirect('/login')
    return render_template('info.html')

@app.route('/save-profile', methods=['POST'])
def save_profile():
    if 'user_id' not in session:
        return redirect('/login')

    form = request.form
    liked_subjects = request.form.getlist('liked_subjects')
    liked_subjects_str = ','.join(liked_subjects)

    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            sql = """
                INSERT INTO user_profile (
                  user_id, full_name, age, gender, education_level, nationality,
                  major, degree, knowledge_level, goals, interests, liked_subjects,
                  programming_skill, math_skill, english_skill
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (
                session['user_id'],
                form['full_name'],
                form['age'],
                form['gender'],
                form['education_level'],
                form['nationality'],
                form['major'],
                form['degree'],
                form['knowledge_level'],
                form['goals'],
                form['interests'],
                liked_subjects_str,
                form['programming_skill'],
                form['math_skill'],
                form['english_skill']
            ))
            conn.commit()
    finally:
        conn.close()

    return redirect('/home')

@app.route('/settings', methods=['GET'])
def settings():
    if 'user_id' not in session:
        return redirect('/login')
    user_id = session['user_id']
    profile = {}
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM user_profile WHERE user_id = %s", (user_id,))
            profile = cursor.fetchone()
    finally:
        conn.close()
    return render_template('settings.html', profile=profile, profile_msg=None, pwd_msg=None)

@app.route('/update-profile', methods=['POST'])
def update_profile():
    if 'user_id' not in session:
        return redirect('/login')
    user_id = session['user_id']
    form = request.form
    liked_subjects = request.form.getlist('liked_subjects')
    liked_str = ','.join(liked_subjects)

    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            sql = """
            UPDATE user_profile SET
              full_name=%s, age=%s, gender=%s, education_level=%s, nationality=%s,
              major=%s, degree=%s, knowledge_level=%s,
              goals=%s, interests=%s, liked_subjects=%s,
              programming_skill=%s, math_skill=%s, english_skill=%s
            WHERE user_id=%s
            """
            cursor.execute(sql, (
                form['full_name'],
                form['age'],
                form['gender'],
                form['education_level'],
                form['nationality'],
                form['major'],
                form['degree'],
                form['knowledge_level'],
                form['goals'],
                form['interests'],
                liked_str,
                form['programming_skill'],
                form['math_skill'],
                form['english_skill'],
                user_id
            ))
            conn.commit()
            msg = "个人信息修改成功！"
            success = True
    except Exception as e:
        msg = "保存失败：" + str(e)
        success = False
    finally:
        conn.close()

    return settings_with_message(profile_msg=msg, profile_success=success)

def settings_with_message(profile_msg=None, profile_success=True, pwd_msg=None, pwd_success=True):
    user_id = session['user_id']
    conn = get_db_connection()
    profile = {}
    with conn.cursor() as cursor:
        cursor.execute("SELECT * FROM user_profile WHERE user_id = %s", (user_id,))
        profile = cursor.fetchone()
    conn.close()
    return render_template('settings.html',
        profile=profile,
        profile_msg=profile_msg, profile_success=profile_success,
        pwd_msg=pwd_msg, pwd_success=pwd_success
    )

@app.route('/change-password', methods=['POST'])
def change_password():
    if 'user_id' not in session:
        return redirect('/login')
    user_id = session['user_id']
    form = request.form
    old_pwd = form['old_password']
    new_pwd = form['new_password']
    confirm_pwd = form['confirm_password']
    msg = ""
    success = True

    if new_pwd != confirm_pwd:
        msg = "两次密码不一致"
        success = False
    elif len(new_pwd) < 6:
        msg = "新密码太短"
        success = False
    else:
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT password FROM users WHERE id = %s", (user_id,))
                user = cursor.fetchone()
                if user and user['password'] != old_pwd:
                    msg = "旧密码错误"
                    success = False
                else:
                    cursor.execute("UPDATE users SET password = %s WHERE id = %s", (new_pwd, user_id))
                    conn.commit()
                    msg = "密码修改成功！"
        finally:
            conn.close()

    return settings_with_message(pwd_msg=msg, pwd_success=success)

if __name__ == '__main__':
    app.run(debug=True)