from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash, check_password_hash
from flask import jsonify
from flask_login import login_required
from flask_login import LoginManager, UserMixin
import os
import pandas as pd
from flask import Flask, request, redirect, url_for, flash, render_template
from flask_mysqldb import MySQL
from flask import url_for
from functools import wraps



app = Flask(__name__)

# Configuration de la base de données MySQL
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'super_d1'
mysql = MySQL(app)

app.secret_key = 'votre_cle_secrete'  # Clé secrète pour les sessions
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  # اسم صفحة تسجيل الدخول


def update_classement(equipe, buts_marques, buts_encaisses, resultat):
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT Matches_joues, Victoires, Nuls, Defaites, Points, Buts_marques, Buts_encaisses 
        FROM classement WHERE Nom_equipe = %s
    """, (equipe,))
    stats = cur.fetchone()

    if stats:
        matches_joues, victoires, nuls, defaites, points, buts_marques_totaux, buts_encaisses_totaux = stats
        matches_joues += 1
        buts_marques_totaux += buts_marques
        buts_encaisses_totaux += buts_encaisses

        if resultat == 'victoire':
            victoires += 1
            points += 3
        elif resultat == 'nul':
            nuls += 1
            points += 1
        elif resultat == 'defaite':
            defaites += 1

        cur.execute("""
            UPDATE classement
            SET Matches_joues = %s, Victoires = %s, Nuls = %s, Defaites = %s, Points = %s, 
                Buts_marques = %s, Buts_encaisses = %s
            WHERE Nom_equipe = %s
        """, (matches_joues, victoires, nuls, defaites, points, buts_marques_totaux, buts_encaisses_totaux, equipe))
        mysql.connection.commit()
    cur.close()


# تعريف نموذج مستخدم بسيط
class User(UserMixin):
    def _init_(self, id):
        self.id = id

# وظيفة تحميل المستخدم
@login_manager.user_loader
def load_user(user_id):
    return User(user_id)


@app.route('/')
def home():
    return redirect(url_for('login'))  # تحويل إلى صفحة تسجيل الدخول


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']  # استخدام البريد الإلكتروني
        password = request.form['password']

        # البحث عن المستخدم في قاعدة البيانات
        cur = mysql.connection.cursor()
        cur.execute("SELECT id, password, role FROM users WHERE email = %s", (email,))
        user = cur.fetchone()
        cur.close()

        if user:
            stored_password = user[1]
            if check_password_hash(stored_password, password):
                # تسجيل الدخول بنجاح
                session['user_id'] = user[0]
                session['role'] = user[2]
                flash("success.", "success")
                return redirect(url_for('match_results'))
            else:
                flash("mots de passe incorrect.", "error")
        else:
            flash("email incorrect.", "error")

        return redirect(url_for('login'))

    background_image = "logos/LOGO.png"
    return render_template('login2.html', background_image=background_image)


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form['email']  # استخدام البريد الإلكتروني
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        # التحقق من كلمات المرور
        if password != confirm_password:
            flash("mots de passe ne sont pas identique.", "error")
            return redirect(url_for('signup'))

        # التحقق مما إذا كان البريد الإلكتروني موجودًا بالفعل
        cur = mysql.connection.cursor()
        cur.execute("SELECT id FROM users WHERE email = %s", (email,))
        existing_user = cur.fetchone()

        if existing_user:
            flash("email deja exist.", "error")
            return redirect(url_for('signup'))

        # هاش كلمة المرور وإضافتها إلى قاعدة البيانات
        hashed_password = generate_password_hash(password)
        cur.execute("INSERT INTO users (email, password, role) VALUES (%s, %s, 'user')",
                    (email, hashed_password))
        mysql.connection.commit()
        cur.close()

        flash("un compte a ete cree avec succee. vous pouvez connetez.", "success")
        return redirect(url_for('login'))

    background_image = "logos/LOGO.png"
    return render_template('register.html', background_image=background_image)


@app.route('/logout')
def logout():
    session.clear()
    flash("vous avez deconnecter avec succes.", "success")
    return redirect(url_for('login'))


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("يرجى تسجيل الدخول أولاً.", "error")
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'role' not in session or session['role'] != 'admin':
            flash("غير مصرح لك بالوصول إلى هذه الصفحة.", "error")
            return redirect(url_for('match_results'))  # أو أي صفحة أخرى تريد توجيه المستخدم إليها
        return f(*args, **kwargs)
    return decorated_function


@app.route('/classement')
@login_required

def Index():
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT 
            Nom_equipe,
            Matches_joues,
            Victoires,
            Nuls,
            Defaites,
            Points,
            Buts_marques,
            Buts_encaisses,
            logo_url
        FROM 
            classement
        ORDER BY 
            Points DESC, 
            Victoires DESC
    """)
    data = cur.fetchall()
    cur.close()
    total_matches = sum(row[1] for row in data)
    total_wins = sum(row[2] for row in data)
    total_draws = sum(row[3] for row in data)
    total_losses = sum(row[4] for row in data)
    return render_template('list_pt.html', EQPS=data,
                           total_matches=total_matches,
                           total_wins=total_wins,
                           total_draws=total_draws,
                           total_losses=total_losses)


