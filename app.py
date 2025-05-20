from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_migrate import Migrate
from datetime import datetime, date, time
import re

from flask_mail import Mail, Message



app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Change this to a strong secret key
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///school_volunteer.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

migrate = Migrate(app, db)

# Configure mail server
from flask_mail import Mail, Message

app.config['MAIL_SERVER'] = 'smtp.sendgrid.net'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'apikey'  # This is literal, not your username
app.config['MAIL_PASSWORD'] = "Key removed for security"  # Paste your key here
app.config['MAIL_DEFAULT_SENDER'] = 'milesbrown1102@gmail.com'
mail = Mail(app)


mail = Mail(app)
# -----------------------------
# Database Models
# -----------------------------
class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    school_id = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(150), nullable=True)
    password = db.Column(db.String(200), nullable=False)
    avatar = db.Column(db.String(100), nullable=True)
    notification_opt_in = db.Column(db.Boolean, default=False)
    points = db.Column(db.Integer, default=0)



class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    max_participants = db.Column(db.Integer, nullable=False)
    current_participants = db.Column(db.Integer, default=0)
    date = db.Column(db.Date, nullable=True)
    start_time = db.Column(db.Time, nullable=True)
    end_time = db.Column(db.Time, nullable=True)
    points = db.Column(db.Integer, default=0)
    location = db.Column(db.String(200), nullable=True)  # NEW
    notes = db.Column(db.Text, nullable=True)



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
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        school_id = request.form['school_id']
        password = request.form['password']
        email = request.form.get('email')
        notification_opt_in = 'notification_opt_in' in request.form

        # Validate school ID (must be 7 digits)
        if not re.fullmatch(r"\d{7}", school_id):
            flash("School ID must be exactly 7 digits.")
            return redirect(url_for('signup'))

        # Validate strong password
        if len(password) < 8 or not re.search(r"[A-Z]", password) or not re.search(r"[\W_]", password):
            flash("Password must be at least 8 characters long, contain at least one uppercase letter and one special character.")
            return redirect(url_for('signup'))

        # Check if School ID already exists
        if Student.query.filter_by(school_id=school_id).first():
            flash('School ID already registered.')
            return redirect(url_for('signup'))

        hashed_password = generate_password_hash(password)
        new_student = Student(
            first_name=first_name,
            last_name=last_name,
            school_id=school_id,
            password=hashed_password,
            email=email,
            notification_opt_in=notification_opt_in
        )
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
    return render_template('portal.html', student=student, points=student.points)



from flask_mail import Message  # Ensure this is imported at the top

@app.route('/events', methods=['GET', 'POST'])
def events():
    if 'student_id' not in session:
        flash("You must be logged in as a student to view events.")
        return redirect(url_for('login'))

    student = Student.query.get(session['student_id'])

    if request.method == 'POST':
        event_id = request.form.get('event_id')
        event = Event.query.get(event_id)

        # Prevent duplicate signups
        already_signed_up = EventSignup.query.filter_by(
            event_id=event_id,
            student_id=student.id
        ).first()

        if already_signed_up:
            flash("You are already signed up for this event.")
        elif event and event.current_participants < event.max_participants:
            signup = EventSignup(event_id=event_id, student_id=student.id)
            event.current_participants += 1
            db.session.add(signup)
            db.session.commit()
            flash(f"Successfully signed up for {event.name}.")

            # Send email if student opted in and email exists
            if student.email and student.notification_opt_in:
                try:
                    msg = Message(
                    subject="Event Signup Confirmation",
                    sender="Bowie Volunteer Portal <milesbrown1102@gmail.com>",
                    recipients=[student.email],
                    body=f"""Hello {student.first_name},

You’ve signed up for:

Event: {event.name}
Date: {event.date.strftime('%Y-%m-%d') if event.date else 'TBD'}
Time: {event.start_time.strftime('%I:%M %p') if event.start_time else ''} - {event.end_time.strftime('%I:%M %p') if event.end_time else ''}
Location: {event.location or 'TBD'}

Thanks for volunteering!
- Bowie Volunteer Portal
                        """
                    )
                    mail.send(msg)
                except Exception as e:
                    print(f"Email send failed: {e}")
        else:
            flash("Event is full or not found.")

    # Sorting logic
    sort_by = request.args.get('sort')
    if sort_by == 'date_asc':
        events = Event.query.order_by(Event.date.asc()).all()
    elif sort_by == 'date_desc':
        events = Event.query.order_by(Event.date.desc()).all()
    elif sort_by == 'points_asc':
        events = Event.query.order_by(Event.points.asc()).all()
    elif sort_by == 'points_desc':
        events = Event.query.order_by(Event.points.desc()).all()
    elif sort_by == 'name_asc':
        events = Event.query.order_by(Event.name.asc()).all()
    elif sort_by == 'name_desc':
        events = Event.query.order_by(Event.name.desc()).all()
    else:
        events = Event.query.all()

    return render_template('events.html', events=events)





