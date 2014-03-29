import os
from flask import Flask, request
from werkzeug.utils import secure_filename
from moviepy.editor import *
from flask.ext.pymongo import PyMongo

UPLOAD_FOLDER = 'file-uploads'
ALLOWED_EXTENSIONS = set(['mp4'])

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

mongo = PyMongo(app)

@app.route("/")
def hello():
	return "Hello Tribe Hacks!"

if __name__ == "__main__":
	app.run(debug=True)