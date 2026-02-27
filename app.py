import os
import json
import uuid
import requests
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from dotenv import load_dotenv

# Загружаем переменные окружения из .env
load_dotenv()

# --- Проверка наличия обязательных ключей ----
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
MINIMAX_API_KEY = os.getenv("MINIMAX_API_KEY")

if not DEEPSEEK_API_KEY:
    raise ValueError("Отсутствует переменная окружения DEEPSEEK_API_KEY")
if not MINIMAX_API_KEY:
    raise ValueError("Отсутствует переменная окружения MINIMAX_API_KEY")

# --- Конфигурация MiniMax Music API ---
MINIMAX_MUSIC_URL = "https://api.minimax.io/v1/music_generation"

# --- Временная папка для сохранения аудиофайлов ---
TEMP_AUDIO_DIR = "/tmp/audio"
os.makedirs(TEMP_AUDIO_DIR, exist_ok=True)

app = Flask(__name__)
# Настройка CORS – добавьте все ваши домены
CORS(app, origins=[
    "http://localhost:5001",
    "https://pozdrav888.tilda.ws",
    "https://www.pozdrav888.tilda.ws",
    "https://pozdravit-ai.ru",
    "https://www.pozdravit-ai.ru",
    "https://arbitrfernando-prog-birthday-generator-backend-d412.twc1.net"
])

# ========== ФУНКЦИЯ ДЛЯ ПРЯМОГО ВЫЗОВА DEEPSEEK ==========
def deepseek_completion(prompt, temperature=0.9, max_tokens=1000):
    """
    Отправляет запрос к DeepSeek API и возвращает текст ответа.
    В случае ошибки возвращает None.
    """
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
    """Формирует детальный промпт для генерации трёх вариантов поздравления"""
    if data['gender'] == 'female':
        dear = "Дорогая"
    else:
        dear = "Дорогой"

    relationship_map = {
        'husband': 'муж', 'wife': 'жена', 'boyfriend': 'парень',
        'girlfriend': 'девушка', 'friend': 'друг/подруга',
        'colleague': 'коллега', 'relative': 'родственник'
    }
    relationship = relationship_map.get(data.get('relationship'), 'близкий человек')

    family_parts = []
    if data.get('spouse'):
        family_parts.append(f"супруг(а) {data['spouse']}")
    if data.get('children'):
        family_parts.append(f"дети {data['children']}")
    family_text = f"Семья: {', '.join(family_parts)}. " if family_parts else ""

    dreams_text = f"Особая мечта: {data['dreams']}. " if data.get('dreams') else ""

    style_text = {
        'warm': 'тёплое, душевное, искреннее',
        'funny': 'с юмором, но доброе',
        'romantic': 'романтичное, нежное',
        'short': 'короткое, для смс'
    }.get(data.get('style'), 'тёплое')

    prompt = f"""
Ты — мастер искренних поздравлений. Напиши **три разных варианта** поздравления с днём рождения для человека по имени {data['name']}.

Детали:
- Пол: {data['gender']}
- Возраст: {data['age']} лет
- Отношения с поздравляющим: {relationship}
- Подпись от: {data['fromName']}
- Увлечения: {data['hobby']}
- Черты характера: {data['traits']}
- {dreams_text}
- {family_text}
- Желаемый стиль: {style_text}

Требования к каждому варианту:
- Живой, естественный язык, как будто писал настоящий человек.
- Разные интонации (например, один более эмоциональный, другой – сдержанный, третий – с лёгким юмором, если уместно).
- Длина: 2–4 предложения.
- Заканчивается подписью "{data['fromName']}".

**Верни ТОЛЬКО JSON-массив из трёх строк** в формате:
["вариант 1", "вариант 2", "вариант 3"]
Никаких дополнительных пояснений, только массив.
"""
    return prompt

@app.route('/')
def index():
    return jsonify({"message": "Генератор поздравлений API работает!"})

@app.route('/test', methods=['POST'])
def test():
    """Тестовый эндпоинт (без нейросети)"""
    data = request.get_json()
    name = data.get('name', 'друг')
    gender = data.get('gender', 'female')
    from_name = data.get('fromName', 'Твой близкий')
    greeting = f"Дорогая {name}" if gender == 'female' else f"Дорогой {name}"
    variants = [
        f"{greeting}! От всей души поздравляю с днём рождения! Желаю счастья, здоровья и исполнения самых заветных желаний. Пусть каждый день дарит радость!",
        f"С днём рождения, {name}! Ты удивительный человек. Пусть мечты сбываются, а рядом будут только любящие люди. С любовью, {from_name}.",
        f"{greeting}! Желаю тебе море улыбок, солнечного настроения и ярких впечатлений. Пусть жизнь играет яркими красками!"
    ]
    return jsonify({"variants": variants})