@app.route('/rewards', methods=['GET', 'POST'])
def rewards():
    if 'student_id' not in session:
        flash("You must be logged in as a student to view rewards.")
        return redirect(url_for('login'))

    student = Student.query.get(session['student_id'])

    if request.method == 'POST':
        reward_id = request.form.get('reward_id')
        reward = Reward.query.get(reward_id)

        if reward and student.points >= reward.points_required:
            student.points -= reward.points_required
            db.session.commit()
            flash(f"You redeemed {reward.name}!")

            # ✅ Send email AFTER commit
            if student.email and student.notification_opt_in:
                try:
                    msg = Message(
                        subject="Reward Redeemed Successfully",
                        sender=app.config['MAIL_DEFAULT_SENDER'],
                        recipients=[student.email],
                        body=f"""Hi {student.first_name},

You just redeemed the reward: {reward.name}
Points Used: {reward.points_required}
Remaining Points: {student.points}

Thank you for your continued service!
- Bowie Volunteer Portal"""
                    )
                    mail.send(msg)
                    print("✅ Reward email sent")
                except Exception as e:
                    print(f"❌ Reward email failed: {e}")
        else:
            flash("Not enough points to redeem this reward.")

    # Sorting logic
    sort_by = request.args.get('sort')
    if sort_by == 'points_asc':
        rewards = Reward.query.order_by(Reward.points_required.asc()).all()
    elif sort_by == 'points_desc':
        rewards = Reward.query.order_by(Reward.points_required.desc()).all()
    elif sort_by == 'name_asc':
        rewards = Reward.query.order_by(Reward.name.asc()).all()
    elif sort_by == 'name_desc':
        rewards = Reward.query.order_by(Reward.name.desc()).all()
    else:
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
        if 'event_name' in request.form:
            # Process event data
            event_name = request.form['event_name']
            max_participants = int(request.form['max_participants'])
            event_date = request.form.get('event_date')
            start_time = request.form.get('start_time')
            end_time = request.form.get('end_time')
            points = int(request.form.get('points'))
            location = request.form.get('location') or None

            from datetime import datetime
            event_date = datetime.strptime(event_date, '%Y-%m-%d').date()
            start_time = datetime.strptime(start_time, '%H:%M').time()
            end_time = datetime.strptime(end_time, '%H:%M').time()

            new_event = Event(
                name=event_name,
                max_participants=max_participants,
                date=event_date,
                start_time=start_time,
                end_time=end_time,
                points=points,
                location=location
            )
            db.session.add(new_event)
            db.session.commit()
            flash("Event added successfully.")

            # Email all opted-in students
            opted_in_students = Student.query.filter_by(notification_opt_in=True).all()
            for student in opted_in_students:
                if student.email:
                    try:
                        msg = Message(
                            subject="🎉 New Volunteer Event Just Posted!",
                            sender=app.config['MAIL_DEFAULT_SENDER'],
                            recipients=[student.email],
                            body=f"""Hey {student.first_name},

A new volunteer opportunity is now available:

📌 Event: {event_name}
📅 Date: {event_date.strftime('%Y-%m-%d')}
🕒 Time: {start_time.strftime('%I:%M %p')} - {end_time.strftime('%I:%M %p')}
📍 Location: {location or 'TBD'}
💰 Points: {points}

Log in to your dashboard and sign up before spots fill up!

- Bowie Volunteer Portal
                            """
                        )
                        mail.send(msg)
                    except Exception as e:
                        print(f"Failed to send event email: {e}")

        elif 'reward_name' in request.form:
            reward_name = request.form['reward_name']
            points_required = int(request.form['points_required'])

            new_reward = Reward(name=reward_name, points_required=points_required)
            db.session.add(new_reward)
            db.session.commit()
            flash("Reward added successfully.")

            # Email all opted-in students
            opted_in_students = Student.query.filter_by(notification_opt_in=True).all()
            for student in opted_in_students:
                if student.email:
                    try:
                        msg = Message(
                            subject="🛍️ New Reward Added - Grab it While It Lasts!",
                            sender=app.config['MAIL_DEFAULT_SENDER'],
                            recipients=[student.email],
                            body=f"""Hi {student.first_name},

A new reward is available in the Bowie Volunteer Portal:

🏆 Reward: {reward_name}
🔑 Points Needed: {points_required}

Don't miss your chance—volunteer, earn points, and claim this reward before it's gone!

- Bowie Volunteer Portal
                            """
                        )
                        mail.send(msg)
                    except Exception as e:
                        print(f"Failed to send reward email: {e}")

    events = Event.query.all()
    rewards = Reward.query.all()
    return render_template('manager_page.html', events=events, rewards=rewards)


