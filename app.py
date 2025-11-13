from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
import pandas as pd
import os
from datetime import datetime, timedelta
from models import db, User, Group, Student, Supervisor, WorkType, Topic, TopicReservation
from config import Config
import random
import threading
import time

# === Создание приложения ===
app = Flask(__name__)
app.config.from_object(Config)

# === Инициализация базы ===
db.init_app(app)

# === Настройка Flask-Login ===
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# === Функции инициализации ===
def init_db():
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(username='admin').first():
            admin = User(username='admin', role='admin')
            admin.set_password('admin')
            db.session.add(admin)
            db.session.commit()


def create_test_headman():
    with app.app_context():
        # Создаем тестовую группу если ее нет
        group = Group.query.filter_by(name='ИТ-21').first()
        if not group:
            group = Group(name='ИТ-21', cmk='Информационные технологии')
            db.session.add(group)
            db.session.commit()
            print('✅ Создана тестовая группа: ИТ-21')

        # Создаем старосту
        headman = User.query.filter_by(username='headman').first()
        if not headman:
            headman = User(username='headman', role='headman', group_id=group.id)
            headman.set_password('headman')
            db.session.add(headman)
            db.session.commit()
            print('✅ Создан пользователь-староста: headman/headman')


def create_test_student():
    with app.app_context():
        # Находим группу ИТ-21
        group = Group.query.filter_by(name='ИТ-21').first()
        if not group:
            group = Group(name='ИТ-21', cmk='Информационные технологии')
            db.session.add(group)
            db.session.commit()
            print('✅ Создана тестовая группа: ИТ-21')

        # Создаем тестового студента если его нет
        student = Student.query.filter_by(full_name='Иванов Иван Иванович').first()
        if not student:
            student = Student(
                full_name='Иванов Иван Иванович',
                phone='+79991234567',
                group_id=group.id
            )
            db.session.add(student)
            db.session.commit()
            print('✅ Создан тестовый студент: Иванов Иван Иванович')

        # Создаем пользователя-студента
        student_user = User.query.filter_by(username='student').first()
        if not student_user:
            student_user = User(
                username='student',
                role='student',
                group_id=group.id,
                student_id=student.id  # Связываем с записью студента
            )
            student_user.set_password('student')
            db.session.add(student_user)
            db.session.commit()
            print('✅ Создан пользователь-студент: student/student')


def cleanup_expired_reservations():
    """Очистка просроченных резерваций"""
    with app.app_context():
        try:
            now = datetime.utcnow()
            expired_reservations = TopicReservation.query.filter(
                TopicReservation.expires_at < now
            ).all()

            for reservation in expired_reservations:
                topic = reservation.topic
                if topic.status == 'reserved':
                    topic.status = 'free'
                    topic.group_id = None
                    topic.reserved_at = None
                    topic.reserved_by = None

                db.session.delete(reservation)
                print(f"✅ Удалена просроченная резервация темы {topic.id}")

            db.session.commit()
        except Exception as e:
            print(f"❌ Ошибка при очистке резерваций: {e}")


def start_background_cleanup():
    """Запуск фоновой задачи очистки"""

    def cleanup_loop():
        while True:
            cleanup_expired_reservations()
            time.sleep(60)  # Проверка каждую минуту

    thread = threading.Thread(target=cleanup_loop)
    thread.daemon = True
    thread.start()


# === Маршруты аутентификации ===
@app.route('/')
def index():
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user)
            if user.role == 'admin':
                return redirect(url_for('admin_dashboard'))
            elif user.role == 'headman':
                return redirect(url_for('headman_dashboard'))
            elif user.role == 'student':
                return redirect(url_for('student_dashboard'))
            else:
                flash('Неизвестная роль пользователя')
        else:
            flash('Неверный логин или пароль')

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


# === Маршруты администратора ===
@app.route('/admin')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        flash('Доступ запрещен')
        return redirect(url_for('login'))

    groups = Group.query.all()
    students = Student.query.all()
    supervisors = Supervisor.query.all()
    topics = Topic.query.all()
    work_types = WorkType.query.all()

    return render_template('admin.html',
                           groups=groups,
                           students=students,
                           supervisors=supervisors,
                           topics=topics,
                           work_types=work_types)


