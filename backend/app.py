from flask import Flask, request, jsonify, render_template, request, redirect, session, url_for, make_response
from config import get_db_connection
import pandas as pd
import json
import re
import bcrypt
import mysql.connector
import pdfkit
from flask import send_from_directory
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from Sastrawi.StopWordRemover.StopWordRemoverFactory import StopWordRemoverFactory
from Sastrawi.Stemmer.StemmerFactory import StemmerFactory
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = 'chatbotadminsecretkey'

config = pdfkit.configuration(wkhtmltopdf="C:/Program Files/wkhtmltopdf/bin/wkhtmltopdf.exe")

stop_factory = StopWordRemoverFactory()
stopword = stop_factory.create_stop_word_remover()
stem_factory = StemmerFactory()
stemmer = stem_factory.create_stemmer()

def preprocess(text):
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s]', '', text)  # hapus simbol
    text = stopword.remove(text)            # hapus stopword
    text = stemmer.stem(text)               # stemming
    return text

def load_qa_data():
    conn = get_db_connection()
    df = pd.read_sql("SELECT * FROM qa_data", conn)
    conn.close()
    df['processed'] = df['komentar'].apply(preprocess)
    return df

df = load_qa_data()
vectorizer = TfidfVectorizer()
tfidf_matrix = vectorizer.fit_transform(df['processed'])

@app.route('/chat', methods=['POST'])
def chat():
    global df, vectorizer, tfidf_matrix

    user_input = request.json['message']
    user_processed = preprocess(user_input)

    user_vec = vectorizer.transform([user_processed])
    similarities = cosine_similarity(user_vec, tfidf_matrix)

    best_idx = similarities.argmax()
    best_score = similarities[0][best_idx]

    print(f"> User: {user_input}")
    print(f"> Best Match Score: {best_score}")

    if best_score < 0.3:
        return jsonify({"reply" : "Maaf, saya belum bisa memahami pertanyaan tersebut."})

    matched_row = df.iloc[best_idx]
    return jsonify({"reply": matched_row['jawaban'], "intent" : matched_row['label_intent']})

@app.route('/')
def serve_index():
    return send_from_directory('../frontend', 'index.html')

@app.route('/<path:path>')
def serve_static_file(path):
    return send_from_directory('../frontend', path)

@app.route('/meeting', methods=['POST'])
def submit_meeting():
    data = request.json
    conn = get_db_connection()
    cursor = conn.cursor()

    query = """
        INSERT INTO meetings (name, email, topic, date, time)
        VALUES (%s, %s, %s, %s, %s)
    """
    values = (data['name'], data['email'], data['topic'], data['date'], data['time'])
    cursor.execute(query, values)
    conn.commit()
    cursor.close()
    conn.close()
    
    return jsonify({"message" : "Berhasil diajukan"})

@app.route('/feedback', methods=['POST'])
def submit_feedback():
    data = request.json
    conn = get_db_connection()
    cursor = conn.cursor()

    query = """
        INSERT INTO feedback (message, intent, rating)
        VALUES (%s, %s, %s)
    """
    values = (data['message'], data['intent'], data['rating'])
    cursor.execute(query, values)
    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({"message": "Feedback disimpan"})

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM admin_users WHERE username = %s", (username,))
        admin = cursor.fetchone()
        cursor.close()
        conn.close()

        if admin and bcrypt.checkpw(password.encode('utf-8'), admin['password_hash'].encode('utf-8')):
          session['username'] = admin['username']
          return redirect('/admin/dashboard')
        else:
            return "Login gagal. Username atau password salah.", 401

    return render_template('login.html')     

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('admin_login'))

