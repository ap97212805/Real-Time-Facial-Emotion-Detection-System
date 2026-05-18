import io
import os
import json
import base64
import glob
from datetime import datetime
from collections import defaultdict

import numpy as np
import cv2
from PIL import Image
from flask import Flask, request, jsonify, render_template, send_from_directory, send_file
from emotion_detector import predict_emotion_from_image
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.units import inch

app = Flask(__name__)

# Removed FER detector, using custom CNN

session_data = {
    "start_time": datetime.now(),
    "detections": [],
    "emotion_counts": defaultdict(int),
    "total_detections": 0,
    "assessment": {
        "frequency_count": 0,  
        "pronunciation_level": 85,  
        "nervousness": 0,  
        "hr_assessment": 0  
    }
}






session_data.update({
    "paused": False,
    "paused_at": None,
    "total_paused_seconds": 0,
    "target_duration_minutes": None
})





EMOTION_DISEASE_MAP = {
    "angry": [
        "Heart disease",
        "High blood pressure",
        "Tachycardia"
    ],
    "disgust": [
        "Psoriasis",
        "Atopic dermatitis"
    ],
    "fear": [
        "Fibromyalgia",
        "Migraines",
        "Irritable bowel syndrome"
    ],
    "sad": [
        "Depression",
        "Anxiety disorders",
        "Hypothyroidism"
    ]
}

NO_RISK_EMOTIONS = {"happy", "neutral", "surprise"}





@app.route("/")
def index():
    return render_template("index.html")

@app.route("/analytics")
def analytics_page():
    return render_template("analytics.html")

@app.route("/history")
def history_page():
    return render_template("history.html")

@app.route("/sessions_list")
def sessions_list_page():
    return render_template("sessions_list.html")

@app.route("/settings")
def settings_page():
    return render_template("settings.html")





def read_base64_image(data_url: str) -> np.ndarray:
    if "," in data_url:
        data_url = data_url.split(",")[1]
    img_bytes = base64.b64decode(data_url)
    img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    return np.array(img)

def normalize_emotions(emotions: dict) -> dict:
    total = sum(emotions.values()) or 1.0
    return {k: round(v / total, 3) for k, v in emotions.items()}

def calculate_assessment_metrics(detections):
    """Calculate interview assessment metrics from emotion detections"""
    if not detections:
        return {
            "frequency_count": 0,
            "pronunciation_level": 85,
            "nervousness": 0,
            "hr_assessment": 50
        }

    


    fear_count = sum(1 for d in detections if d["emotion"] == "fear")
    angry_count = sum(1 for d in detections if d["emotion"] == "angry")
    surprise_count = sum(1 for d in detections if d["emotion"] == "surprise")

    total_detections = len(detections)
    nervousness_score = ((fear_count + angry_count + surprise_count) / total_detections) * 100
    nervousness_score = min(100, nervousness_score * 2)  

    




    happy_count = sum(1 for d in detections if d["emotion"] == "happy")
    neutral_count = sum(1 for d in detections if d["emotion"] == "neutral")
    sad_count = sum(1 for d in detections if d["emotion"] == "sad")

    positive_ratio = (happy_count + neutral_count) / total_detections
    hr_score = (positive_ratio * 100) - (sad_count / total_detections * 50) - (nervousness_score * 0.3)
    hr_score = max(0, min(100, hr_score))

    


    now = datetime.now()
    elapsed_seconds = (now - session_data["start_time"]).total_seconds()
    elapsed_seconds -= session_data.get("total_paused_seconds", 0)
    session_duration_minutes = max(1, elapsed_seconds / 60)
    frequency_count = int(total_detections * 2.5 / session_duration_minutes)  

    
    base_pronunciation = 85
    nervousness_penalty = nervousness_score * 0.2
    pronunciation_level = max(60, base_pronunciation - nervousness_penalty)

    return {
        "frequency_count": frequency_count,
        "pronunciation_level": round(pronunciation_level, 1),
        "nervousness": round(nervousness_score, 1),
        "hr_assessment": round(hr_score, 1)
    }