@app.route('/manager-logout')
def manager_logout():
    session.pop('manager', None)
    flash("Manager logged out.")
    return redirect(url_for('home'))  # Sends them to the welcome page

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'student_id' not in session:
        return redirect(url_for('login'))

    student = Student.query.get(session['student_id'])
    avatars = ['bear.png', 'cat.png', 'chick.png', 'gorilla.png', 'panda.png', 'laugh.png']

    if request.method == 'POST':
        selected_avatar = request.form.get('avatar')
        if selected_avatar in avatars:
            student.avatar = selected_avatar
            db.session.commit()
            flash('Avatar updated successfully!')
        return redirect(url_for('portal'))  # ✅ Redirect after save

    return render_template('profile.html', student=student, avatars=avatars)

@app.context_processor
def inject_student():
    if 'student_id' in session:
        student = Student.query.get(session['student_id'])
        return dict(student=student)
    return dict(student=None)

from datetime import datetime

@app.route('/edit-event/<int:event_id>', methods=['GET', 'POST'])
def edit_event(event_id):
    if 'manager' not in session:
        return redirect(url_for('manager_login'))

    event = Event.query.get_or_404(event_id)

    if request.method == 'POST':
        event.name = request.form['event_name']
        event.max_participants = int(request.form['max_participants'])
        event.date = datetime.strptime(request.form['event_date'], '%Y-%m-%d').date()
        event.start_time = datetime.strptime(request.form['start_time'], '%H:%M:%S').time()
        event.end_time = datetime.strptime(request.form['end_time'], '%H:%M:%S').time()
        event.points = int(request.form['points'])
        event.notes = request.form.get('notes')

        db.session.commit()
        flash("Event updated successfully.")
        return redirect(url_for('manager_page'))

    return render_template('edit_event.html', event=event)


@app.route('/delete-event/<int:event_id>', methods=['POST'])
def delete_event(event_id):
    if 'manager' not in session:
        return redirect(url_for('manager_login'))
    event = Event.query.get_or_404(event_id)
    db.session.delete(event)
    db.session.commit()
    flash("Event deleted.")
    return redirect(url_for('manager_page'))
