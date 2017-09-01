from flask import Flask

app = Flask(__name__)
app.config.from_object('nursingHomeApp.config')
from nursingHomeApp.views import wireframe

