from datetime import datetime
import pytz
from database import get_today_transactions, get_month_transactions, get_week_transactions

ALMATY_TZ = pytz.timezone("Asia/Almaty")

MONTH_NAMES = {
    1: "Январь", 2: "Февраль", 3: "Март", 4: "Апрель",
    5: "Май", 6: "Июнь", 7: "Июль", 8: "Август",
    9: "Сентябрь", 10: "Октябрь", 11: "Ноябрь", 12: "Декабрь"
}


def _build_summary(transactions, title):
    if not transactions:
        return f"📊 *{title}*\n\nЗаписей нет."

    income = sum(t["amount"] for t in transactions if t["type"] == "income")
    expenses = sum(t["amount"] for t in transactions if t["type"] == "expense")

    expense_cats = {}
    income_cats = {}
    for t in transactions:
        if t["type"] == "expense":
            expense_cats[t["category"]] = expense_cats.get(t["category"], 0) + t["amount"]
        else:
            income_cats[t["category"]] = income_cats.get(t["category"], 0) + t["amount"]

    text = f"📊 *{title}*\n\n"

    if income > 0:
        text += f"💚 *Доходы: +{income:,.0f} ₸*\n"
        for cat, amount in sorted(income_cats.items(), key=lambda x: -x[1]):
            text += f"  • {cat}: {amount:,.0f} ₸\n"
        text += "\n"

    if expenses > 0:
        text += f"❤️ *Расходы: -{expenses:,.0f} ₸*\n"
        for cat, amount in sorted(expense_cats.items(), key=lambda x: -x[1]):
            text += f"  • {cat}: {amount:,.0f} ₸\n"
        text += "\n"

    balance = income - expenses
    emoji = "📈" if balance >= 0 else "📉"
    text += f"{emoji} *Итог: {'+' if balance >= 0 else ''}{balance:,.0f} ₸*"

    return text


def format_daily_report(user_id):
    transactions = get_today_transactions(user_id)
    return _build_summary(transactions, "Сводка за сегодня")


def format_week_report(user_id):
    transactions = get_week_transactions(user_id)
    return _build_summary(transactions, "Статистика за 7 дней")


def format_monthly_report(user_id):
    now = datetime.now(ALMATY_TZ)
    transactions = get_month_transactions(user_id)

    if not transactions:
        return f"📅 *Отчёт за {MONTH_NAMES[now.month]} {now.year}*\n\nЗаписей нет."

    income = sum(t["amount"] for t in transactions if t["type"] == "income")
    expenses = sum(t["amount"] for t in transactions if t["type"] == "expense")

    expense_cats = {}
    income_cats = {}
    for t in transactions:
        if t["type"] == "expense":
            expense_cats[t["category"]] = expense_cats.get(t["category"], 0) + t["amount"]
        else:
            income_cats[t["category"]] = income_cats.get(t["category"], 0) + t["amount"]

    text = f"📅 *Полный отчёт за {MONTH_NAMES[now.month]} {now.year}*\n"
    text += f"Операций: {len(transactions)}\n\n"

    if income > 0:
        text += f"💚 *Доходы: +{income:,.0f} ₸*\n"
        for cat, amount in sorted(income_cats.items(), key=lambda x: -x[1]):
            pct = amount / income * 100
            text += f"  • {cat}: {amount:,.0f} ₸ ({pct:.0f}%)\n"
        text += "\n"

    if expenses > 0:
        text += f"❤️ *Расходы: -{expenses:,.0f} ₸*\n"
        for cat, amount in sorted(expense_cats.items(), key=lambda x: -x[1]):
            pct = amount / expenses * 100
            text += f"  • {cat}: {amount:,.0f} ₸ ({pct:.0f}%)\n"
        text += "\n"

    balance = income - expenses
    emoji = "📈" if balance >= 0 else "📉"
    text += f"{emoji} *Итог месяца: {'+' if balance >= 0 else ''}{balance:,.0f} ₸*\n"

    if expenses > 0 and expense_cats:
        top_cat = max(expense_cats.items(), key=lambda x: x[1])
        text += f"\n🏆 Главная статья расходов: *{top_cat[0]}* — {top_cat[1]:,.0f} ₸"

    return text
