from flask import Flask
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_bootstrap import Bootstrap
from config import Config
from flask_uploads import UploadSet, configure_uploads, TEXT


app = Flask(__name__)
app.config.from_object(Config)
login = LoginManager(app)
db = SQLAlchemy(app)
migrate = Migrate(app=app, db=db)
bootstrap = Bootstrap(app)
login.login_view = 'login'
text = UploadSet("downloads",TEXT)
configure_uploads(app,text)

from app import models, routes

import create_db

