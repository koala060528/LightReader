from flask import Flask, request
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy, SignallingSession
from flask_migrate import Migrate
from flask_bootstrap import Bootstrap
from config import Config
from flask_uploads import UploadSet, configure_uploads, TEXT
from flask_moment import Moment
from flask_babel import Babel
from redis import Redis
import rq


# class MySQLAlchemy(SQLAlchemy):
#     def create_session(self, options):
#         options['autoflush'] = False
#         return SignallingSession(self, **options)


app = Flask(__name__)
app.config.from_object(Config)
login = LoginManager(app)
db = SQLAlchemy(app)
migrate = Migrate(app=app, db=db)
bootstrap = Bootstrap(app)
login.login_view = 'login'
text = UploadSet("downloads", TEXT)
configure_uploads(app, text)
moment = Moment(app)
babel = Babel(app)
redis = Redis.from_url(app.config['REDIS_URL'])
app.task_queue = rq.Queue('lightreader-tasks', connection=redis)

from app import models, routes

import create_db


@babel.localeselector
def get_locale():
    return request.accept_languages.best_match(app.config['LANGUAGES'])