@app.route('/add_match', methods=['GET', 'POST'])

@login_required
@admin_required
def add_match():
    pass
    cur = mysql.connection.cursor()
    cur.execute("SELECT Nom_equipe FROM classement")
    equipes = cur.fetchall()
    cur.close()

    if request.method == 'POST':
        equipe_a = request.form['equipe_a']
        equipe_b = request.form['equipe_b']
        try:
            score_a = int(request.form['score_equipe1'])
            score_b = int(request.form['score_equipe2'])
            semaine = int(request.form['id_semaine'])
            if semaine < 0:
                raise ValueError()
        except ValueError:
            flash("Les scores et la semaine doivent être numériques et positifs.", "error")
            return render_template('IndexMed.html', equipes=equipes)

        match_date = request.form['date']

        if not all([equipe_a, equipe_b, score_a, score_b, semaine, match_date]):
            flash("Tous les champs sont obligatoires !", "error")
            return render_template('IndexMed.html', equipes=equipes)

        if semaine > 24 or semaine < 1:
            flash("La semaine doit être comprise entre 1 et 24.", "error")
            return render_template('IndexMed.html', equipes=equipes)

        if equipe_a == equipe_b:
            flash("Erreur: une équipe ne peut pas jouer contre elle-même.", "error")
            return render_template('IndexMed.html', equipes=equipes)

        cur = mysql.connection.cursor()
        cur.execute("""
            SELECT COUNT(*) 
            FROM matchs 
            WHERE id_semaine = %s 
            AND (ID_equipe1 = (SELECT ID_equipe FROM classement WHERE Nom_equipe = %s) 
            OR ID_equipe2 = (SELECT ID_equipe FROM classement WHERE Nom_equipe = %s))
        """, (semaine, equipe_a, equipe_a))
        match_count_a = cur.fetchone()[0]

        cur.execute("""
            SELECT COUNT(*) 
            FROM matchs 
            WHERE id_semaine = %s 
            AND (ID_equipe1 = (SELECT ID_equipe FROM classement WHERE Nom_equipe = %s) 
            OR ID_equipe2 = (SELECT ID_equipe FROM classement WHERE Nom_equipe = %s))
        """, (semaine, equipe_b, equipe_b))
        match_count_b = cur.fetchone()[0]

        if match_count_a > 0:
            flash(f"L'équipe {equipe_a} ne peut pas jouer plus d'une fois dans la même semaine.", "error")
            return render_template('IndexMed.html', equipes=equipes)

        if match_count_b > 0:
            flash(f"L'équipe {equipe_b} ne peut pas jouer plus d'une fois dans la même semaine.", "error")
            return render_template('IndexMed.html', equipes=equipes)

        cur.execute("""
            INSERT INTO matchs (ID_equipe1, ID_equipe2, Score_equipe1, Score_equipe2, id_semaine, date)
            VALUES (
                (SELECT ID_equipe FROM classement WHERE Nom_equipe = %s),
                (SELECT ID_equipe FROM classement WHERE Nom_equipe = %s),
                %s, %s, %s, %s
            )
        """, (equipe_a, equipe_b, score_a, score_b, semaine, match_date))

        if score_a > score_b:
            cur.execute("""
                UPDATE classement 
                SET Points = Points + 3, Victoires = Victoires + 1, Matches_joues = Matches_joues + 1,
                    Buts_marques = Buts_marques + %s, Buts_encaisses = Buts_encaisses + %s
                WHERE Nom_equipe = %s
            """, (score_a, score_b, equipe_a))
            cur.execute("""
                UPDATE classement 
                SET Defaites = Defaites + 1, Matches_joues = Matches_joues + 1,
                    Buts_marques = Buts_marques + %s, Buts_encaisses = Buts_encaisses + %s
                WHERE Nom_equipe = %s
            """, (score_b, score_a, equipe_b))
        elif score_a < score_b:
            cur.execute("""
                UPDATE classement 
                SET Points = Points + 3, Victoires = Victoires + 1, Matches_joues = Matches_joues + 1,
                    Buts_marques = Buts_marques + %s, Buts_encaisses = Buts_encaisses + %s
                WHERE Nom_equipe = %s
            """, (score_b, score_a, equipe_b))
            cur.execute("""
                UPDATE classement 
                SET Defaites = Defaites + 1, Matches_joues = Matches_joues + 1,
                    Buts_marques = Buts_marques + %s, Buts_encaisses = Buts_encaisses + %s
                WHERE Nom_equipe = %s
            """, (score_a, score_b, equipe_a))
        else:
            cur.execute("""
                UPDATE classement 
                SET Points = Points + 1, Nuls = Nuls + 1, Matches_joues = Matches_joues + 1,
                    Buts_marques = Buts_marques + %s, Buts_encaisses = Buts_encaisses + %s
                WHERE Nom_equipe = %s
            """, (score_a, score_b, equipe_a))
            cur.execute("""
                UPDATE classement 
                SET Points = Points + 1, Nuls = Nuls + 1, Matches_joues = Matches_joues + 1,
                    Buts_marques = Buts_marques + %s, Buts_encaisses = Buts_encaisses + %s
                WHERE Nom_equipe = %s
            """, (score_b, score_a, equipe_b))

        mysql.connection.commit()
        cur.close()
        flash("Le match a été ajouté avec succès.", "success")
        return redirect(url_for('add_match'))

    return render_template('indexMed.html', equipes=equipes)


