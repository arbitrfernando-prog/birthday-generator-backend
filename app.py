import sys
import logging
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
print("=== Starting Flask app ===", flush=True)

import os
import json
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

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)
