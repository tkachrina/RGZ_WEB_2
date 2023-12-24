from flask import Flask, session, render_template, redirect, request, url_for, flash
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime
from Db import db
from Db.models import users, cinema_sessions
from flask_migrate import Migrate


app = Flask(__name__)


app.secret_key = 'smell'  # Ключ для сессий
user_db = "tkach"
host_ip = "127.0.0.1"
host_port = "5432"
database_name = "cinema"
password = "stink"


app.config['SQLALCHEMY_DATABASE_URI'] = f'postgresql://{user_db}:{password}@{host_ip}:{host_port}/{database_name}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

migrate = Migrate(app, db)

db.init_app(app)


@app.route('/')
def start():
    return redirect(url_for('main'))


@app.route("/app/index", methods=['GET', 'POST'])
def main():
    db.create_all()
    if 'name' not in session:
        return redirect(url_for('registerPage'))

    all_users = users.query.all()

    visible_user = session.get('name', 'Anon')

    return render_template('index.html', name=visible_user, all_users=all_users)


@app.route('/app/register', methods=['GET', 'POST'])
def registerPage():
    errors = []

    if request.method == 'GET':
        return render_template("register.html", errors=errors)

    name = request.form.get('name')
    username = request.form.get("username")
    password = request.form.get("password")

    if not (username or password):
        errors.append("Пожалуйста, заполните все поля")
        print(errors)
        return render_template("register.html", errors=errors)
    elif not name:
        errors.append("Пожалуйста, заполните все поля")
        print(errors)
        return render_template("register.html", errors=errors)

    existing_user = users.query.filter_by(username=username).first()

    if existing_user:
        errors.append('Пользователь с данным именем уже существует')
        return render_template('register.html', errors=errors, resultСur=existing_user)

    hashed_password = generate_password_hash(password)

    new_user = users(username=username, password=hashed_password, name=name)
    db.session.add(new_user)
    db.session.commit()

    return redirect("/app/login")


@app.route('/app/login', methods=["GET", "POST"])
def loginPage():
    errors = []

    if request.method == 'GET':
        return render_template("login.html", errors=errors)

    name = request.form.get("name")
    username = request.form.get("username")
    password = request.form.get("password")

    if not (username or password or name):
        errors.append("Пожалуйста, заполните все поля")
        return render_template("login.html", errors=errors)

    user = users.query.filter_by(username=username).first()

    if user is None or not check_password_hash(user.password, password):
        errors.append('Неправильный пользователь или пароль')
        return render_template("login.html", errors=errors)

    session['name'] = user.name
    session['id'] = user.id
    session['username'] = user.username

    return redirect("index")


@app.route("/app/new_session", methods=["GET", "POST"])
def createSession():
    errors = []
    username = session.get('username')

    if username == 'admin':
        if request.method == 'POST':
            movie = request.form.get('movie')
            start_time = request.form.get('date')
            room_number = request.form.get('room_number')

            if start_time:
                try:
                    # Преобразовываем строку в объект datetime
                    time = datetime.strptime(start_time, "%d-%m-%Y %H:%M")
                except:
                    errors.append('Некорректный формат времени')
                    return render_template('new_session.html', errors=errors)

                new_session = cinema_sessions(movie=movie, room_number=room_number, start_time=time)
                db.session.add(new_session)
                db.session.commit()

                session_id = new_session.session_id

                flash('Сеанс успешно создан', 'success')
                return redirect(url_for('allFilms'), cinema_session_id=session_id)

    return render_template('new_session.html', errors=errors)


@app.route("/app/all_sessions", methods=["GET", "POST"])
def allFilms():
    movie_sessions = db.session.query(cinema_sessions.movie).distinct().all()

    return render_template("allFilms.html", movie_sessions=movie_sessions)


@app.route("/app/movieSessions/<movie>")
def movie_sessions(movie):
    sessions = cinema_sessions.query.filter_by(movie=movie).all()

    return render_template("movieSessions.html", movie=movie, sessions=sessions)


@app.route('/app/session/<int:cinema_session_id>')
def session_details(cinema_session_id):
    session_data = cinema_sessions.query.get(cinema_session_id)

    if not session_data:
        # Обработка случая, если сеанс с указанным ID не найден
        return render_template("movieSessions.html")

    # Создадим список кортежей, содержащих номер места и его статус
    seats = [(f'seat_{i}', getattr(session_data, f'seat_{i}')) for i in range(1, 31)]

    # Получим список занимающих мест людей
    occupants = [getattr(session_data, f'occupant_{i}') for i in range(1, 31)]

    return render_template('sessionDetails.html', session_data=session_data, seats=seats, occupants=occupants)


@app.route('/app/session/<int:cinema_session_id>/reserve', methods=['POST'])
def reserve_seats(cinema_session_id):
    if 'name' not in session:
        flash('Необходимо войти в систему для резервации мест', 'error')
        return redirect(url_for('loginPage'))

    selected_seats = request.form.getlist('selected_seats')

    if not selected_seats:
        flash('Выберите места для резервации', 'error')
        return redirect(url_for('session_details', cinema_session_id=cinema_session_id))

    session_data = cinema_sessions.query.get(cinema_session_id)

    if not session_data:
        flash('Сеанс с указанным ID не найден', 'error')
        return redirect(url_for('allFilms'))

    for selected_seat in selected_seats:
        seat_number = int(selected_seat.split('_')[-1])
        if getattr(session_data, selected_seat, False):
            flash(f'Место {selected_seat} уже занято', 'error')
        else:
            setattr(session_data, selected_seat, True)
            setattr(session_data, f'occupant_{seat_number}', session['name'])
            db.session.commit()
            flash(f'Место {selected_seat} успешно зарезервировано', 'success')

    return redirect(url_for('session_details', cinema_session_id=cinema_session_id))

