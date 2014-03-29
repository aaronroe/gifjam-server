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

@app.route("/upload", methods=["POST"])
def upload():
	file = request.files['video']

	if file and allowed_file(file.filename):
		# escape the filename so it is safe to store on the server
		filename = secure_filename(file.filename)

		# the name & path of upload.
		name_with_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
		file.save(name_with_path)

		gifname = filename.rsplit(".", 1)[0] + ".gif"
		gifpath = "converted/" + gifname

		# Create the gif
		VideoFileClip(name_with_path).subclip((0,0.0), (0,1.0)).resize(0.3).to_gif(gifpath)

		# save the video and gif to mongo
		giffile = open(gifpath)
		mongo.save_file(file.filename, file)
		mongo.save_file(gifname, giffile)
		giffile.close()

		# clean up what we uploaded.
		os.remove(name_with_path)
		os.remove(gifpath)
	return ""

if __name__ == "__main__":
	app.run(debug=True)