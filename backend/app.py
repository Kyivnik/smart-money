# backend/app.py (оновлена частина)
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, Transaction
from ml_model import (analyze_user_data, create_interactive_financial_chart,
                      predict_next_month_balance, create_category_pie_chart)
from flask_migrate import Migrate
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'  # Замініть на свій безпечний ключ
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///smart_money.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
migrate = Migrate(app, db)

login_manager = LoginManager(app)
login_manager.login_view = 'login'


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route('/')
def index():
    return redirect(url_for('login'))


# Реєстрація та логін залишаються без змін
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username').strip()
        password = request.form.get('password').strip()

        if not username or not password:
            flash("Будь ласка, заповніть усі поля.")
            return redirect(url_for('register'))

        if User.query.filter_by(username=username).first():
            flash("Користувач із таким ім'ям вже існує.")
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password, method='pbkdf2:sha256', salt_length=8)
        new_user = User(username=username, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()

        flash("Реєстрація пройшла успішно! Тепер увійдіть у свій акаунт.")
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username').strip()
        password = request.form.get('password').strip()

        user = User.query.filter_by(username=username).first()
        if not user or not check_password_hash(user.password, password):
            flash("Невірне ім'я користувача або пароль.")
            return redirect(url_for('login'))

        login_user(user)
        return redirect(url_for('dashboard'))

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


# Головна панель
@app.route('/dashboard')
@login_required
def dashboard():
    transactions = Transaction.query.filter_by(user_id=current_user.id).order_by(Transaction.created_at.desc()).all()
    suggestions = analyze_user_data(transactions)
    interactive_chart = create_interactive_financial_chart(transactions)
    next_balance = predict_next_month_balance(transactions)
    category_chart = create_category_pie_chart(transactions)
    return render_template('dashboard.html',
                           transactions=transactions,
                           suggestions=suggestions,
                           interactive_chart=interactive_chart,
                           next_balance=next_balance,
                           category_chart=category_chart)


@app.route('/transaction', methods=['POST'])
@login_required
def add_transaction():
    t_type = request.form.get('type')
    amount = request.form.get('amount')
    description = request.form.get('description', '')
    category = request.form.get('category', '')

    try:
        amount = float(amount)
    except ValueError:
        flash("Неправильний формат суми.")
        return redirect(url_for('dashboard'))

    transaction = Transaction(
        type=t_type,
        amount=amount,
        description=description,
        category=category,
        user_id=current_user.id
    )
    db.session.add(transaction)
    db.session.commit()

    flash("Транзакцію додано успішно!")
    return redirect(url_for('dashboard'))


# Маршрут для редагування транзакції
@app.route('/transaction/edit/<int:trans_id>', methods=['GET', 'POST'])
@login_required
def edit_transaction(trans_id):
    transaction = Transaction.query.get_or_404(trans_id)
    if transaction.user_id != current_user.id:
        flash("Немає прав доступу.")
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        try:
            transaction.amount = float(request.form.get('amount'))
        except ValueError:
            flash("Невірний формат суми.")
            return redirect(url_for('edit_transaction', trans_id=trans_id))
        transaction.description = request.form.get('description', transaction.description)
        transaction.category = request.form.get('category', transaction.category)
        created_at_str = request.form.get('created_at')
        try:
            # Очікуємо формат "YYYY-MM-DD HH:MM"
            transaction.created_at = datetime.strptime(created_at_str, '%Y-%m-%d %H:%M')
        except Exception:
            flash("Невірний формат дати. Використовуйте формат 'YYYY-MM-DD HH:MM'")
            return redirect(url_for('edit_transaction', trans_id=trans_id))
        db.session.commit()
        flash("Транзакцію оновлено.")
        return redirect(url_for('dashboard'))
    return render_template('edit_transaction.html', transaction=transaction)


# Маршрут для видалення транзакції
@app.route('/transaction/delete/<int:trans_id>', methods=['POST'])
@login_required
def delete_transaction(trans_id):
    transaction = Transaction.query.get_or_404(trans_id)
    if transaction.user_id != current_user.id:
        flash("Немає прав доступу.")
        return redirect(url_for('dashboard'))
    db.session.delete(transaction)
    db.session.commit()
    flash("Транзакцію видалено.")
    return redirect(url_for('dashboard'))


@app.route('/api/transaction/<int:trans_id>', methods=['PUT', 'DELETE'])
@login_required
def modify_transaction(trans_id):
    transaction = Transaction.query.get_or_404(trans_id)
    if transaction.user_id != current_user.id:
        return jsonify({'error': 'Немає прав доступу.'}), 403

    if request.method == 'PUT':
        data = request.json
        transaction.type = data.get('type', transaction.type)
        try:
            transaction.amount = float(data.get('amount', transaction.amount))
        except ValueError:
            return jsonify({'error': 'Невірний формат суми.'}), 400
        transaction.description = data.get('description', transaction.description)
        transaction.category = data.get('category', transaction.category)
        db.session.commit()
        return jsonify({'message': 'Транзакцію оновлено.'})

    if request.method == 'DELETE':
        db.session.delete(transaction)
        db.session.commit()
        return jsonify({'message': 'Транзакцію видалено.'})


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
