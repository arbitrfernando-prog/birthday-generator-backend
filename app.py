import os
import json
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

# --- Проверка ключей ---
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
PIAPI_API_KEY = os.getenv("PIAPI_API_KEY")

if not DEEPSEEK_API_KEY:
    raise ValueError("Отсутствует DEEPSEEK_API_KEY")
if not PIAPI_API_KEY:
    raise ValueError("Отсутствует PIAPI_API_KEY")

# --- Конфигурация piapi ---
PIAPI_BASE_URL = "https://api.piapi.ai/api/v1"
PIAPI_TASK_URL = f"{PIAPI_BASE_URL}/task"

app = Flask(__name__)
CORS(app, origins=[
    "http://localhost:5001",
    "https://pozdrav888.tilda.ws",
    "https://www.pozdrav888.tilda.ws",
    "https://pozdravit-ai.ru",
    "https://www.pozdravit-ai.ru",
    "https://arbitrfernando-prog-birthday-generator-backend-9bd2.twc1.net"
])

# ========== ФУНКЦИИ ДЛЯ DEEPSEEK ==========
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
        response = requests.post("https://api.deepseek.com/v1/chat/completions",
                                  json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"Ошибка DeepSeek: {e}")
        return None

# ========== ТЕКСТОВЫЕ ПОЗДРАВЛЕНИЯ ==========
def build_prompt(data):
    # (без изменений, как в предыдущей версии)
    # ... (сохраняем существующую функцию)
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
    """Генерирует текст песни через DeepSeek (с учётом жанра)"""
    genre = data.get('songGenre', 'pop')
    prompt = f"""Ты — поэт-песенник. Напиши текст песни на русском языке в жанре {genre} в честь дня рождения для человека по имени {data['name']}.

Детали:
- Пол: {data['gender']}
- Возраст: {data['age']} лет
- Увлечения: {data.get('hobby', 'жизнь')}
- Черты характера: {data.get('traits', 'замечательный человек')}
- Мечты: {data.get('dreams', 'счастье')}

Структура: [Verse 1], [Chorus], [Verse 2], [Bridge], [Outro]. Текст тёплый, персонализированный, с упоминанием увлечений.
Верни ТОЛЬКО текст с тегами."""
    lyrics = deepseek_completion(prompt, max_tokens=800)
    if lyrics is None:
        # Запасной вариант
        return f"""[Verse 1]
С днём рождения, {data['name']}, сегодня твой день,
В этот праздник светлый нам грустить совсем не лень.
Ты {data.get('traits', 'замечательный')}, это знаем мы давно,
И с тобою рядом всегда нам всем тепло.

[Chorus]
Пусть сбудутся мечты, что в сердце ты хранишь,
Как яркий свет в окне, как утренняя тишь.
Твой {data.get('hobby', 'любимый досуг')} — источник вдохновения,
Желаем счастья, мира и везения!"""
    return lyrics

def create_udio_task(lyrics, data):
    """
    Отправляет задачу на генерацию музыки через piapi (точный формат из примеров).
    """
    headers = {
        "x-api-key": PIAPI_API_KEY,
        "Content-Type": "application/json"
    }

    name = data['name']
    genre = data.get('songGenre', 'pop')
    hobby = data.get('hobby', '')

    # Формируем краткий промпт (как gpt_description_prompt в примере)
    prompt = f"A {genre} birthday song for {name}, {hobby}"

    # Точный формат payload на основе примеров
    payload = {
        "model": "music-u",
        "task_type": "generate_music_custom",  # именно этот тип для своих текстов
        "input": {
            "lyrics_type": "user",
            "lyrics": lyrics,
            "prompt": prompt,
            "seed": -1
        }
    }

    try:
        response = requests.post(PIAPI_TASK_URL, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        result = response.json()
        if result.get("code") == 200 and result.get("data", {}).get("task_id"):
            return result["data"]["task_id"]
        else:
            print("Ошибка от piapi:", result)
            return None
    except Exception as e:
        print(f"Ошибка при создании задачи: {e}")
        return None

def get_udio_task_status(task_id):
    """Проверяет статус задачи (GET /api/v1/task/{task_id})"""
    url = f"{PIAPI_BASE_URL}/task/{task_id}"
    headers = {"x-api-key": PIAPI_API_KEY}

    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        if data.get("code") == 200:
            task_data = data.get("data", {})
            status = task_data.get("status")
            if status == "completed":
                audio_url = task_data.get("result", {}).get("audio_url")
                title = task_data.get("result", {}).get("title") or "Персональная песня"
                return {"ready": True, "audio_url": audio_url, "title": title}
            elif status == "failed":
                return {"ready": False, "error": "Генерация не удалась"}
            else:
                return {"ready": False, "status": status}
        else:
            return {"ready": False, "error": "Ошибка от piapi"}
    except Exception as e:
        return {"ready": False, "error": str(e)}

@app.route('/generate_song', methods=['POST'])
def generate_song():
    data = request.get_json()
    if not data or 'name' not in data:
        return jsonify({"error": "Не указано имя именинника"}), 400

    lyrics = generate_song_lyrics(data)
    if lyrics is None:
        return jsonify({"error": "Не удалось сгенерировать текст песни"}), 500

    task_id = create_udio_task(lyrics, data)
    if not task_id:
        return jsonify({"error": "Не удалось создать задачу в piapi"}), 500

    return jsonify({"task_id": task_id, "message": "Песня создаётся. Это займёт около 2 минут."})

@app.route('/song_status/<task_id>', methods=['GET'])
def song_status(task_id):
    status = get_udio_task_status(task_id)
    return jsonify(status)

@app.route('/test_udio', methods=['POST'])
def test_udio():
    data = request.get_json()
    name = data.get('name', 'друг')
    test_lyrics = f"""[Verse]
С днём рождения, {name}!
Пусть будет счастье вокруг.
[Chorus]
Это тестовая песня через piapi."""
    task_id = create_udio_task(test_lyrics, data)
    if task_id:
        return jsonify({"task_id": task_id, "message": "Тестовая задача создана"})
    else:
        return jsonify({"error": "Не удалось создать тестовую задачу"}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)
