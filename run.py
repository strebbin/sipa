#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Drupalport auf Python im Zuge der Entwicklung von Pycroft.
Erstellt am 02.03.2014 von Dominik Pataky pataky@wh2.tu-dresden.de
"""

from flask import Flask, render_template, request, redirect, url_for, flash
from flask.ext.login import LoginManager, current_user, login_user, logout_user

from authentication import User, authenticate

app = Flask(__name__)
app.secret_key = "q_T_a1C18aizPnA2yf-1Q8(2&,pd5n"
login_manager = LoginManager()
login_manager.init_app(app)


@login_manager.user_loader
def load_user(username):
    return User.get(username)


@app.route('/')
def index():
    return render_template("index.html")


@app.route("/contacts")
def contacts():
    return render_template("content/ansprechpartner.html")


@app.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = authenticate(username, password)

        #TODO: error codes and flashes
        
        if isinstance(user, User):
            login_user(user)

    if current_user.is_authenticated():
        return redirect(url_for('index'))

    return render_template('login.html')


@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=True, host="localhost")