@app.route('/view-signups/<int:event_id>')
def view_signups(event_id):
    if 'manager' not in session:
        return redirect(url_for('manager_login'))

    event = Event.query.get_or_404(event_id)
    signups = EventSignup.query.filter_by(event_id=event.id).all()
    students = [Student.query.get(signup.student_id) for signup in signups]

    return render_template('view_signups.html', event=event, students=students)

@app.route('/manager/students', methods=['GET', 'POST'])
def manage_students():
    if 'manager' not in session:
        return redirect(url_for('manager_login'))

    students = Student.query.all()

    if request.method == 'POST':
        student_id = request.form['student_id']
        points = int(request.form['points'])
        student = Student.query.get(student_id)
        if student:
            student.points += points
            db.session.commit()
            flash(f"{student.first_name} {student.last_name} awarded {points} points.")

    return render_template('manage_students.html', students=students)
@app.route('/view-students')
def view_students():
    if 'manager' not in session:
        return redirect(url_for('manager_login'))

    students = Student.query.all()
    all_signups = EventSignup.query.all()
    events = {event.id: event.name for event in Event.query.all()}
    rewards = Reward.query.all()

    student_data = []
    for s in students:
        signups = [events[signup.event_id] for signup in all_signups if signup.student_id == s.id]
        student_data.append({
            'id': s.id,
            'name': f"{s.first_name} {s.last_name}",
            'points': s.points,
            'events': signups,
            'school_id': s.school_id
        })

    return render_template('view_students.html', students=student_data)

@app.route('/student/<int:student_id>', methods=['GET', 'POST'])
def student_detail(student_id):
    if 'manager' not in session:
        return redirect(url_for('manager_login'))

    student = Student.query.get_or_404(student_id)

    if request.method == 'POST':
        try:
            points_to_add = int(request.form.get('points_to_add'))
            student.points += points_to_add
            db.session.commit()
            flash(f"Successfully added {points_to_add} points to {student.first_name} {student.last_name}.")

            # ✅ Send email after successful update
            if student.email and student.notification_opt_in:
                try:
                    msg = Message(
                        subject="You've Received Volunteer Points!",
                        sender=app.config['MAIL_DEFAULT_SENDER'],
                        recipients=[student.email],
                        body=f"""Hi {student.first_name},

You just received {points_to_add} volunteer points!
New Total: {student.points}

Keep up the great work!
- Bowie Volunteer Portal"""
                    )
                    mail.send(msg)
                    print("✅ Points email sent")
                except Exception as e:
                    print(f"❌ Points email failed: {e}")
        except ValueError:
            flash("Invalid input. Please enter a number.")

        return redirect(url_for('student_detail', student_id=student_id))

    signups = EventSignup.query.filter_by(student_id=student.id).all()
    event_names = [Event.query.get(s.event_id).name for s in signups]
    rewards_redeemed = []  # Optional future logic

    return render_template('student_detail.html', student=student, events=event_names, rewards=rewards_redeemed)

@app.route('/assign-points', methods=['GET', 'POST'])
def assign_points():
    if 'manager' not in session:
        return redirect(url_for('manager_login'))

    students = Student.query.order_by(Student.last_name.asc()).all()

    if request.method == 'POST':
        student_id = request.form.get('student_id')
        points_to_add = int(request.form.get('points'))
        student = Student.query.get(student_id)

        if student:
            student.points += points_to_add
            db.session.commit()
            flash(f"{points_to_add} points assigned to {student.first_name} {student.last_name}.")

            # Email notification
            if student.email and student.notification_opt_in:
                try:
                    msg = Message(
                        subject="You've Been Awarded Points!",
                        sender=app.config['MAIL_USERNAME'],
                        recipients=[student.email],
                        body=f"""Hi {student.first_name},

You've just been awarded {points_to_add} points!

Your updated points balance is: {student.points}

Thank you for your contributions!
- Bowie Volunteer Portal
                        """
                    )
                    mail.send(msg)
                except Exception as e:
                    print(f"Email failed: {e}")
        return redirect(url_for('assign_points'))

    return render_template('assign_points.html', students=students)

if __name__ == '__main__':
    app.run(debug=True)
