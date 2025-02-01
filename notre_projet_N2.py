from flask import Flask, jsonify, request
from flask_mysqldb import MySQL
from flask_cors import CORS
from flask import send_from_directory
from flask import Flask, request, jsonify
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__ ,static_folder='static')
app.secret_key = 'your_secret_key'
CORS(app)

# إعدادات قاعدة البيانات
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'super_d1'

mysql = MySQL(app)

# صفحة جذرية
@app.route('/')
def home():
    return jsonify({"message": "Welcome to the Football Management API"})

# استرجاع ملفات ثابتة
@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory(app.static_folder, filename)

# استرجاع الترتيب
@app.route('/api/classement', methods=['GET'])
def get_classement():
    try:
        cur = mysql.connection.cursor()
        cur.execute("""
            SELECT Nom_equipe, Matches_joues, Victoires, Nuls, Defaites, Points, Buts_marques, Buts_encaisses, logo_url 
            FROM classement ORDER BY Points DESC, Victoires DESC
        """)
        data = cur.fetchall()
        print(f"Fetched Data: {data}")  # طباعة البيانات المستردة
        cur.close()
        return jsonify([{
            "Nom_equipe": row[0],
            "Matches_joues": row[1],
            "Victoires": row[2],
            "Nuls": row[3],
            "Defaites": row[4],
            "Points": row[5],
            "Buts_marques": row[6],
            "Buts_encaisses": row[7],
            "logo_url": row[8]
        } for row in data])
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"error": f"Failed to fetch classement: {str(e)}"}), 500

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json  # استلام البيانات من Flutter
    email = data.get('email')
    password = data.get('password')

    # البحث عن المستخدم في قاعدة البيانات
    cur = mysql.connection.cursor()
    cur.execute("SELECT id, password FROM users WHERE email = %s", (email,))
    user = cur.fetchone()
    cur.close()

    if user:
        stored_password = user[1]
        if check_password_hash(stored_password, password):
            # تسجيل الدخول بنجاح
            return jsonify({"success": True, "message": "Login successful", "user_id": user[0]})
        else:
            return jsonify({"success": False, "message": "Incorrect password"})
    else:
        return jsonify({"success": False, "message": "Email not found"})

@app.route('/signup', methods=['POST'])
def signup():
    data = request.json  # استلام البيانات كـ JSON
    email = data.get('email')
    password = data.get('password')
    confirm_password = data.get('confirm_password')

    # التحقق من كلمات المرور
    if password != confirm_password:
        return jsonify({"success": False, "message": "Passwords do not match"}), 400

    # التحقق مما إذا كان البريد الإلكتروني موجودًا بالفعل
    cur = mysql.connection.cursor()
    cur.execute("SELECT id FROM users WHERE email = %s", (email,))
    existing_user = cur.fetchone()

    if existing_user:
        return jsonify({"success": False, "message": "Email already exists"}), 400

    # تشفير كلمة المرور وإضافتها إلى قاعدة البيانات
    hashed_password = generate_password_hash(password)
    cur.execute("INSERT INTO users (email, password, role) VALUES (%s, %s, 'user')",
                (email, hashed_password))
    mysql.connection.commit()
    cur.close()

    return jsonify({"success": True, "message": "Account created successfully"}), 201
# استرجاع المباريات
@app.route('/api/matches', methods=['GET'])
def get_matches():
    try:
        cur = mysql.connection.cursor()
        cur.execute("""
            SELECT 
                m.ID_match,
                
                m.id_semaine, 
                c1.Nom_equipe AS equipe1, 
                c1.logo_url AS logo1, 
                m.Score_equipe1, 
                m.Score_equipe2, 
                c2.Nom_equipe AS equipe2, 
                c2.logo_url AS logo2, 
                m.date 
            FROM matchs m
            JOIN classement c1 ON m.ID_equipe1 = c1.ID_equipe
            JOIN classement c2 ON m.ID_equipe2 = c2.ID_equipe
        """)
        data = cur.fetchall()
        cur.close()
        return jsonify([{
            "ID_match" : row[0],
            "id_semaine": row[1],
            "equipe1": row[2],
            "logo1": row[3],
            "Score_equipe1": row[4],
            "Score_equipe2": row[5],
            "equipe2": row[6],
            "logo2": row[7],
            "date": row[8].strftime("%Y-%m-%d %H:%M:%S")
        } for row in data])
    except Exception as e:
        return jsonify({"error": f"Failed to fetch matches: {str(e)}"}), 500
