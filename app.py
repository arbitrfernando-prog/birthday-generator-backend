import os
import json
import uuid
import time
import requests
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from dotenv import load_dotenv

# Загружаем переменные окружения из .env
load_dotenv()

# --- Проверка наличия обязательных ключей ---
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
MINIMAX_API_KEY = os.getenv("MINIMAX_API_KEY")

if not DEEPSEEK_API_KEY:
    raise ValueError("Отсутствует переменная окружения DEEPSEEK_API_KEY")
if not MINIMAX_API_KEY:
    raise ValueError("Отсутствует переменная окружения MINIMAX_API_KEY")

# --- Конфигурация MiniMax Music API ---
MINIMAX_MUSIC_URL = "https://api.minimax.io/v1/music_generation"
# Альтернативный URL (если основной не работает)
# MINIMAX_MUSIC_URL = "https://api.minimax.io/v1/music/generate"

TEMP_AUDIO_DIR = "/tmp/audio"
os.makedirs(TEMP_AUDIO_DIR, exist_ok=True)

app = Flask(__name__)
CORS(app, origins=[
    "http://localhost:5001",
    "https://pozdrav888.tilda.ws",
    "https://www.pozdrav888.tilda.ws",
    "https://pozdravit-ai.ru",
    "https://www.pozdravit-ai.ru",
    "https://arbitrfernando-prog-birthday-generator-backend-d412.twc1.net"
])

# ========== ФУНКЦИЯ ДЛЯ DEEPSEEK ==========
def deepseek_completion(prompt, temperature=0.9, max_tokens=1000):
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_tokens": max_tokens
    }
    try:
        response = requests.post(
            "https://api.deepseek.com/v1/chat/completions",
            json=payload,
            headers=headers,
            timeout=30
        )
        response.raise_for_status()
        result = response.json()
        return result["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"Ошибка вызова DeepSeek API: {e}")
        return None

# ========== ФУНКЦИИ ДЛЯ ТЕКСТОВЫХ ПОЗДРАВЛЕНИЙ ==========
def build_prompt(data):
    # (без изменений, оставьте как было)
    pass

@app.route('/')
def index():
    return jsonify({"message": "Генератор поздравлений API работает!"})

@app.route('/test', methods=['POST'])
def test():
    # (без изменений)
    pass

@app.route('/generate', methods=['POST'])
def generate():
    # (без изменений)
    pass

# ========== ФУНКЦИИ ДЛЯ ПЕСЕН ==========
def generate_song_lyrics(data):
    # (без изменений)
    pass

def create_minimax_task(lyrics, data):
    headers = {
        "Authorization": f"Bearer {MINIMAX_API_KEY}",
        "Content-Type": "application/json"
    }

    name = data['name']
    genre = data.get('songGenre', 'pop')
    hobby = data.get('hobby', '')
    traits = data.get('traits', '')

    prompt = f"{genre} birthday song for {name}, {traits}, likes {hobby}."

    payload = {
        "model": "music-2.5",
        "prompt": prompt,
        "lyrics": lyrics
    }

    print(f"Sending payload to MiniMax: {json.dumps(payload, ensure_ascii=False)}")

    # Настройки повторных попыток
    max_retries = 3
    timeout = 300  # секунд

    for attempt in range(max_retries):
        try:
            print(f"Попытка {attempt+1}/{max_retries}...")
            response = requests.post(
                MINIMAX_MUSIC_URL,
                json=payload,
                headers=headers,
                timeout=timeout
            )
            print(f"Статус ответа: {response.status_code}")
            print(f"Тело ответа: {response.text}")

            response.raise_for_status()
            result = response.json()

            if result.get("base_resp", {}).get("status_code") == 0:
                audio_data = result.get("data", {})
                audio_url = audio_data.get("audio") or audio_data.get("url")
                if audio_url:
                    # Скачиваем файл
                    audio_response = requests.get(audio_url, timeout=60)
                    audio_response.raise_for_status()
                    filename = f"{uuid.uuid4()}.mp3"
                    filepath = os.path.join(TEMP_AUDIO_DIR, filename)
                    with open(filepath, 'wb') as f:
                        f.write(audio_response.content)
                    print(f"Аудио сохранено: {filepath}")
                    return f"/audio/{filename}"
                else:
                    print("Ошибка: в ответе нет аудио.")
                    return None
            else:
                error_msg = result.get("base_resp", {}).get("status_msg", "Неизвестная ошибка")
                print(f"Ошибка от MiniMax: {error_msg}")
                return None

        except requests.exceptions.Timeout:
            print(f"Таймаут (попытка {attempt+1})")
            if attempt == max_retries - 1:
                print("Все попытки исчерпаны. Сервер не отвечает.")
                return None
            time.sleep(2 ** attempt)  # экспоненциальная задержка: 1, 2, 4 секунды
        except Exception as e:
            print(f"Исключение: {e}")
            return None

@app.route('/generate_song', methods=['POST'])
def generate_song():
    data = request.get_json()
    if not data or 'name' not in data:
        return jsonify({"error": "Не указано имя именинника"}), 400

    lyrics = generate_song_lyrics(data)
    if lyrics is None:
        return jsonify({"error": "Не удалось сгенерировать текст песни"}), 500

    audio_path = create_minimax_task(lyrics, data)
    if not audio_path:
        return jsonify({"error": "Не удалось создать задачу в MiniMax"}), 500

    return jsonify({
        "ready": True,
        "audio_url": audio_path,
        "title": f"Персональная песня для {data['name']}",
        "message": "Песня успешно сгенерирована!"
    })

@app.route('/test_minimax', methods=['POST'])
def test_minimax():
    data = request.get_json()
    name = data.get('name', 'друг')
    test_lyrics = f"""[Verse]
С днём рождения, {name}!
Пусть будет счастье вокруг.
[Chorus]
Это тестовая песня через MiniMax."""

    audio_path = create_minimax_task(test_lyrics, data)
    if audio_path:
        return jsonify({"audio_url": audio_path, "message": "Тестовая задача выполнена"})
    else:
        return jsonify({"error": "Не удалось создать тестовую задачу"}), 500

@app.route('/audio/<filename>')
def serve_audio(filename):
    filepath = os.path.join(TEMP_AUDIO_DIR, filename)
    if not os.path.exists(filepath):
        return jsonify({"error": "Файл не найден"}), 404
    return send_file(filepath, mimetype='audio/mpeg', as_attachment=False)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)
