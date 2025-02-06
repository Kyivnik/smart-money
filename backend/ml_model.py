# backend/ml_model.py
import numpy as np
import matplotlib.pyplot as plt
import io, base64
import pandas as pd
from sklearn.linear_model import LinearRegression, LogisticRegression

# Для інтерактивних графіків Plotly
import plotly.express as px
import plotly.io as pio


def analyze_user_data(transactions):
    """
    Аналіз бюджетних даних для видачі рекомендацій.
    """
    total_income = sum(t.amount for t in transactions if t.type == 'income')
    total_expense = sum(t.amount for t in transactions if t.type == 'expense')

    # Проста логістична регресія як приклад
    X_train = np.array([
        [5000, 3000],
        [6000, 4000],
        [7000, 3500],
        [3000, 3500],
        [4000, 4500],
        [8000, 6000]
    ])
    y_train = np.array([1, 1, 1, 0, 0, 1])
    model = LogisticRegression()
    model.fit(X_train, y_train)

    X_input = np.array([[total_income, total_expense]])
    prediction = model.predict(X_input)[0]

    suggestions = []
    if prediction == 1:
        suggestions.append("Ваш бюджет збалансований. Продовжуйте в тому ж дусі!")
    else:
        suggestions.append("Витрати перевищують доходи. Розгляньте можливість зменшення витрат або збільшення доходів.")

    if total_income > 0:
        expense_ratio = total_expense / total_income
        if expense_ratio > 0.8:
            suggestions.append("Ви витрачаєте більше 80% свого доходу. Варто переглянути свої витрати.")
        elif expense_ratio < 0.5:
            suggestions.append("У вас хороший баланс витрат та доходів. Продовжуйте планувати бюджет.")
    else:
        suggestions.append("Немає даних про доходи. Будь ласка, додайте транзакції.")

    return suggestions


def create_interactive_financial_chart(transactions):
    """
    Будує інтерактивний графік місячного фінансового тренду за допомогою Plotly.
    Повертає HTML‑код, який можна вбудувати в шаблон.
    """
    if not transactions:
        return None

    data = {
        'date': [t.created_at for t in transactions],
        'amount': [t.amount if t.type == 'income' else -t.amount for t in transactions]
    }
    df = pd.DataFrame(data)
    df['date'] = pd.to_datetime(df['date'])
    df['month'] = df['date'].dt.to_period('M').astype(str)
    monthly = df.groupby('month')['amount'].sum().reset_index()

    fig = px.line(monthly, x='month', y='amount', markers=True,
                  title="Інтерактивний фінансовий тренд",
                  labels={'month': 'Місяць', 'amount': 'Баланс'})
    fig.update_layout(xaxis_tickangle=-45)
    # Повертаємо HTML-код графіку (вбудований div)
    return pio.to_html(fig, full_html=False, include_plotlyjs='cdn')


def predict_next_month_balance(transactions):
    """
    Прогнозує баланс наступного місяця за допомогою лінійної регресії.
    """
    if not transactions:
        return None

    data = {
        'date': [t.created_at for t in transactions],
        'balance': [t.amount if t.type == 'income' else -t.amount for t in transactions]
    }
    df = pd.DataFrame(data)
    df['date'] = pd.to_datetime(df['date'])
    df['month'] = df['date'].dt.to_period('M')
    monthly = df.groupby('month')['balance'].sum().reset_index()
    if len(monthly) < 2:
        return None

    monthly['month_num'] = range(1, len(monthly) + 1)
    X = monthly[['month_num']]
    y = monthly['balance']
    model = LinearRegression()
    model.fit(X, y)

    next_month = np.array([[len(monthly) + 1]])
    prediction = model.predict(next_month)[0]
    return prediction


def create_category_pie_chart(transactions):
    """
    Будує кругову діаграму розподілу витрат за категоріями.
    Повертає зображення у форматі base64.
    """
    # Фільтруємо лише витрати
    expenses = [t for t in transactions if t.type == 'expense']
    if not expenses:
        return None

    data = {
        'category': [t.category if t.category else "Інше" for t in expenses],
        'amount': [t.amount for t in expenses]
    }
    df = pd.DataFrame(data)
    grouped = df.groupby('category')['amount'].sum().reset_index()

    fig, ax = plt.subplots(figsize=(6, 6))
    ax.pie(grouped['amount'], labels=grouped['category'], autopct='%1.1f%%', startangle=90)
    ax.set_title("Розподіл витрат за категоріями")
    ax.axis('equal')

    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    buf.seek(0)
    image_base64 = base64.b64encode(buf.read()).decode('utf-8')
    plt.close(fig)
    return image_base64