@app.route('/match_results')
@login_required

def match_results():
    # الحصول على الأسبوع المحدد من الرابط (إذا تم تحديده)
    selected_week = request.args.get('week', type=int)
    cur = mysql.connection.cursor()

    # استعلام SQL لجلب البيانات مع تنسيق التاريخ
    if selected_week:
        cur.execute("""
            SELECT 
                m.id_semaine, 
                e1.Nom_equipe AS team1, 
                e1.logo_url AS team1_logo, 
                e2.Nom_equipe AS team2, 
                e2.logo_url AS team2_logo, 
                m.Score_equipe1, 
                m.Score_equipe2, 
                m.date,  -- استخدم التاريخ الأصلي بدلاً من التنسيق
                m.ID_match
            FROM matchs AS m
            JOIN classement AS e1 ON m.ID_equipe1 = e1.ID_equipe
            JOIN classement AS e2 ON m.ID_equipe2 = e2.ID_equipe
            WHERE m.id_semaine = %s
            ORDER BY m.id_semaine, m.ID_match
        """, (selected_week,))
    else:
        cur.execute("""
                    SELECT 
                        m.id_semaine, 
                        e1.Nom_equipe AS team1, 
                        e1.logo_url AS team1_logo, 
                        e2.Nom_equipe AS team2, 
                        e2.logo_url AS team2_logo, 
                        m.Score_equipe1, 
                        m.Score_equipe2, 
                        m.date,  -- استخدم التاريخ الأصلي بدلاً من التنسيق
                        m.ID_match
                    FROM matchs AS m
                    JOIN classement AS e1 ON m.ID_equipe1 = e1.ID_equipe
                    JOIN classement AS e2 ON m.ID_equipe2 = e2.ID_equipe
                    ORDER BY m.id_semaine, m.ID_match
                """)


    # جلب البيانات
    data2 = cur.fetchall()
    cur.close()

    # إرسال البيانات إلى القالب
    return render_template('list_Med.html', QP=data2, selected_week=selected_week)