@app.route('/admin/dashboard')
def admin_dashboard():
    if 'username' not in session:
        return redirect(url_for('admin_login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT COUNT(*) AS total FROM feedback")
    total_questions = cursor.fetchone()['total']

    cursor.execute("SELECT COUNT(*) AS answered FROM feedback WHERE rating = 'Membantu'")
    answered = cursor.fetchone()['answered']

    cursor.execute("SELECT COUNT(*) AS unanswered FROM feedback WHERE rating = 'Tidak Membantu'")
    unanswered = cursor.fetchone()['unanswered']
    
    cursor.execute("""
        SELECT
            SUM(CASE WHEN rating = 'Membantu' THEN 1 ELSE 0 END) AS helpful,
            SUM(CASE WHEN rating = 'Tidak Membantu' THEN 1 ELSE 0 END) AS not_helpful
        FROM feedback
    """)
    feedback_summary = cursor.fetchone()

    cursor.execute("""
        SELECT intent, COUNT(*) AS jumlah
        FROM feedback
        GROUP BY intent
        ORDER BY jumlah DESC
        LIMIT 3
    """)

    popular_intents =[row['intent'] for row in cursor.fetchall()]

    cursor.execute("""
        SELECT
            intent,
            COUNT(*) AS total,
            SUM(CASE WHEN rating = 'Membantu' THEN 1 ELSE 0 END) AS helpful,
            SUM(CASE WHEN rating = 'Tidak Membantu' THEN 1 ELSE 0 END) AS not_helpful
        FROM feedback
        GROUP BY intent
        ORDER BY total DESC
    """)

    intent_stats = cursor.fetchall()

    total_feedback = feedback_summary['helpful'] + feedback_summary['not_helpful']
    helpful_percent = round((feedback_summary['helpful'] / total_feedback) * 100, 1) if total_feedback > 0 else 0
    not_helpful_percent = round((feedback_summary['not_helpful'] / total_feedback) * 100, 1) if total_feedback > 0 else 0

    conn.close()
    
    return render_template("dashboard.html",
                            total_questions=total_questions,
                            answered=answered,
                            unanswered=unanswered,
                            popular_intents=popular_intents,
                            feedback_summary=feedback_summary,
                            intent_stats=intent_stats,
                            helpful_percent=helpful_percent,
                            not_helpful_percent=not_helpful_percent)

@app.route("/admin/manage-qa")
def manage_qa():
    if 'username' not in session:
        return redirect(url_for('admin_login'))
    
    return render_template("manage_qa.html")

@app.route('/admin/qa', methods=['GET'])
def get_all_qa():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM qa_data")
    data = cursor.fetchall()
    conn.close()
    return jsonify(data)

@app.route('/admin/qa', methods=['POST'])
def add_qa():
    data = request.json
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO qa_data (komentar, label_intent, jawaban) VALUES (%s, %s, %s)",
        (data['komentar'], data['label_intent'], data['jawaban'])
    )
    conn.commit()
    conn.close()
    return jsonify({"message": "Q&A berhasil ditambahkan"})

@app.route('/admin/qa/<int:id>', methods=['PUT'])
def update_qa(id):
    data = request.json
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE qa_data SET komentar=%s, label_intent=%s, jawaban=%s WHERE id=%s",
        (data['komentar'], data['label_intent'], data['jawaban'], id)
    )
    conn.commit()
    conn.close()
    return jsonify({"message": "Q&A berhasil diperbaharui"})

@app.route('/admin/qa/<int:id>', methods=['DELETE'])
def delete_qa(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM qa_data WHERE id=%s", (id,))
    conn.commit()
    conn.close()
    return jsonify({"message": "Q&A berhasil dihapus"})

@app.route('/admin/answers', methods=['GET'])
def get_unique_answers():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
       SELECT label_intent, MAX(jawaban) AS jawaban            
       FROM qa_data
       GROUP BY label_intent
    """)
    data = cursor.fetchall()
    conn.close()
    return jsonify(data)

@app.route('/admin/answers/<intent>', methods=['PUT'])
def update_answer(intent):
    data = request.json
    new_jawaban = data['jawaban']
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE qa_data SET jawaban=%s WHERE label_intent=%s",
        (new_jawaban, intent)
    )
    conn.commit()
    conn.close()
    return jsonify({"message": "Jawaban berhasil diperbarui"})


@app.route('/admin/answers/<intent>', methods=['DELETE'])
def delete_answer(intent):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM qa_data WHERE label_intent = %s", (intent,))
    conn.commit()
    conn.close()
    return jsonify({"message": "Jawaban berhasil dihapus"})

@app.route("/admin/manage-meeting")
def manage_meeting():
    if 'username' not in session:
        return redirect(url_for('admin_login'))
    
    return render_template("manage_meeting.html")

@app.route("/admin/meetings", methods=['GET'])
def get_meetings():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM meetings ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()

    for row in rows:
        if isinstance(row.get("created_at"), (datetime, timedelta)):
            row["created_at"] = str(row["created_at"])
        if isinstance(row.get("time"), (datetime, timedelta)):
            row["time"] = str(row["time"])

    return jsonify(rows)

@app.route('/admin/meetings/<int:id>', methods=['PUT'])
def update_meeting_status(id):
    data = request.json
    new_status = data.get("status")
    new_date = data.get("date")
    new_time = data.get("time")

    conn = get_db_connection()
    cursor = conn.cursor()

    # Jika hanya update status
    if new_date and new_time:
        cursor.execute("""
            UPDATE meetings SET status = %s, date = %s, time = %s WHERE id = %s
        """, (new_status, new_date, new_time, id))
    else:
        cursor.execute("UPDATE meetings SET status = %s WHERE id = %s", (new_status, id))

    conn.commit()
    conn.close()
    return jsonify({"message": "Status meeting berhasil diperbarui"})

@app.route("/admin/reports")
def report_page():
    if 'username' not in session:
        return redirect(url_for('admin_login'))

    return render_template("report.html")

@app.route("/admin/api/chatbot-summary")
def chatbot_summary():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT COUNT(*) AS total_pertanyaan FROM feedback")
    total_pertanyaan = cursor.fetchone()["total_pertanyaan"]

    cursor.execute("""
        SELECT intent, COUNT(*) AS jumlah
        FROM feedback
        WHERE intent != 'unknown'
        GROUP BY intent
        ORDER BY jumlah DESC
        LIMIT 1        
    """)
    populer = cursor.fetchone()
    intent_populer = populer["intent"] if populer else "-"
    jumlah_populer = populer["jumlah"] if populer else 0

    cursor.execute("SELECT COUNT(*) AS terjawab FROM feedback WHERE intent != 'unknown'")
    terjawab = cursor.fetchone()["terjawab"]

    cursor.execute("SELECT COUNT(*) AS tidak_terjawab FROM feedback WHERE intent = 'unknown'")
    tidak_terjawab = cursor.fetchone()["tidak_terjawab"]

    cursor.execute("SELECT COUNT(*) AS positif FROM feedback WHERE rating = 'membantu'")
    positif = cursor.fetchone()["positif"]

    feedback_positif = round((positif / total_pertanyaan) * 100) if total_pertanyaan > 0 else 0

    conn.close()

    return jsonify({
        "total_pertanyaan": total_pertanyaan,
        "intent_populer": intent_populer,
        "jumlah_populer": jumlah_populer,
        "terjawab": terjawab,
        "tidak_terjawab": tidak_terjawab,
        "feedback_positif": feedback_positif
    })

@app.route("/admin/api/intent-statistics")
def intent_statistics():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT intent,
               COUNT(*) AS jumlah,
               SUM(CASE WHEN rating = 'membantu' THEN 1 ELSE 0 END) AS positif
        FROM feedback
        WHERE intent != 'unknown'
        GROUP BY intent
        ORDER BY jumlah DESC
    """)

    data = cursor.fetchall()
    conn.close()
    return jsonify(data)