@app.route('/admin/upload_students', methods=['POST'])
@login_required
def upload_students():
    if current_user.role != 'admin':
        return jsonify({'error': 'Доступ запрещен'}), 403

    if 'file' not in request.files:
        return jsonify({'error': 'Файл не выбран'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Файл не выбран'}), 400

    try:
        if file.filename.endswith('.csv'):
            df = pd.read_csv(file)
        else:
            df = pd.read_excel(file)

        for _, row in df.iterrows():
            group_name = row['group']
            group = Group.query.filter_by(name=group_name).first()
            if not group:
                group = Group(name=group_name, cmk=row.get('cmk', 'Общая'))
                db.session.add(group)
                db.session.commit()

            student = Student(
                full_name=row['full_name'],
                phone=row.get('phone', ''),
                group_id=group.id
            )
            db.session.add(student)

        db.session.commit()
        return jsonify({'success': 'Студенты успешно загружены'})

    except Exception as e:
        return jsonify({'error': f'Ошибка: {str(e)}'}), 500


@app.route('/admin/upload_topics', methods=['POST'])
@login_required
def upload_topics():
    if current_user.role != 'admin':
        return jsonify({'error': 'Доступ запрещен'}), 403

    if 'file' not in request.files:
        return jsonify({'error': 'Файл не выбран'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Файл не выбран'}), 400

    try:
        if file.filename.endswith('.csv'):
            df = pd.read_csv(file)
        else:
            df = pd.read_excel(file)

        for _, row in df.iterrows():
            supervisor_name = row['supervisor']
            supervisor = Supervisor.query.filter_by(full_name=supervisor_name).first()
            if not supervisor:
                supervisor = Supervisor(
                    full_name=supervisor_name,
                    subjects=row.get('subjects', '')
                )
                db.session.add(supervisor)
                db.session.commit()

            work_type_name = row['work_type']
            work_type_subject = row['subject']
            work_type = WorkType.query.filter_by(
                name=work_type_name,
                subject=work_type_subject
            ).first()
            if not work_type:
                work_type = WorkType(
                    name=work_type_name,
                    subject=work_type_subject
                )
                db.session.add(work_type)
                db.session.commit()

            topic = Topic(
                title=row['title'],
                supervisor_id=supervisor.id,
                work_type_id=work_type.id
            )
            db.session.add(topic)

        db.session.commit()
        return jsonify({'success': 'Темы успешно загружены'})

    except Exception as e:
        return jsonify({'error': f'Ошибка: {str(e)}'}), 500


@app.route('/admin/random_distribute', methods=['POST'])
@login_required
def random_distribute():
    if current_user.role != 'admin':
        return jsonify({'error': 'Доступ запрещен'}), 403

    try:
        group_id = request.json.get('group_id')
        work_type_id = request.json.get('work_type_id')

        students = Student.query.filter_by(group_id=group_id, topic_id=None).all()
        topics = Topic.query.filter_by(status='free', work_type_id=work_type_id).all()

        if len(students) > len(topics):
            return jsonify({'error': 'Недостаточно свободных тем для всех студентов'})

        random.shuffle(students)
        random.shuffle(topics)

        for i, student in enumerate(students):
            if i < len(topics):
                topics[i].status = 'assigned'
                topics[i].student_id = student.id
                topics[i].group_id = group_id

        db.session.commit()
        return jsonify({'success': f'Распределено {min(len(students), len(topics))} тем'})

    except Exception as e:
        return jsonify({'error': f'Ошибка: {str(e)}'}), 500


# === Маршруты старосты ===
@app.route('/headman')
@login_required
def headman_dashboard():
    if current_user.role == 'admin':
        return redirect(url_for('admin_dashboard'))

    group = current_user.group
    students = Student.query.filter_by(group_id=group.id).all()
    topics = Topic.query.all()

    return render_template('headman.html',
                           group=group,
                           students=students,
                           topics=topics)


@app.route('/headman/reserve_topic', methods=['POST'])
@login_required
def reserve_topic():
    if current_user.role == 'admin':
        return jsonify({'error': 'Доступ запрещен'}), 403

    try:
        topic_id = request.json.get('topic_id')

        topic = Topic.query.get(topic_id)
        if not topic:
            return jsonify({'error': 'Тема не найдена'}), 404

        if topic.status != 'free':
            return jsonify({'error': 'Тема уже занята или зарезервирована'}), 400

        # Проверяем, нет ли активной резервации
        existing_reservation = TopicReservation.query.filter_by(topic_id=topic_id).first()
        if existing_reservation:
            if existing_reservation.expires_at > datetime.utcnow():
                return jsonify({'error': 'Тема уже зарезервирована другим пользователем'}), 400
            else:
                # Удаляем просроченную резервацию
                db.session.delete(existing_reservation)

        # Создаем новую резервацию на 30 минут
        reserved_at = datetime.utcnow()
        expires_at = reserved_at + timedelta(minutes=30)

        reservation = TopicReservation(
            topic_id=topic_id,
            group_id=current_user.group.id,
            reserved_by=current_user.id,
            reserved_at=reserved_at,
            expires_at=expires_at
        )

        # Обновляем статус темы
        topic.status = 'reserved'
        topic.group_id = current_user.group.id
        topic.reserved_at = reserved_at
        topic.reserved_by = current_user.id

        db.session.add(reservation)
        db.session.commit()

        return jsonify({
            'success': 'Тема зарезервирована на 30 минут',
            'expires_at': expires_at.isoformat()
        })

    except Exception as e:
        return jsonify({'error': f'Ошибка: {str(e)}'}), 500


@app.route('/headman/get_reservations')
@login_required
def get_reservations():
    """Получить активные резервации пользователя"""
    if current_user.role == 'admin':
        return jsonify({'error': 'Доступ запрещен'}), 403

    try:
        reservations = TopicReservation.query.filter_by(
            reserved_by=current_user.id
        ).filter(
            TopicReservation.expires_at > datetime.utcnow()
        ).all()

        result = []
        for reservation in reservations:
            result.append({
                'topic_id': reservation.topic_id,
                'topic_title': reservation.topic.title[:50] + '...' if len(
                    reservation.topic.title) > 50 else reservation.topic.title,
                'reserved_at': reservation.reserved_at.isoformat(),
                'expires_at': reservation.expires_at.isoformat(),
                'minutes_left': int((reservation.expires_at - datetime.utcnow()).total_seconds() / 60)
            })

        return jsonify({'reservations': result})

    except Exception as e:
        return jsonify({'error': f'Ошибка: {str(e)}'}), 500


@app.route('/headman/cancel_reservation', methods=['POST'])
@login_required
def cancel_reservation():
    """Отменить резервацию"""
    if current_user.role == 'admin':
        return jsonify({'error': 'Доступ запрещен'}), 403

    try:
        topic_id = request.json.get('topic_id')

        reservation = TopicReservation.query.filter_by(
            topic_id=topic_id,
            reserved_by=current_user.id
        ).first()

        if not reservation:
            return jsonify({'error': 'Резервация не найдена'}), 404

        topic = reservation.topic
        topic.status = 'free'
        topic.group_id = None
        topic.reserved_at = None
        topic.reserved_by = None

        db.session.delete(reservation)
        db.session.commit()

        return jsonify({'success': 'Резервация отменена'})

    except Exception as e:
        return jsonify({'error': f'Ошибка: {str(e)}'}), 500


@app.route('/headman/assign_topic', methods=['POST'])
@login_required
def assign_topic():
    if current_user.role == 'admin':
        return jsonify({'error': 'Доступ запрещен'}), 403

    try:
        data = request.json
        topic_id = data.get('topic_id')
        student_id = data.get('student_id')

        topic = Topic.query.get(topic_id)
        student = Student.query.get(student_id)

        if not topic or not student:
            return jsonify({'error': 'Тема или студент не найдены'}), 404

        # Проверяем резервацию
        reservation = TopicReservation.query.filter_by(
            topic_id=topic_id,
            reserved_by=current_user.id
        ).first()

        if not reservation:
            return jsonify({'error': 'Тема не зарезервирована вами'}), 400

        if reservation.expires_at < datetime.utcnow():
            return jsonify({'error': 'Время резервации истекло'}), 400

        if topic.status == 'assigned':
            return jsonify({'error': 'Тема уже назначена'}), 400

        if student.topic_id is not None:
            return jsonify({'error': 'Студент уже имеет тему'}), 400

        # Назначаем тему
        topic.status = 'assigned'
        topic.student_id = student.id
        topic.group_id = current_user.group.id

        # Удаляем резервацию
        db.session.delete(reservation)

        db.session.commit()
        return jsonify({'success': 'Тема успешно назначена'})

    except Exception as e:
        return jsonify({'error': f'Ошибка: {str(e)}'}), 500


# === Маршруты студента ===
@app.route('/student')
@login_required
def student_dashboard():
    if current_user.role not in ['student', 'admin']:
        flash('Доступ запрещен')
        return redirect(url_for('login'))

    # Получаем данные студента
    student = None
    if current_user.role == 'student' and current_user.student_id:
        student = Student.query.get(current_user.student_id)
    elif current_user.role == 'admin':
        # Админ может просматривать любого студента (для тестирования)
        student = Student.query.first()

    if not student:
        flash('Данные студента не найдены')
        return redirect(url_for('login'))

    # Получаем тему студента если есть
    topic = None
    if student.topic_id:
        topic = Topic.query.get(student.topic_id)

    return render_template('student.html',
                           student=student,
                           topic=topic)


# === Главная страница ===
@app.route('/home')
def home():
    return redirect(url_for('login'))


# === Инициализация и запуск ===
if __name__ == '__main__':
    init_db()
    create_test_headman()
    create_test_student()
    start_background_cleanup()
    print("✅ Сервер запущен с системой резерваций и входом для студентов")
    print("✅ Доступен по адресу: http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)