@app.route("/api/analytics")
def get_analytics():
    total = len(session_data["detections"])
    duration = int((datetime.now() - session_data["start_time"]).total_seconds())

    counts = defaultdict(int)
    for d in session_data["detections"]:
        counts[d["emotion"]] += 1

    most = max(counts, key=counts.get) if counts else None
    percentages = {k: round((v/total)*100, 1) for k,v in counts.items()} if total else {}

    
    assessment = calculate_assessment_metrics(session_data["detections"])

    return jsonify({
        "total_detections": total,
        "most_detected_emotion": most,
        "session_duration": duration,
        "emotion_percentages": percentages,
        "assessment": assessment
    })


@app.route("/api/history")
def get_history():
    return jsonify(session_data["detections"])

@app.route("/api/save", methods=["POST"])
def save_session():
    
    session_data["assessment"] = calculate_assessment_metrics(session_data["detections"])

    os.makedirs("sessions", exist_ok=True)
    filename = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    path = os.path.join("sessions", filename)

    with open(path, "w") as f:
        json.dump(session_data, f, indent=2, default=str)

    return jsonify({"status":"ok", "filename":filename})

@app.route("/api/sessions")
def list_sessions():
    if not os.path.exists("sessions"):
        return jsonify([])
    files = []
    for f in os.listdir("sessions"):
        with open(os.path.join("sessions", f)) as fp:
            data = json.load(fp)
        files.append({
            "filename": f,
            "start_time": data["start_time"],
            "total_detections": len(data["detections"])
        })
    return jsonify(files)

@app.route("/api/sessions/<filename>", methods=["DELETE"])
def delete_session(filename):
    os.remove(os.path.join("sessions", filename))
    return jsonify({"status":"deleted"})

@app.route("/sessions/<filename>")
def download_session(filename):
    return send_from_directory("sessions", filename, as_attachment=True)

@app.route("/api/assessment")
def get_assessment():
    """Get current interview assessment metrics"""
    assessment = calculate_assessment_metrics(session_data["detections"])
    return jsonify(assessment)


@app.route("/api/session_control", methods=["POST"])
def session_control():
    """Control session timing: start, pause, resume, extend (minutes)"""
    data = request.get_json() or {}
    action = data.get("action")

    if action == "start":
        
        duration_seconds = data.get("duration_seconds")
        if duration_seconds is not None:
            duration_seconds = int(duration_seconds)
            duration_seconds = max(30, min(600, duration_seconds))
        else:
            minutes = int(data.get("duration", 1))
            minutes = max(1, min(10, minutes))
            duration_seconds = minutes * 60

        session_data["start_time"] = datetime.now()
        session_data["detections"] = []
        session_data["total_paused_seconds"] = 0
        session_data["paused"] = False
        session_data["paused_at"] = None
        session_data["target_duration_seconds"] = duration_seconds
        return jsonify({"status": "started", "duration_seconds": duration_seconds})

    if action == "pause":
        if not session_data.get("paused"):
            session_data["paused"] = True
            session_data["paused_at"] = datetime.now()
        return jsonify({"status": "paused"})

    if action == "resume":
        if session_data.get("paused"):
            paused_at = session_data.get("paused_at")
            if paused_at:
                delta = (datetime.now() - paused_at).total_seconds()
                session_data["total_paused_seconds"] = session_data.get("total_paused_seconds", 0) + delta
            session_data["paused"] = False
            session_data["paused_at"] = None
        return jsonify({"status": "resumed"})

    if action == "extend":
        add_minutes = int(data.get("minutes", 1))
        if session_data.get("target_duration_seconds") is None:
            session_data["target_duration_seconds"] = 60
        session_data["target_duration_seconds"] = min(600, session_data["target_duration_seconds"] + (add_minutes * 60))
        return jsonify({"status": "extended", "new_duration_seconds": session_data["target_duration_seconds"]})

    if action == "end":
        session_data["target_duration_seconds"] = 0
        return jsonify({"status": "ended"})

    return jsonify({"error": "unknown action"}), 400