@app.route('/get_available_rounds', methods=['GET'])
def get_available_rounds():
    equipe_a = request.args.get('equipe_a')
    equipe_b = request.args.get('equipe_b')

    if not equipe_a or not equipe_b:
        return {"rounds": []}

    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT id_semaine 
        FROM matchs 
        WHERE ID_equipe1 = (SELECT ID_equipe FROM classement WHERE Nom_equipe = %s)
        OR ID_equipe2 = (SELECT ID_equipe FROM classement WHERE Nom_equipe = %s)
    """, (equipe_a, equipe_a))
    rounds_a = {row[0] for row in cur.fetchall()}

    cur.execute("""
        SELECT id_semaine 
        FROM matchs 
        WHERE ID_equipe1 = (SELECT ID_equipe FROM classement WHERE Nom_equipe = %s)
        OR ID_equipe2 = (SELECT ID_equipe FROM classement WHERE Nom_equipe = %s)
    """, (equipe_b, equipe_b))
    rounds_b = {row[0] for row in cur.fetchall()}

    cur.close()

    all_rounds = set(range(1, 25))
    available_rounds = list(all_rounds - rounds_a - rounds_b)

    return {"rounds": sorted(available_rounds)}






@app.route('/modifie_match/<int:match_id>', methods=['GET', 'POST'])
@login_required
@admin_required

def modifie_match(match_id):
    cur = mysql.connection.cursor()

    if request.method == 'POST':
        # جلب القيم الجديدة من النموذج
        new_score_a = int(request.form['score_equipe1'])
        new_score_b = int(request.form['score_equipe2'])
        new_date_match = request.form['date']

        # جلب بيانات المباراة الأصلية
        cur.execute("""
            SELECT ID_equipe1, ID_equipe2, Score_equipe1, Score_equipe2 
            FROM matchs 
            WHERE ID_match = %s
        """, (match_id,))
        old_match = cur.fetchone()

        if not old_match:
            flash("le match n'exist pas.", "error")
            return redirect(url_for('match_results'))

        id_equipe1, id_equipe2, old_score_a, old_score_b = old_match

        # عكس تأثير النتيجة القديمة على الترتيب
        if old_score_a > old_score_b:
            # فريق 1 كان الفائز
            cur.execute("""
                UPDATE classement 
                SET Points = GREATEST(0, Points - 3), Victoires = GREATEST(0, Victoires - 1), Matches_joues = GREATEST(0, Matches_joues - 1),
                    Buts_marques = GREATEST(0, Buts_marques - %s), Buts_encaisses = GREATEST(0, Buts_encaisses - %s)
                WHERE ID_equipe = %s
            """, (old_score_a, old_score_b, id_equipe1))
            cur.execute("""
                UPDATE classement 
                SET Defaites = GREATEST(0, Defaites - 1), Matches_joues = GREATEST(0, Matches_joues - 1),
                    Buts_marques = GREATEST(0, Buts_marques - %s), Buts_encaisses = GREATEST(0, Buts_encaisses - %s)
                WHERE ID_equipe = %s
            """, (old_score_b, old_score_a, id_equipe2))
        elif old_score_a < old_score_b:
            # فريق 2 كان الفائز
            cur.execute("""
                UPDATE classement 
                SET Points = GREATEST(0, Points - 3), Victoires = GREATEST(0, Victoires - 1), Matches_joues = GREATEST(0, Matches_joues - 1),
                    Buts_marques = GREATEST(0, Buts_marques - %s), Buts_encaisses = GREATEST(0, Buts_encaisses - %s)
                WHERE ID_equipe = %s
            """, (old_score_b, old_score_a, id_equipe2))
            cur.execute("""
                UPDATE classement 
                SET Defaites = GREATEST(0, Defaites - 1), Matches_joues = GREATEST(0, Matches_joues - 1),
                    Buts_marques = GREATEST(0, Buts_marques - %s), Buts_encaisses = GREATEST(0, Buts_encaisses - %s)
                WHERE ID_equipe = %s
            """, (old_score_a, old_score_b, id_equipe1))
        else:
            # المباراة كانت تعادل
            cur.execute("""
                UPDATE classement 
                SET Points = GREATEST(0, Points - 1), Nuls = GREATEST(0, Nuls - 1), Matches_joues = GREATEST(0, Matches_joues - 1),
                    Buts_marques = GREATEST(0, Buts_marques - %s), Buts_encaisses = GREATEST(0, Buts_encaisses - %s)
                WHERE ID_equipe = %s
            """, (old_score_a, old_score_b, id_equipe1))
            cur.execute("""
                UPDATE classement 
                SET Points = GREATEST(0, Points - 1), Nuls = GREATEST(0, Nuls - 1), Matches_joues = GREATEST(0, Matches_joues - 1),
                    Buts_marques = GREATEST(0, Buts_marques - %s), Buts_encaisses = GREATEST(0, Buts_encaisses - %s)
                WHERE ID_equipe = %s
            """, (old_score_b, old_score_a, id_equipe2))

        # تحديث النتائج الجديدة
        cur.execute("""
            UPDATE matchs
            SET Score_equipe1 = %s, Score_equipe2 = %s, date = %s
            WHERE ID_match = %s
        """, (new_score_a, new_score_b, new_date_match, match_id))

        # تطبيق تأثير النتيجة الجديدة
        if new_score_a > new_score_b:
            cur.execute("""
                UPDATE classement 
                SET Points = Points + 3, Victoires = Victoires + 1, Matches_joues = Matches_joues + 1,
                    Buts_marques = Buts_marques + %s, Buts_encaisses = Buts_encaisses + %s
                WHERE ID_equipe = %s
            """, (new_score_a, new_score_b, id_equipe1))
            cur.execute("""
                UPDATE classement 
                SET Defaites = Defaites + 1, Matches_joues = Matches_joues + 1,
                    Buts_marques = Buts_marques + %s, Buts_encaisses = Buts_encaisses + %s
                WHERE ID_equipe = %s
            """, (new_score_b, new_score_a, id_equipe2))
        elif new_score_a < new_score_b:
            cur.execute("""
                UPDATE classement 
                SET Points = Points + 3, Victoires = Victoires + 1, Matches_joues = Matches_joues + 1,
                    Buts_marques = Buts_marques + %s, Buts_encaisses = Buts_encaisses + %s
                WHERE ID_equipe = %s
            """, (new_score_b, new_score_a, id_equipe2))
            cur.execute("""
                UPDATE classement 
                SET Defaites = Defaites + 1, Matches_joues = Matches_joues + 1,
                    Buts_marques = Buts_marques + %s, Buts_encaisses = Buts_encaisses + %s
                WHERE ID_equipe = %s
            """, (new_score_a, new_score_b, id_equipe1))
        else:
            cur.execute("""
                UPDATE classement 
                SET Points = Points + 1, Nuls = Nuls + 1, Matches_joues = Matches_joues + 1,
                    Buts_marques = Buts_marques + %s, Buts_encaisses = Buts_encaisses + %s
                WHERE ID_equipe = %s
            """, (new_score_a, new_score_b, id_equipe1))
            cur.execute("""
                UPDATE classement 
                SET Points = Points + 1, Nuls = Nuls + 1, Matches_joues = Matches_joues + 1,
                    Buts_marques = Buts_marques + %s, Buts_encaisses = Buts_encaisses + %s
                WHERE ID_equipe = %s
            """, (new_score_b, new_score_a, id_equipe2))

        mysql.connection.commit()
        cur.close()

        flash("les resultas du match et classement sont modifier avec succes.", "success")
        return redirect(url_for('match_results'))

    # جلب بيانات المباراة الحالية
    cur.execute("""
        SELECT m.Score_equipe1, m.Score_equipe2, m.date, 
               e1.Nom_equipe AS equipe_a, e2.Nom_equipe AS equipe_b
        FROM matchs AS m
        JOIN classement AS e1 ON m.ID_equipe1 = e1.ID_equipe
        JOIN classement AS e2 ON m.ID_equipe2 = e2.ID_equipe
        WHERE m.ID_match = %s
    """, (match_id,))
    match = cur.fetchone()
    cur.close()

    return render_template('list_Med_user.html', match={
        'Score_equipe1': match[0],
        'Score_equipe2': match[1],
        'date': match[2],
        'equipe_a': match[3],
        'equipe_b': match[4]
    }, match_id=match_id)


@app.route('/filter_by_week/<int:week>')
def filter_by_week(week):
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT 
            m.id_semaine, 
            e1.Nom_equipe AS team1, 
            e1.logo_url AS team1_logo, 
            e2.Nom_equipe AS team2, 
            e2.logo_url AS team2_logo, 
            m.Score_equipe1, 
            m.Score_equipe2, 
            DATE_FORMAT(m.date, '%Y-%m-%d') AS formatted_date,
            m.ID_match
        FROM matchs AS m
        JOIN classement AS e1 ON m.ID_equipe1 = e1.ID_equipe
        JOIN classement AS e2 ON m.ID_equipe2 = e2.ID_equipe
        WHERE m.id_semaine = %s
        ORDER BY m.ID_match
    """, (week,))
    data2 = cur.fetchall()
    cur.close()

    return render_template('list_Med.html', QP=data2, selected_week=week)


