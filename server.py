from flask import Flask, request, redirect, render_template, session, flash
from mysqlconnection import MySQLConnector
from flask.ext.bcrypt import Bcrypt

import re

EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9.+_-]+@[a-zA-Z0-9._-]+\.[a-zA-Z]+$')

app = Flask(__name__)
bcrypt = Bcrypt(app)
app.secret_key = 'ThisIsLoginKey'
mysql = MySQLConnector(app,'the_wall')

# ==============================================================================
#                                   Render
# ==============================================================================

@app.route('/')
def index():

    if session.get('login') == True:
        return redirect('/wall')

    return render_template('index.html')

@app.route('/register')
def register():
    pass
    return render_template('registration.html')

@app.route('/wall')
def wall():

    if session.get('login') == None:
        return redirect('/')
    id = session['user_id']
    user_query = "SELECT first_name FROM users WHERE id = :id"
    user_data = { 'id': id }
    user_name = mysql.query_db(user_query, user_data)

    message_query = "SELECT users.first_name, users.last_name, messages.message, messages.id, DATE_FORMAT(messages.created_at,'%b %d %Y %h:%i %p') as date, messages.users_id,messages.created_at, TIME_TO_SEC(messages.created_at) as created_at_in_sec,TIME_TO_SEC(NOW()) as current_time_in_sec FROM messages JOIN users on users.id = messages.users_id ORDER BY created_at desc;"

    comment_query = "SELECT users.first_name, users.last_name, DATE_FORMAT(comments.created_at,'%b %d %Y %h:%i %p') as date, comments.comments,comments.messages_id, comments.created_at from comments JOIN users on users.id = comments.user_id join messages on messages.id = comments.messages_id ORDER BY created_at desc;"

    messages = mysql.query_db(message_query)
    comments = mysql.query_db(comment_query)
    print messages
    return render_template('wall.html', user = user_name[0], messages = messages, comments = comments, edit_post_display = None)

# ==============================================================================
#                                   Process
# ==============================================================================

# ---------------------------
#       Registration
# ---------------------------

@app.route('/registration', methods=['POST'])
def registration():
    valid = True

    if len(request.form['first_name']) < 3:
        flash("First Name cannot be less than 3 Characters")
        valid = False

    if len(request.form['last_name']) < 3:
        flash("Last Name cannot be less than 3 Characters")
        valid = False

    if len(request.form['email']) < 5:
        flash("Email cannot be less than 5 Characters")
        valid = False
    elif not EMAIL_REGEX.match(request.form['email']):
        flash("Invalid Email Address")
        valid = False

    if len(request.form['pass']) < 4:
        flash("Password Should be 4 or More Characters")
        valid = False
    elif request.form['pass'] != request.form['passconf']:
        flash("Password doesn't match")
        valid = False

    if valid:

        first_name = request.form['first_name']
        last_name = request.form['last_name']
        email = request.form['email']
        password = request.form['pass']
        pw_hash = bcrypt.generate_password_hash(password)

        check_query = "SELECT COUNT(email) as email FROM users WHERE email = :email;"
        data = { 'email': email }
        email_exists = mysql.query_db(check_query, data)
        email_count = email_exists[0]['email']
        # email_count = email_exists['email']
        print email_count
        # int(email_count)

        if email_count > 0:
            flash("Email Already Exists")
            return redirect('/register')

        insert_query = "INSERT INTO users (first_name, last_name, email, password, created_at) VALUES (:first_name, :last_name, :email, :password, NOW())"

        query_data = {
            'first_name': first_name,
            'last_name': last_name,
            'email': email,
            'password': pw_hash
        }
        mysql.query_db(insert_query, query_data)
        session['login'] = True
        query = "SELECT id FROM users WHERE email = :email"
        data = { 'email': email }
        user_id = mysql.query_db(query, data)
        uid = user_id[0]
        session['user_id'] = uid['id']

        return redirect('/wall')

    return redirect('/register')

# ---------------------------
#           Login
# ---------------------------

@app.route('/login', methods=['POST'])
def login():

    if len(request.form['email']) < 5:
        flash("Email cannot be less than 5 Characters")
        return redirect('/')

    elif not EMAIL_REGEX.match(request.form['email']):
        flash("Invalid Email Address")
        return redirect('/')

    elif len(request.form['pass']) < 4:
        flash("Invalid Password")
        return redirect('/')

    else:
        email = request.form['email']
        password = request.form['pass']
        user_query = "SELECT * FROM users WHERE email = :email LIMIT 1"
        query_data = { 'email': email }
        user = mysql.query_db(user_query, query_data)
        if bcrypt.check_password_hash(user[0]['password'], password):
            session['login'] = True
            query = "SELECT id FROM users WHERE email = :email"
            data = { 'email': email }
            user_id = mysql.query_db(query, data)
            uid = user_id[0]
            session['user_id'] = uid['id']
        else:
            flash("Invalid Email or Password")
            return redirect('/')


    return redirect('/wall')

# ---------------------------
#           Logout
# ---------------------------

@app.route('/logout')
def logout():
    session.pop('login', None)
    session.pop('user_id', None)
    return redirect('/')

# ---------------------------
#       Posting Message
# ---------------------------

@app.route('/post_message', methods=['POST'])
def post_message():
    if session.get('login') == None:
        return redirect('/')
    user_id = session['user_id']
    message = request.form['message']
    insert_query = "INSERT INTO `messages` (`users_id`, `message`, `created_at`) VALUES (:user_id, :message, NOW());"
    data = {
        'user_id': user_id,
        'message': message
    }
    mysql.query_db(insert_query, data)

    return redirect('/wall')

# ---------------------------
#       Posting Comments
# ---------------------------

@app.route('/post_comment', methods=['POST'])
def post_comment():
    if session.get('login') == None:
        return redirect('/')
    user_id = session['user_id']
    messages_id = request.form['message_id']
    comment = request.form['comment']
    insert_query = "INSERT INTO comments (messages_id, user_id, comments, created_at) VALUES (:messages_id, :user_id, :comment, NOW())"
    data = {
        'messages_id': messages_id,
        'user_id': user_id,
        'comment': comment
    }
    mysql.query_db(insert_query, data)

    return redirect('/wall')

# ---------------------------
#       Delete Posts
# ---------------------------

@app.route('/delete_post/<message_id>')
def delete_post(message_id):
    if session.get('login') == None:
        return redirect('/')
    print message_id

    query = "SELECT users_id,TIME_TO_SEC(messages.created_at) as created_at_in_sec,TIME_TO_SEC(NOW()) as current_time_in_sec FROM messages WHERE id = :message_id"
    data = { 'message_id': message_id }
    print mysql.query_db(query,data)
    user_check = mysql.query_db(query, data)
    user_check_id = user_check[0]['users_id']
    ca_in_sec = user_check[0]['created_at_in_sec']
    current_time_sec = user_check[0]['current_time_in_sec']

    if current_time_sec - ca_in_sec >= 30:
        flash("You Cannot Delete Message after 30 Seconds")
        return redirect('/wall')

    if user_check_id == session['user_id']:

        comment_delete_query = "DELETE FROM comments WHERE messages_id = :message_id;"
        data = { 'message_id': message_id }
        mysql.query_db(comment_delete_query,data)

        delete_query = "DELETE FROM messages WHERE id = :message_id;"
        data = { 'message_id': message_id }
        mysql.query_db(delete_query,data)

    return redirect('/wall')

app.run(debug=True)