@app.route('/generate', methods=['POST'])
def generate():
    """Основной эндпоинт для текстовых поздравлений через DeepSeek"""
    try:
        data = request.get_json()
        if not data or 'name' not in data:
            return jsonify({"error": "Не указано имя именинника"}), 400

        prompt = build_prompt(data)
        print(f"Sending prompt to DeepSeek: {prompt[:200]}...")

        result_text = deepseek_completion(prompt)

        if result_text is None:
            return jsonify({"error": "Ошибка при обращении к нейросети"}), 500

        print(f"DeepSeek response: {result_text[:200]}...")

        try:
            variants = json.loads(result_text)
            if isinstance(variants, list) and len(variants) == 3 and all(isinstance(v, str) for v in variants):
                return jsonify({"variants": variants})
            else:
                print("Некорректный формат ответа:", result_text)
                return jsonify({
                    "variants": [
                        "Не удалось сгенерировать поздравление в нужном формате.",
                        "Попробуйте ещё раз позже.",
                        "Либо обратитесь в поддержку."
                    ]
                })
        except json.JSONDecodeError:
            print("Ошибка парсинга JSON. Ответ:", result_text)
            return jsonify({
                "variants": [
                    "Не удалось сгенерировать поздравление в нужном формате.",
                    "Попробуйте ещё раз позже.",
                    "Либо обратитесь в поддержку."
                ]
            })

    except Exception as e:
        print(f"Ошибка в /generate: {e}")
        return jsonify({"error": str(e)}), 500

# ========== ФУНКЦИИ ДЛЯ ГЕНЕРАЦИИ ПЕСЕН (MiniMax Music) ==========
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

Требования к структуре:
[Verse 1] — первый куплет
[Chorus] — припев (повторяется)
[Verse 2] — второй куплет
[Bridge] — мост/переход
[Outro] — завершение

Текст должен быть тёплым, персонализированным, с упоминанием увлечений и черт характера. 
Припев должен быть запоминающимся. Используй простой, понятный язык.
Верни ТОЛЬКО текст песни с указанными тегами, без лишних пояснений.
"""
    try:
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
    except Exception as e:
        print(f"Ошибка генерации текста песни: {e}")
        return None

def create_minimax_task(lyrics, data):
    """
    Отправляет задачу на генерацию музыки через MiniMax Music API.
    Скачивает полученный файл и возвращает путь к локальному эндпоинту.
    """
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
    print("Отправка запроса на создание музыки...")

    try:
        response = requests.post(
            MINIMAX_MUSIC_URL,
            json=payload,
            headers=headers,
            timeout=120
        )
        print(f"MiniMax status code: {response.status_code}")
        print(f"MiniMax raw response: {response.text}")

        response.raise_for_status()
        result = response.json()
        print(f"MiniMax parsed response: {json.dumps(result, ensure_ascii=False)}")

        if result.get("base_resp", {}).get("status_code") == 0:
            audio_data = result.get("data", {})
            audio_url = audio_data.get("audio") or audio_data.get("url")
            if audio_url:
                # Скачиваем файл
                try:
                    audio_response = requests.get(audio_url, timeout=60)
                    audio_response.raise_for_status()
                    # Генерируем уникальное имя файла
                    filename = f"{uuid.uuid4()}.mp3"
                    filepath = os.path.join(TEMP_AUDIO_DIR, filename)
                    with open(filepath, 'wb') as f:
                        f.write(audio_response.content)
                    print(f"Аудио сохранено как {filepath}")
                    # Возвращаем путь к локальному эндпоинту
                    return f"/audio/{filename}"
                except Exception as e:
                    print(f"Ошибка при скачивании аудио: {e}")
                    return None
            else:
                print("Ошибка: в ответе нет аудио.")
                return None
        else:
            error_msg = result.get("base_resp", {}).get("status_msg", "Неизвестная ошибка")
            print(f"Ошибка от MiniMax: {error_msg}")
            return None
    except Exception as e:
        print(f"Исключение при создании задачи в MiniMax: {e}")
        return None

@app.route('/generate_song', methods=['POST'])
def generate_song():
    """Запускает генерацию песни: текст (DeepSeek) + генерация в MiniMax + локальное сохранение"""
    data = request.get_json()
    if not data or 'name' not in data:
        return jsonify({"error": "Не указано имя именинника"}), 400

    lyrics = generate_song_lyrics(data)
    if lyrics is None:
        return jsonify({"error": "Не удалось сгенерировать текст песни"}), 500

    audio_path = create_minimax_task(lyrics, data)
    if not audio_path:
        return jsonify({"error": "Не удалось создать задачу в MiniMax"}), 500

    # Возвращаем ссылку на локальный эндпоинт (полный URL формируется на фронтенде)
    return jsonify({
        "ready": True,
        "audio_url": audio_path,  # это относительный путь, например "/audio/uuid.mp3"
        "title": f"Персональная песня для {data['name']}",
        "message": "Песня успешно сгенерирована!"
    })

@app.route('/test_minimax', methods=['POST'])
def test_minimax():
    """Тестовый эндпоинт для проверки MiniMax (без генерации текста)"""
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
    """Отдаёт ранее сохранённый аудиофайл с правильными заголовками"""
    filepath = os.path.join(TEMP_AUDIO_DIR, filename)
    if not os.path.exists(filepath):
        return jsonify({"error": "Файл не найден"}), 404
    # Отдаём файл, браузер будет его проигрывать
    return send_file(filepath, mimetype='audio/mpeg', as_attachment=False)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)
