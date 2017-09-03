from nursingHomeApp import app
from flask import render_template


@app.route('/')
def base():
    return render_template('base.html')


@app.route('/patient')
def patient():
    return render_template('add_patient.html')