@app.route("/api/session_status")
def session_status():
    """Return session timing status including remaining seconds if target set"""
    now = datetime.now()
    elapsed = (now - session_data["start_time"]).total_seconds() - session_data.get("total_paused_seconds", 0)
    elapsed = max(0, elapsed)
    paused = session_data.get("paused", False)
    remaining = None
    if session_data.get("target_duration_seconds") is not None:
        total_seconds = session_data["target_duration_seconds"]
        remaining = max(0, int(total_seconds - elapsed))

    return jsonify({
        "elapsed_seconds": int(elapsed),
        "paused": bool(paused),
        "remaining_seconds": remaining,
        "target_duration_seconds": session_data.get("target_duration_seconds")
    })



EMOTION_DISEASE_PROB = {
    "angry": {
        "Heart Disease": 65,
        "Hypertension": 70,
        "Stroke Risk": 40
    },
    "fear": {
        "Anxiety Disorder": 75,
        "Panic Attacks": 60,
        "IBS": 45
    },
    "sad": {
        "Depression": 80,
        "Sleep Disorder": 55,
        "Hormonal Imbalance": 35
    },
    "disgust": {
        "Skin Disorder": 50,
        "Autoimmune Risk": 30
    }
}


def predict_disease_from_history(detections):
    if not detections:
        return {
            "emotion": "No data",
            "risk": "No Risk",
            "diseases": []
        }

    counts = defaultdict(int)
    for d in detections:
        counts[d["emotion"]] += 1

    dominant = max(counts, key=counts.get)

    if dominant in NO_RISK_EMOTIONS:
        return {
            "emotion": dominant.capitalize(),
            "risk": "No Risk",
            "diseases": []
        }

    return {
        "emotion": dominant.capitalize(),
        "risk": "Possible Risk",
        "diseases": EMOTION_DISEASE_MAP.get(dominant, [])
    }


@app.route("/predict", methods=["POST"])
def predict():
    data = request.get_json(force=True)
    if not data or "image" not in data:
        return jsonify({"error": "image required"}), 400

    img = read_base64_image(data["image"])

    h, w = img.shape[:2]
    if max(h, w) > 800:
        scale = 800 / max(h, w)
        img = cv2.resize(img, (int(w * scale), int(h * scale)))

    # Use custom CNN for emotion detection
    detections = predict_emotion_from_image(img)
    if not detections:
        return jsonify({"faces": [], "emotion": "no_face", "score": 0})

    # Get the first face detection
    face = detections[0]
    best_emotion = face["emotion"]
    best_score = face["score"]

    session_data["detections"].append({
        "emotion": best_emotion,
        "score": round(best_score, 3),
        "timestamp": datetime.now().isoformat()
    })
    session_data["detections"] = session_data["detections"][-120:]

    return jsonify({
        "faces": [{
            "emotion": best_emotion,
            "score": best_score
        }],
        "emotion": best_emotion,
        "score": best_score
    })

@app.route("/api/predict_disease")
def predict_disease():
    if not session_data["detections"]:
        return jsonify({
            "emotion": "No data",
            "confidence": 0,
            "diseases": {}
        })

    
    recent_detections = session_data["detections"][-5:] if len(session_data["detections"]) >= 5 else session_data["detections"]
    
    emotion_counts = defaultdict(int)
    total_confidence = 0
    
    for detection in recent_detections:
        emotion_counts[detection["emotion"]] += 1
        total_confidence += detection["score"]
    
    dominant_emotion = max(emotion_counts, key=emotion_counts.get)
    avg_confidence = total_confidence / len(recent_detections)

    diseases = {}
    if dominant_emotion in EMOTION_DISEASE_PROB:
        for d, p in EMOTION_DISEASE_PROB[dominant_emotion].items():
            diseases[d] = round(p * avg_confidence, 1)

    return jsonify({
        "emotion": dominant_emotion,
        "confidence": round(avg_confidence, 3),
        "diseases": diseases
    })





