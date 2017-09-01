from nursingHomeApp import app
from flask import render_template


@app.route('/')
def base():
    return render_template('base.html')
