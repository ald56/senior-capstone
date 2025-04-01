from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Change this to a strong secret key
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///school_volunteer.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# -----------------------------
# Database Models
# -----------------------------
class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    school_id = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    points = db.Column(db.Integer, default=0)

class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    max_participants = db.Column(db.Integer, nullable=False)
    current_participants = db.Column(db.Integer, default=0)

class Reward(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    points_required = db.Column(db.Integer, nullable=False)

class EventSignup(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)

# Instead of using @app.before_first_request, create tables once at startup:
with app.app_context():
    db.create_all()

# -----------------------------
# Routes for Student Users
# -----------------------------
@app.route('/')
def home():
    return render_template('welcome.html')  # ✅ This will show the welcome page


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form['name']
        school_id = request.form['school_id']
        password = request.form['password']
        if Student.query.filter_by(school_id=school_id).first():
            flash('School ID already registered.')
            return redirect(url_for('signup'))
        hashed_password = generate_password_hash(password)
        new_student = Student(name=name, school_id=school_id, password=hashed_password)
        db.session.add(new_student)
        db.session.commit()
        flash('Signup successful! Please log in.')
        return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        school_id = request.form['school_id']
        password = request.form['password']
        student = Student.query.filter_by(school_id=school_id).first()
        if student and check_password_hash(student.password, password):
            session['student_id'] = student.id
            flash('Login successful.')
            return redirect(url_for('portal'))  # Redirect to portal after login
        else:
            flash('Invalid School ID or password.')
    return render_template('login.html')  # Render login page


@app.route('/logout')
def logout():
    session.pop('student_id', None)
    flash('Logged out.')
    return redirect(url_for('login'))

@app.route('/portal')
def portal():
    if 'student_id' not in session:
        return redirect(url_for('login'))
    student = Student.query.get(session['student_id'])
    return render_template('portal.html', points=student.points)  # Show points on portal

@app.route('/events', methods=['GET', 'POST'])
def events():
    if 'student_id' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        event_id = request.form['event_id']
        event = Event.query.get(event_id)
        if event and event.current_participants < event.max_participants:
            new_signup = EventSignup(event_id=event_id, student_id=session['student_id'])
            event.current_participants += 1
            db.session.add(new_signup)
            db.session.commit()
            flash(f"Signed up for {event.name}!")
        else:
            flash("Event is full or does not exist.")
    events = Event.query.all()
    return render_template('events.html', events=events)

@app.route('/rewards', methods=['GET', 'POST'])
def rewards():
    if 'student_id' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        reward_id = request.form['reward_id']
        student = Student.query.get(session['student_id'])
        reward = Reward.query.get(reward_id)
        if student and reward and student.points >= reward.points_required:
            student.points -= reward.points_required
            db.session.commit()
            flash(f"Redeemed reward: {reward.name}!")
        else:
            flash("Not enough points to redeem this reward.")
    rewards = Reward.query.all()
    return render_template('rewards.html', rewards=rewards)

# -----------------------------
# Routes for Manager Users
# -----------------------------
@app.route('/manager-login', methods=['GET', 'POST'])
def manager_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        # Hardcoded credentials for demonstration:
        if username == 'admin' and password == 'adminpass':
            session['manager'] = True
            flash("Manager login successful.")
            return redirect(url_for('manager_page'))
        else:
            flash("Invalid manager credentials.")
    return render_template('manager_login.html')

@app.route('/manager', methods=['GET', 'POST'])
def manager_page():
    if 'manager' not in session:
        return redirect(url_for('manager_login'))
    if request.method == 'POST':
        # Check which form was submitted:
        if 'event_name' in request.form:
            event_name = request.form['event_name']
            max_participants = request.form['max_participants']
            new_event = Event(name=event_name, max_participants=int(max_participants))
            db.session.add(new_event)
            db.session.commit()
            flash("Event added successfully.")
        elif 'reward_name' in request.form:
            reward_name = request.form['reward_name']
            points_required = request.form['points_required']
            new_reward = Reward(name=reward_name, points_required=int(points_required))
            db.session.add(new_reward)
            db.session.commit()
            flash("Reward added successfully.")
    events = Event.query.all()
    rewards = Reward.query.all()
    return render_template('manager_page.html', events=events, rewards=rewards)

@app.route('/manager-logout')
def manager_logout():
    session.pop('manager', None)
    flash("Manager logged out.")
    return redirect(url_for('manager_login'))

if __name__ == '__main__':
    app.run(debug=True)
