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

def allowed_file(filename):
	"""Takes in a filename and returns whether or not it is of the allowed filetype."""
  return '.' in filename and \
		filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS


@app.route("/")
def hello():
	return "Hello Tribe Hacks!"

if __name__ == "__main__":
	app.run(debug=True)