def update_team_stats(cur, team1_id, team2_id, score1, score2):
    # تحديث إحصائيات الفريق الأول
    if score1 > score2:
        cur.execute("""
            UPDATE classement 
            SET Matches_joues = Matches_joues + 1,
                Victoires = Victoires + 1,
                Points = Points + 3,
                Buts_marques = Buts_marques + %s,
                Buts_encaisses = Buts_encaisses + %s
            WHERE ID_equipe = %s
        """, (score1, score2, team1_id))
    elif score1 < score2:
        cur.execute("""
            UPDATE classement 
            SET Matches_joues = Matches_joues + 1,
                Defaites = Defaites + 1,
                Buts_marques = Buts_marques + %s,
                Buts_encaisses = Buts_encaisses + %s
            WHERE ID_equipe = %s
        """, (score1, score2, team1_id))
    else:
        cur.execute("""
            UPDATE classement 
            SET Matches_joues = Matches_joues + 1,
                Nuls = Nuls + 1,
                Points = Points + 1,
                Buts_marques = Buts_marques + %s,
                Buts_encaisses = Buts_encaisses + %s
            WHERE ID_equipe = %s
        """, (score1, score2, team1_id))

    # تحديث إحصائيات الفريق الثاني
    if score2 > score1:
        cur.execute("""
            UPDATE classement 
            SET Matches_joues = Matches_joues + 1,
                Victoires = Victoires + 1,
                Points = Points + 3,
                Buts_marques = Buts_marques + %s,
                Buts_encaisses = Buts_encaisses + %s
            WHERE ID_equipe = %s
        """, (score2, score1, team2_id))
    elif score2 < score1:
        cur.execute("""
            UPDATE classement 
            SET Matches_joues = Matches_joues + 1,
                Defaites = Defaites + 1,
                Buts_marques = Buts_marques + %s,
                Buts_encaisses = Buts_encaisses + %s
            WHERE ID_equipe = %s
        """, (score2, score1, team2_id))
    else:
        cur.execute("""
            UPDATE classement 
            SET Matches_joues = Matches_joues + 1,
                Nuls = Nuls + 1,
                Points = Points + 1,
                Buts_marques = Buts_marques + %s,
                Buts_encaisses = Buts_encaisses + %s
            WHERE ID_equipe = %s
        """, (score2, score1, team2_id))

