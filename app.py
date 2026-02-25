import os
import json
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
# from openai import OpenAI  # закомментировано

load_dotenv()

# DeepSeek client временно отключён
# client = OpenAI(...)

PIAPI_API_KEY = os.getenv("PIAPI_API_KEY")
PIAPI_BASE_URL = "https://api.piapi.ai/v1"

app = Flask(__name__)
CORS(app, origins=["http://localhost:5001", "https://pozdrav888.tilda.ws"])

@app.route('/')
def index():
    return jsonify({"message": "Генератор поздравлений API работает!"})

# --- Временные заглушки ---
@app.route('/generate', methods=['POST'])
def generate():
    data = request.get_json()
    name = data.get('name', 'друг')
    gender = data.get('gender', 'female')
    from_name = data.get('fromName', 'Твой близкий')
    if gender == 'female':
        greeting = f"Дорогая {name}"
    else:
        greeting = f"Дорогой {name}"
    variants = [
        f"{greeting}! От всей души поздравляю с днём рождения! Желаю счастья, здоровья и исполнения самых заветных желаний. Пусть каждый день дарит радость!",
        f"С днём рождения, {name}! Ты удивительный человек. Пусть мечты сбываются, а рядом будут только любящие люди. С любовью, {from_name}.",
        f"{greeting}! Желаю тебе море улыбок, солнечного настроения и ярких впечатлений. Пусть жизнь играет яркими красками!"
    ]
    return jsonify({"variants": variants})

@app.route('/generate_song', methods=['POST'])
def generate_song():
    return jsonify({"task_id": "test_task_123", "message": "Тестовая задача"})

@app.route('/song_status/<task_id>', methods=['GET'])
def song_status(task_id):
    return jsonify({"ready": True, "audio_url": "https://example.com/test.mp3"})

@app.route('/test_udio', methods=['POST'])
def test_udio():
    return jsonify({"task_id": "test_udio_123", "message": "Тестовая задача Udio"})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)