@app.route("/admin/api/meeting-report")
def meeting_report():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT name, email, topic, date, time, status, created_at 
        FROM meetings
        ORDER BY created_at DESC
    """)
    data = cursor.fetchall()
    conn.close()

    for item in data:
        item["created_at"] = str(item["created_at"])
        item["date"] = str(item["date"]) if item["date"] else "-"
        item["time"] = str(item["time"]) if item["time"] else "-"

    return jsonify(data)

@app.route("/admin/api/feedback-report")
def feedback_report():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT message, intent, rating, date
        FROM feedback
        ORDER BY date DESC
    """)
    data = cursor.fetchall()
    conn.close()

    for item in data:
        item["date"] = str(item["date"])
    return jsonify(data)

@app.route('/admin/export/<string:report_type>')
def export_report_pdf(report_type):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if report_type == 'summary':
        cursor.execute("SELECT COUNT(*) AS total FROM feedback")
        total = cursor.fetchone()['total']

        cursor.execute("SELECT COUNT(*) AS terjawab FROM feedback WHERE intent != 'unknown'")
        terjawab = cursor.fetchone()['terjawab']

        cursor.execute("SELECT COUNT(*) AS tidak_terjawab FROM feedback WHERE intent = 'unknown'")
        tidak_terjawab = cursor.fetchone()['tidak_terjawab']

        cursor.execute("""
            SELECT intent, COUNT(*) AS jumlah
            FROM feedback
            WHERE intent != 'unknown'
            GROUP BY intent
            ORDER BY jumlah DESC
            LIMIT 1
        """)
        populer = cursor.fetchone()
        intent_populer = populer["intent"] if populer else "-"
        jumlah_populer = populer["jumlah"] if populer else 0

        cursor.execute("SELECT COUNT(*) AS positif FROM feedback WHERE rating = 'membantu'")
        positif = cursor.fetchone()["positif"]

        feedback_positif = round((positif / total) * 100) if total else 0

        html = render_template("pdf_summary.html", 
            total=total,
            terjawab=terjawab,
            tidak_terjawab=tidak_terjawab,
            intent_populer=intent_populer,
            jumlah_populer=jumlah_populer,
            feedback_positif=feedback_positif
    )


    elif report_type == 'intent':
        cursor.execute("""
            SELECT intent,
                COUNT(*) AS jumlah,
                SUM(CASE WHEN rating = 'membantu' THEN 1 ELSE 0 END) AS positif
            FROM feedback
            WHERE intent != 'unknown'
            GROUP BY intent
            ORDER BY jumlah DESC
        """)
        data = cursor.fetchall()
        html = render_template("pdf_intent.html", intents=data)

    elif report_type == 'meeting':
        cursor.execute("SELECT name, topic, date, time, status FROM meetings ORDER BY created_at DESC")
        data = cursor.fetchall()
        html = render_template("pdf_meeting.html", meetings=data)

    elif report_type == 'feedback':
        cursor.execute("SELECT message, intent, rating, date FROM feedback ORDER BY date DESC")
        data = cursor.fetchall()
        html = render_template("pdf_feedback.html", feedbacks=data)

    else:
        return "Jenis laporan tidak dikenal", 404

    conn.close()

    pdf = pdfkit.from_string(html, False, configuration=config)
    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=laporan_{report_type}.pdf'
    return response

if __name__ == '__main__':
    app.run(debug=True, port=5001)