@app.route('/get_statistics_data')
@login_required
def get_statistics_data():
    cur = mysql.connection.cursor()

    # جلب بيانات الإحصائيات
    cur.execute("SELECT Nom_equipe, Victoires, Nuls, Defaites FROM classement")
    team_stats = cur.fetchall()
    team_labels = [row[0] for row in team_stats]
    victories = [row[1] for row in team_stats]
    draws = [row[2] for row in team_stats]
    defeats = [row[3] for row in team_stats]

    cur.execute("SELECT Nom_equipe, Buts_marques, Buts_encaisses FROM classement")
    goal_stats = cur.fetchall()
    goal_labels = [row[0] for row in goal_stats]
    goals_scored = [row[1] for row in goal_stats]
    goals_conceded = [row[2] for row in goal_stats]

    cur.close()

    return render_template(
        'statistics.html',
        team_labels=team_labels,
        victories=victories,
        draws=draws,
        defeats=defeats,
        goal_labels=goal_labels,
        goals_scored=goals_scored,
        goals_conceded=goals_conceded
    )
# معالجة ملف Excel وإدخال المباريات
def process_excel(file_path):
    try:
        # قراءة ملف Excel
        df = pd.read_excel(file_path)

        # التحقق من الأعمدة المطلوبة
        required_columns = ['Equipe1', 'Equipe2', 'Score1', 'Score2', 'Date', 'Semaine']
        if not all(col in df.columns for col in required_columns):
            return "le fichier ne contient pas les ligne demande: Equipe1, Equipe2, Score1, Score2, Date, Semaine."

        # إدخال البيانات إلى جدول المباريات وتحديث الترتيب
        cur = mysql.connection.cursor()
        for _, row in df.iterrows():
            equipe1 = row['Equipe1']
            equipe2 = row['Equipe2']
            score1 = int(row['Score1'])
            score2 = int(row['Score2'])
            match_date = row['Date']
            semaine = int(row['Semaine'])

            # إدخال المباراة
            cur.execute("""
                INSERT INTO matchs (ID_equipe1, ID_equipe2, Score_equipe1, Score_equipe2, id_semaine, date)
                VALUES (
                    (SELECT ID_equipe FROM classement WHERE Nom_equipe = %s),
                    (SELECT ID_equipe FROM classement WHERE Nom_equipe = %s),
                    %s, %s, %s, %s
                )
            """, (equipe1, equipe2, score1, score2, semaine, match_date))

            # تحديث ترتيب الفريقين بناءً على النتيجة
            if score1 > score2:
                update_classement(equipe1, score1, score2, 'victoire')
                update_classement(equipe2, score2, score1, 'defaite')
            elif score1 < score2:
                update_classement(equipe2, score2, score1, 'victoire')
                update_classement(equipe1, score1, score2, 'defaite')
            else:
                update_classement(equipe1, score1, score2, 'nul')
                update_classement(equipe2, score2, score1, 'nul')

        mysql.connection.commit()
        cur.close()
        return "fichier analyser avec succes."
    except Exception as e:
        return f"erreur lors de l'analyse du fichier: {e}"


# صفحة لتحميل ملف Excel
@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        # التحقق من اختيار الملف
        file = request.files['file']
        if not file:
            flash("يرجى اختيار ملف Excel.", "error")
            return redirect(url_for('upload'))

        # حفظ الملف في مجلد
        file_path = os.path.join('uploads', file.filename)
        os.makedirs('uploads', exist_ok=True)
        file.save(file_path)

        # معالجة الملف
        result_message = process_excel(file_path)
        flash(result_message, "success")
        return redirect(url_for('upload'))

    return render_template('ex.html')


app.debug = True

app.run(host="0.0.0.0", port=5000 )
