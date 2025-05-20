from flask import Flask, request, jsonify
from flask_mysqldb import MySQL
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# MySQL Configuration
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'password'
app.config['MYSQL_DB'] = 'CommunityServiceDB'
mysql = MySQL(app)

# User Login
@app.route('/login', methods=['POST'])
def login():
    data = request.json
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM studentsCredentials WHERE username = %s AND password = %s", (data['username'], data['password']))
    user = cursor.fetchone()
    cursor.close()
    if user:
        return jsonify({"message": "Login successful", "user": user})
    else:
        return jsonify({"message": "Invalid credentials"}), 401

# Add Student
@app.route('/students', methods=['POST'])
def add_student():
    data = request.json
    cursor = mysql.connection.cursor()
    cursor.execute("INSERT INTO studentsInfo (studentID, firstName, lastName, userID) VALUES (%s, %s, %s, %s)", 
                   (data['studentID'], data['firstName'], data['lastName'], data['userID']))
    mysql.connection.commit()
    cursor.close()
    return jsonify({"message": "Student added successfully"})

# Get All Students
@app.route('/students', methods=['GET'])
def get_students():
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM studentsInfo")
    students = cursor.fetchall()
    cursor.close()
    return jsonify({"students": students})

# Get Available Events
@app.route('/events', methods=['GET'])
def get_events():
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM eventsAvailable")
    events = cursor.fetchall()
    cursor.close()
    return jsonify({"events": events})

# Volunteer for an Event
@app.route('/volunteer', methods=['POST'])
def volunteer_for_event():
    data = request.json
    cursor = mysql.connection.cursor()
    cursor.execute("INSERT INTO volunteerTracking (studentID, eventID) VALUES (%s, %s)", (data['studentID'], data['eventID']))
    mysql.connection.commit()
    cursor.close()
    return jsonify({"message": "Volunteer record added"})

# Get Student Incentives
@app.route('/incentives/<int:student_id>', methods=['GET'])
def get_incentives(student_id):
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT incentiveType, promoCode FROM incentives WHERE studentID = %s", (student_id,))
    incentives = cursor.fetchall()
    cursor.close()
    return jsonify({"incentives": incentives})

if __name__ == '__main__':
    app.run(debug=True)