# إضافة مباراة جديدة
@app.route('/api/add_match', methods=['POST'])
def add_match():
    try:
        data = request.json
        print("Received data:", data)  # للتأكد من البيانات المستلمة

        equipe1 = data['equipe1']
        equipe2 = data['equipe2']
        score1 = int(data['score1'])
        score2 = int(data['score2'])
        semaine = data['semaine'].replace('Semaine ', '')  # إزالة كلمة "Semaine"
        date = data['date']

        # التحقق من صحة البيانات
        if not all([equipe1, equipe2, score1 is not None, score2 is not None, semaine, date]):
            return jsonify({"error": "Missing required fields"}), 400

        if equipe1 == equipe2:
            return jsonify({"error": "Team A and Team B cannot be the same"}), 400

        cur = mysql.connection.cursor()

        # التحقق من وجود الفرق
        cur.execute("SELECT ID_equipe FROM classement WHERE Nom_equipe = %s", (equipe1,))
        team1_id = cur.fetchone()
        cur.execute("SELECT ID_equipe FROM classement WHERE Nom_equipe = %s", (equipe2,))
        team2_id = cur.fetchone()

        if not team1_id or not team2_id:
            return jsonify({"error": "One or both teams not found"}), 404

        # التحقق من عدم وجود مباراة في نفس الأسبوع
        cur.execute("""
            SELECT COUNT(*) FROM matchs 
            WHERE (ID_equipe1 = %s OR ID_equipe2 = %s OR ID_equipe1 = %s OR ID_equipe2 = %s)
            AND id_semaine = %s
        """, (team1_id[0], team1_id[0], team2_id[0], team2_id[0], semaine))

        if cur.fetchone()[0] > 0:
            return jsonify({"error": "One or both teams already have a match this week"}), 400

        # إضافة المباراة
        cur.execute("""
            INSERT INTO matchs (ID_equipe1, ID_equipe2, Score_equipe1, Score_equipe2, id_semaine, date)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (team1_id[0], team2_id[0], score1, score2, semaine, date))

        # تحديث إحصائيات الفرق
        update_team_stats(cur, team1_id[0], team2_id[0], score1, score2)

        mysql.connection.commit()
        cur.close()

        return jsonify({"message": "Match added successfully"}), 201

    except Exception as e:
        print("Error:", str(e))  # للتأكد من الخطأ
        return jsonify({"error": f"Failed to add match: {str(e)}"}), 500



@app.route('/api/weeks', methods=['GET'])
def get_weeks():
    return jsonify([{"id": i} for i in range(1, 21)])

# تحديث الترتيب
def update_ranking(equipe1, equipe2, score1, score2):
    cur = mysql.connection.cursor()
    if score1 > score2:
        cur.execute("UPDATE classement SET Points = Points + 3 WHERE Nom_equipe = %s", (equipe1,))
    elif score1 < score2:
        cur.execute("UPDATE classement SET Points = Points + 3 WHERE Nom_equipe = %s", (equipe2,))
    else:
        cur.execute("UPDATE classement SET Points = Points + 1 WHERE Nom_equipe = %s", (equipe1,))
        cur.execute("UPDATE classement SET Points = Points + 1 WHERE Nom_equipe = %s", (equipe2,))
    mysql.connection.commit()
    cur.close()
def revert_team_stats(cur, team1_id, team2_id, score1, score2):
    # إلغاء تأثير النتيجة القديمة على الفريق الأول
    if score1 > score2:
        cur.execute("""
            UPDATE classement 
            SET Matches_joues = Matches_joues - 1,
                Victoires = Victoires - 1,
                Points = Points - 3,
                Buts_marques = Buts_marques - %s,
                Buts_encaisses = Buts_encaisses - %s
            WHERE ID_equipe = %s
        """, (score1, score2, team1_id))
    elif score1 < score2:
        cur.execute("""
            UPDATE classement 
            SET Matches_joues = Matches_joues - 1,
                Defaites = Defaites - 1,
                Buts_marques = Buts_marques - %s,
                Buts_encaisses = Buts_encaisses - %s
            WHERE ID_equipe = %s
        """, (score1, score2, team1_id))
    else:
        cur.execute("""
            UPDATE classement 
            SET Matches_joues = Matches_joues - 1,
                Nuls = Nuls - 1,
                Points = Points - 1,
                Buts_marques = Buts_marques - %s,
                Buts_encaisses = Buts_encaisses - %s
            WHERE ID_equipe = %s
        """, (score1, score2, team1_id))

    # إلغاء تأثير النتيجة القديمة على الفريق الثاني
    if score2 > score1:
        cur.execute("""
            UPDATE classement 
            SET Matches_joues = Matches_joues - 1,
                Victoires = Victoires - 1,
                Points = Points - 3,
                Buts_marques = Buts_marques - %s,
                Buts_encaisses = Buts_encaisses - %s
            WHERE ID_equipe = %s
        """, (score2, score1, team2_id))
    elif score2 < score1:
        cur.execute("""
            UPDATE classement 
            SET Matches_joues = Matches_joues - 1,
                Defaites = Defaites - 1,
                Buts_marques = Buts_marques - %s,
                Buts_encaisses = Buts_encaisses - %s
            WHERE ID_equipe = %s
        """, (score2, score1, team2_id))
    else:
        cur.execute("""
            UPDATE classement 
            SET Matches_joues = Matches_joues - 1,
                Nuls = Nuls - 1,
                Points = Points - 1,
                Buts_marques = Buts_marques - %s,
                Buts_encaisses = Buts_encaisses - %s
            WHERE ID_equipe = %s
        """, (score2, score1, team2_id))


@app.route('/api/update_match/<int:match_id>', methods=['PUT'])
def update_match(match_id):
    try:
        data = request.json
        print("Received  data for update:", data)  # للتأكد من البيانات المستلمة

        equipe1 = data['equipe1']
        equipe2 = data['equipe2']
        score1 = int(data['score1'])
        score2 = int(data['score2'])
        semaine = data['semaine'].replace('Semaine ', '') if isinstance(data['semaine'], str) else data['semaine']
        date = data['date']

        # التحقق من صحة البيانات
        if not all([equipe1, equipe2, score1 is not None, score2 is not None, semaine, date]):
            return jsonify({"error": "Missing required fields"}), 400

        if equipe1 == equipe2:
            return jsonify({"error": "Team A and Team B cannot be the same"}), 400

        cur = mysql.connection.cursor()

        # الحصول على بيانات المباراة القديمة
        cur.execute("""
            SELECT m.ID_equipe1, m.ID_equipe2, m.Score_equipe1, m.Score_equipe2
            FROM matchs m
            WHERE m.ID_match = %s
        """, (match_id,))
        old_match = cur.fetchone()

        if not old_match:
            return jsonify({"error": "Match not found"}), 404

        old_team1_id, old_team2_id, old_score1, old_score2 = old_match

        # الحصول على معرفات الفرق الجديدة
        cur.execute("SELECT ID_equipe FROM classement WHERE Nom_equipe = %s", (equipe1,))
        team1_id = cur.fetchone()
        cur.execute("SELECT ID_equipe FROM classement WHERE Nom_equipe = %s", (equipe2,))
        team2_id = cur.fetchone()

        if not team1_id or not team2_id:
            return jsonify({"error": "One or both teams not found"}), 404

        # التحقق من عدم وجود مباراة أخرى في نفس الأسبوع للفرق الجديدة
        if team1_id[0] != old_team1_id or team2_id[0] != old_team2_id:
            cur.execute("""
                SELECT COUNT(*) FROM matchs 
                WHERE (ID_equipe1 = %s OR ID_equipe2 = %s OR ID_equipe1 = %s OR ID_equipe2 = %s)
                AND id_semaine = %s
                AND ID_match != %s
            """, (team1_id[0], team1_id[0], team2_id[0], team2_id[0], semaine, match_id))

            if cur.fetchone()[0] > 0:
                return jsonify({"error": "One or both teams already have a match this week"}), 400

        # إلغاء تأثير المباراة القديمة
        revert_team_stats(cur, old_team1_id, old_team2_id, old_score1, old_score2)

        # تحديث بيانات المباراة
        cur.execute("""
            UPDATE matchs 
            SET ID_equipe1 = %s,
                ID_equipe2 = %s,
                Score_equipe1 = %s,
                Score_equipe2 = %s,
                id_semaine = %s,
                date = %s
            WHERE ID_match = %s
        """, (team1_id[0], team2_id[0], score1, score2, semaine, date, match_id))

        # تحديث إحصائيات الفرق بالنتيجة الجديدة
        update_team_stats(cur, team1_id[0], team2_id[0], score1, score2)

        mysql.connection.commit()
        cur.close()

        return jsonify({"message": "Match updated successfully"}), 200

    except Exception as e:
        print("Error updating match:", str(e))
        return jsonify({"error": f"Failed to update match: {str(e)}"}), 500

# مسار لحذف مباراة
@app.route('/api/delete_match/<int:match_id>', methods=['DELETE'])
def delete_match(match_id):
    try:
        cur = mysql.connection.cursor()

        # الحصول على بيانات المباراة قبل حذفها
        cur.execute("""
            SELECT ID_equipe1, ID_equipe2, Score_equipe1, Score_equipe2
            FROM matchs
            WHERE ID_match = %s
        """, (match_id,))
        match = cur.fetchone()

        if not match:
            return jsonify({"error": "Match not found"}), 404

        team1_id, team2_id, score1, score2 = match

        # إلغاء تأثير المباراة على الترتيب
        revert_team_stats(cur, team1_id, team2_id, score1, score2)

        # حذف المباراة
        cur.execute("DELETE FROM matchs WHERE ID_match = %s", (match_id,))

        mysql.connection.commit()
        cur.close()

        return jsonify({"message": "Match deleted successfully"}), 200

    except Exception as e:
        print("Error deleting match:", str(e))
        return jsonify({"error": f"Failed to delete match: {str(e)}"}), 500




app.debug = True

app.run(host="0.0.0.0", port=5001 )