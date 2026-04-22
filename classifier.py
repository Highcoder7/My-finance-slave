import anthropic
import json
import os
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

SYSTEM_PROMPT = """Ты финансовый классификатор. Пользователь пишет о своих тратах или доходах на русском языке.
Извлеки из текста:
1. type: "expense" (расход) или "income" (доход)
2. amount: сумма в тенге (только число, без символов)
3. category: одна категория из списка:
   - Расходы: Еда, Транспорт, Развлечения, Одежда, Здоровье, Жильё, Связь, Образование, Другое
   - Доходы: Зарплата, Фриланс, Подарок, Инвестиции, Другое
4. description: краткое описание (2-4 слова)

Отвечай ТОЛЬКО валидным JSON без пояснений и форматирования.
Пример ответа: {"type": "expense", "amount": 1500, "category": "Еда", "description": "обед в кафе"}

Если не можешь извлечь сумму или определить тип — верни: {"error": "не понял"}"""


def classify_transaction(text: str) -> dict:
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=200,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": text}]
    )
    raw = message.content[0].text.strip()
    # Strip markdown code blocks if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()
    return json.loads(raw)
