import os
import pandas as pd
from flask import Flask, request, redirect, url_for, flash, render_template
from flask_mysqldb import MySQL
from flask import url_for

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# إعداد قاعدة البيانات
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'password'
app.config['MYSQL_DB'] = 'database_name'

mysql = MySQL(app)

def update_classement(team, score_for, score_against, result):
    cur = mysql.connection.cursor()
    if result == 'victoire':
        cur.execute("""
            UPDATE classement
            SET Points = Points + 3, Buts_pour = Buts_pour + %s, Buts_contre = Buts_contre + %s
            WHERE Nom_equipe = %s
        """, (score_for, score_against, team))
    elif result == 'nul':
        cur.execute("""
            UPDATE classement
            SET Points = Points + 1, Buts_pour = Buts_pour + %s, Buts_contre = Buts_contre + %s
            WHERE Nom_equipe = %s
        """, (score_for, score_against, team))
    elif result == 'defaite':
        cur.execute("""
            UPDATE classement
            SET Buts_pour = Buts_pour + %s, Buts_contre = Buts_contre + %s
            WHERE Nom_equipe = %s
        """, (score_for, score_against, team))
    mysql.connection.commit()
    cur.close()

def process_excel(file_path):
    try:
        df = pd.read_excel(file_path)
        required_columns = ['Equipe1', 'Equipe2', 'Score1', 'Score2', 'Date', 'Semaine']
        if not all(col in df.columns for col in required_columns):
            return f"الملف لا يحتوي على الأعمدة المطلوبة: {required_columns}."
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        if df['Date'].isnull().any():
            return "يوجد تواريخ غير صالحة."
        cur = mysql.connection.cursor()
        for _, row in df.iterrows():
            cur.execute("""
                INSERT INTO matchs (ID_equipe1, ID_equipe2, Score_equipe1, Score_equipe2, id_semaine, date)
                VALUES (
                    (SELECT ID_equipe FROM classement WHERE Nom_equipe = %s),
                    (SELECT ID_equipe FROM classement WHERE Nom_equipe = %s),
                    %s, %s, %s, %s
                )
            """, (row['Equipe1'], row['Equipe2'], row['Score1'], row['Score2'], row['Semaine'], row['Date']))
        mysql.connection.commit()
        cur.close()
        return "تمت معالجة البيانات بنجاح."
    except Exception as e:
        return f"خطأ أثناء معالجة الملف: {e}"

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash("يرجى اختيار ملف Excel.", "error")
            return redirect(request.url)
        file = request.files['file']
        file_path = os.path.join('uploads', file.filename)
        os.makedirs('uploads', exist_ok=True)
        file.save(file_path)
        message = process_excel(file_path)
        flash(message, "success")
        return redirect(url_for('add_match'))
    print(url_for('add_match'))
    return render_template('ex.html')

if __name__ == '__main__':
    app.run(debug=True)