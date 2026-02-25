import os
import json
import requests  # <-- добавлен для работы с piapi API
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from openai import OpenAI

# Загружаем переменные окружения из файла .env
load_dotenv()

# Инициализация клиента DeepSeek
client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com/v1"
)

# --- Конфигурация piapi для Udio ---
PIAPI_API_KEY = os.getenv("PIAPI_API_KEY")
PIAPI_BASE_URL = "https://api.piapi.ai/v1"

app = Flask(__name__)
# Настройка CORS – замените на ваш домен Tilda, для локального теста оставьте localhost
CORS(app, origins=["http://localhost:5001", "https://pozdrav888.tilda.ws"])

def build_prompt(data):
    """Формирует детальный промпт для генерации трёх вариантов поздравления"""
    
    # Определяем обращение в зависимости от пола
    if data['gender'] == 'female':
        dear = "Дорогая"
    else:
        dear = "Дорогой"
    
    # Отношения с поздравляющим
    relationship_map = {
        'husband': 'муж', 'wife': 'жена', 'boyfriend': 'парень',
        'girlfriend': 'девушка', 'friend': 'друг/подруга',
        'colleague': 'коллега', 'relative': 'родственник'
    }
    relationship = relationship_map.get(data.get('relationship'), 'близкий человек')
    
    # Семья (супруг, дети)
    family_parts = []
    if data.get('spouse'):
        family_parts.append(f"супруг(а) {data['spouse']}")
    if data.get('children'):
        family_parts.append(f"дети {data['children']}")
    family_text = f"Семья: {', '.join(family_parts)}. " if family_parts else ""
    
    # Мечты
    dreams_text = f"Особая мечта: {data['dreams']}. " if data.get('dreams') else ""
    
    # Стиль поздравления
    style_text = {
        'warm': 'тёплое, душевное, искреннее',
        'funny': 'с юмором, но доброе',
        'romantic': 'романтичное, нежное',
        'short': 'короткое, для смс'
    }.get(data.get('style'), 'тёплое')
    
    # Формируем промпт
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

@app.route('/generate', methods=['POST'])
def generate():
    """Основной эндпоинт с использованием нейросети"""
    try:
        data = request.get_json()
        if not data or 'name' not in data:
            return jsonify({"error": "Не указано имя именинника"}), 400

        # Формируем промпт
        prompt = build_prompt(data)

        # Вызов DeepSeek
        response = client.chat.completions.create(
            model="deepseek-chat",  # можно заменить на "deepseek-reasoner"
            messages=[{"role": "user", "content": prompt}],
            temperature=0.9,
            max_tokens=1000
        )

        result_text = response.choices[0].message.content.strip()

        # Пытаемся распарсить JSON
        try:
            variants = json.loads(result_text)
            # Проверяем, что получили список из трёх строк
            if isinstance(variants, list) and len(variants) == 3 and all(isinstance(v, str) for v in variants):
                return jsonify({"variants": variants})
            else:
                # Если структура не та, логируем и возвращаем запасной вариант
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
        return jsonify({"error": str(e)}), 500


# ========== НОВЫЕ ФУНКЦИИ ДЛЯ ГЕНЕРАЦИИ ПЕСЕН ==========

def generate_song_lyrics(data):
    """
    Генерирует текст песни на основе данных о пользователе через DeepSeek.
    Возвращает текст с разметкой [Verse], [Chorus] и т.д.
    """
    # Определяем обращение
    dear = "Дорогая" if data['gender'] == 'female' else "Дорогой"
    
    prompt = f"""Ты — поэт-песенник. Напиши текст песни на русском языке в честь дня рождения для человека по имени {data['name']}.

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
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.9,
            max_tokens=800
        )
        lyrics = response.choices[0].message.content.strip()
        return lyrics
    except Exception as e:
        print(f"Ошибка генерации текста песни: {e}")
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

def create_udio_task(lyrics, data):
    """
    Отправляет текст песни в piapi для генерации через Udio.
    Возвращает task_id или None в случае ошибки.
    """
    url = f"{PIAPI_BASE_URL}/udio/generate"
    headers = {
        "x-api-key": PIAPI_API_KEY,
        "Content-Type": "application/json"
    }
    
    # Определяем стиль из данных или по умолчанию
    style = data.get('style', 'pop')
    
    payload = {
        "model": "udio-130",  # актуальная модель Udio
        "params": {
            "prompt": f"A {style} birthday song for {data['name']}, {data.get('hobby', '')}",
            "custom_lyrics": lyrics,
            "title": f"Поздравление для {data['name']}",
            "make_instrumental": False,
            "tags": style,
            "seed": -1
        }
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        result = response.json()
        if result.get("code") == 200 and result.get("data", {}).get("task_id"):
            return result["data"]["task_id"]
        else:
            print("Ошибка от piapi:", result)
            return None
    except Exception as e:
        print(f"Ошибка при создании задачи Udio: {e}")
        return None

def get_udio_task_status(task_id):
    """Проверяет статус задачи по task_id, возвращает результат"""
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
                return {"ready": True, "audio_url": audio_url}
            elif status == "failed":
                return {"ready": False, "error": "Генерация не удалась"}
            else:
                return {"ready": False, "status": status}
        else:
            return {"ready": False, "error": "Ошибка от piapi"}
    except Exception as e:
        return {"ready": False, "error": str(e)}

# ========== НОВЫЕ ЭНДПОИНТЫ ==========

@app.route('/generate_song', methods=['POST'])
def generate_song():
    """Запускает генерацию песни: текст (DeepSeek) + музыка (Udio)"""
    data = request.get_json()
    if not data or 'name' not in data:
        return jsonify({"error": "Не указано имя именинника"}), 400

    # 1. Генерируем текст песни
    try:
        lyrics = generate_song_lyrics(data)
    except Exception as e:
        return jsonify({"error": f"Ошибка генерации текста: {str(e)}"}), 500

    # 2. Отправляем задачу в Udio
    task_id = create_udio_task(lyrics, data)
    if not task_id:
        return jsonify({"error": "Не удалось создать задачу в Udio"}), 500

    # 3. Возвращаем task_id клиенту
    return jsonify({
        "task_id": task_id,
        "message": "Песня создаётся. Это займёт около 2 минут."
    })

@app.route('/song_status/<task_id>', methods=['GET'])
def song_status(task_id):
    """Возвращает статус задачи по task_id"""
    status = get_udio_task_status(task_id)
    return jsonify(status)

@app.route('/test_udio', methods=['POST'])
def test_udio():
    """Тестовый эндпоинт для проверки Udio (без DeepSeek)"""
    data = request.get_json()
    name = data.get('name', 'друг')
    test_lyrics = f"""[Verse]
С днём рождения, {name}!
Пусть будет счастье вокруг.
[Chorus]
Это тестовая песня через piapi,
Проверяем, как работает Udio."""
    
    task_id = create_udio_task(test_lyrics, data)
    if task_id:
        return jsonify({"task_id": task_id, "message": "Тестовая задача создана"})
    else:
        return jsonify({"error": "Не удалось создать тестовую задачу"}), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)