@app.route("/api/reset", methods=["POST"])
def reset_session():
    session_data["detections"].clear()
    return jsonify({"status": "reset"})


def generate_session_report_pdf(session_data_param=None):
    """Generate PDF report for completed session"""
    
    data = session_data_param if session_data_param else session_data
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30,
        alignment=1  
    )
    story.append(Paragraph("Interview Assessment Report", title_style))
    story.append(Spacer(1, 12))

    
    session_info = f"Session Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br/>"
    if data.get("target_duration_minutes"):
        session_info += f"Target Duration: {data['target_duration_minutes']} minutes<br/>"
    
    
    if data.get("start_time") and isinstance(data["start_time"], datetime):
        elapsed = (datetime.now() - data["start_time"]).total_seconds() - data.get("total_paused_seconds", 0)
        session_info += f"Actual Duration: {int(elapsed // 60)}m {int(elapsed % 60)}s<br/>"
    
    session_info += f"Total Detections: {len(data.get('detections', []))}"

    story.append(Paragraph(session_info, styles['Normal']))
    story.append(Spacer(1, 20))

    
    assessment = calculate_assessment_metrics(data.get("detections", []))

    story.append(Paragraph("Assessment Results", styles['Heading2']))
    story.append(Spacer(1, 12))

    assessment_data = [
        ["Metric", "Value"],
        ["Speaking Frequency", f"{assessment['frequency_count']} WPM"],
        ["Pronunciation Level", f"{assessment['pronunciation_level']}%"],
        ["Nervousness Level", f"{assessment['nervousness']}%"],
        ["HR Assessment Score", f"{assessment['hr_assessment']}/100"]
    ]

    assessment_table = Table(assessment_data, colWidths=[2*inch, 2*inch])
    assessment_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 14),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    story.append(assessment_table)
    story.append(Spacer(1, 20))

    
    story.append(Paragraph("Emotion Breakdown", styles['Heading2']))
    story.append(Spacer(1, 12))

    emotion_counts = defaultdict(int)
    for d in data.get("detections", []):
        emotion_counts[d["emotion"]] += 1

    total = len(data.get("detections", []))
    emotion_data = [["Emotion", "Count", "Percentage"]]
    emotions = ["angry", "disgust", "fear", "happy", "sad", "surprise", "neutral"]
    for emotion in emotions:
        count = emotion_counts[emotion]
        percentage = round((count / total * 100), 1) if total > 0 else 0
        emotion_data.append([emotion.capitalize(), str(count), f"{percentage}%"])

    emotion_table = Table(emotion_data, colWidths=[1.5*inch, 1*inch, 1.5*inch])
    emotion_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.lightblue),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    story.append(emotion_table)

    doc.build(story)
    buffer.seek(0)
    return buffer


@app.route("/api/generate_report")
def generate_report():
    """Generate and return PDF report for current session"""
    try:
        pdf_buffer = generate_session_report_pdf()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"interview_report_{timestamp}.pdf"

        return send_file(
            pdf_buffer,
            as_attachment=True,
            download_name=filename,
            mimetype='application/pdf'
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/generate_report/<filename>")
def generate_report_for_session(filename):
    """Generate and return PDF report for a specific saved session"""
    try:
        
        session_file = os.path.join("sessions", filename)
        if not os.path.exists(session_file):
            return jsonify({"error": "Session not found"}), 404
            
        with open(session_file, 'r') as f:
            saved_session_data = json.load(f)
        
        
        if "start_time" in saved_session_data:
            saved_session_data["start_time"] = datetime.fromisoformat(saved_session_data["start_time"])
        
        pdf_buffer = generate_session_report_pdf(saved_session_data)
        
        
        pdf_filename = filename.replace('.json', '.pdf')

        return send_file(
            pdf_buffer,
            as_attachment=True,
            download_name=pdf_filename,
            mimetype='application/pdf'
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500






if __name__ == "__main__":
    print("Starting Flask server...")
    app.run(debug=True)
