from flask import Flask, render_template
from flask import flash
from flask import request, redirect, url_for
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import date, timedelta
from flask_mail import Mail, Message
import logging
logging.basicConfig(level=logging.DEBUG)

from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
import os
load_dotenv()
scheduler = BackgroundScheduler()
scheduler.start()



app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///habits.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
 

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_USERNAME')

print("MAIL_USERNAME:", os.getenv('MAIL_USERNAME'))
print("MAIL_PASSWORD:", os.getenv('MAIL_PASSWORD'))

app.config['SECRET_KEY'] = 'your_secret_key_here'


mail = Mail(app)
def send_reminder_email(habit):
    msg = Message(
        subject="Habit Reminder",
        sender=app.config['MAIL_DEFAULT_SENDER'],
        recipients=['recipient-email@example.com'],
        body=f"Don't forget to complete your habit: {habit.name} today!"
    )
    try:
        mail.send(msg)
        print(f"Email sent for habit: {habit.name}")
    except Exception as e:
        print(f"Failed to send email for habit: {habit.name}. Error: {e}")

def check_habits_and_send_emails():
    with app.app_context():
        now = datetime.now()
        current_time = now.strftime('%H:%M')
        app.logger.debug(f"Checking reminders at {current_time}")
        
        habits = Habit.query.all()
        for habit in habits:
            app.logger.debug(f"Checking habit {habit.name} with time {habit.reminder_time}")
            if habit.reminder_time == current_time:
                send_reminder_email(habit)
                app.logger.debug(f"Sent reminder for habit: {habit.name}")

@app.route('/send_reminder/<int:habit_id>')
def test_send_email(habit_id):
    habit = Habit.query.get(habit_id)
    if habit:
        send_reminder_email(habit)
        return "Reminder email sent!"
    return "Habit not found."


class Habit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(200))
    reminder_time = db.Column(db.String(10))  # e.g., '07:00'

class Progress(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    habit_id = db.Column(db.Integer, db.ForeignKey('habit.id'), nullable=False)
    date = db.Column(db.String(10), nullable=False)  # e.g., '2025-09-10'

    habit = db.relationship('Habit', backref=db.backref('progresses', lazy=True))

    def __repr__(self):
        return f'<Progress {self.habit.name} on {self.date}>'


    def __repr__(self):
        return f'<Habit {self.name}>'
@app.route('/add', methods=['POST'])
def add_habit():
    name = request.form.get('name')
    description = request.form.get('description')
    reminder_time = request.form.get('reminder_time')

    if not name or not reminder_time:
        flash('Please fill in all required fields!', 'error')
        return redirect(url_for('index'))

    new_habit = Habit(name=name, description=description, reminder_time=reminder_time)
    db.session.add(new_habit)
    db.session.commit()

    flash('Habit added successfully!', 'success')
    return redirect(url_for('index'))

   


@app.route('/complete/<int:habit_id>', methods=['POST'])
def complete_habit(habit_id):
    habit = Habit.query.get(habit_id)
    if not habit:
        return "Habit not found!", 404  # Not found

    today = date.today().isoformat()
    existing_progress = Progress.query.filter_by(habit_id=habit_id, date=today).first()
    if existing_progress:
        return redirect(url_for('index'))  # Already completed today

    progress = Progress(habit_id=habit_id, date=today)
    db.session.add(progress)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/view')
def view_habits():
    habits = Habit.query.all()
    streaks = {}
    today = date.today()

    for habit in habits:
        progresses = Progress.query.filter_by(habit_id=habit.id).all()
        dates = sorted([date.fromisoformat(p.date) for p in progresses], reverse=True)

        streak = 0
        current_date = today

        for d in dates:
            if d == current_date:
                streak += 1
                current_date -= timedelta(days=1)
            else:
                break

        streaks[habit.id] = streak

    return render_template('view_habits.html', habits=habits, streaks=streaks)



@app.route('/')
def index():
    return render_template('index.html')

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
