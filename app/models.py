from app import db, login
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import check_password_hash, generate_password_hash


# subscribe = db.Table('subscribe',
#                      db.Column('user_id',db.Integer,db.ForeignKey('user.id')),
#                      db.Column('book_id',db.Integer,db.ForeignKey('book.id'))
#                      )


class User(UserMixin, db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20), unique=True, nullable=False)
    # email = db.Column(db.String(50),unique=True,nullable=False)
    password_hash = db.Column(db.String(128))
    can_download = db.Column(db.Boolean)  # 表示用户是否有下载权限，0表示没有，1表示有
    last_seen = db.Column(db.DateTime,default=datetime.now())
    user_ip = db.Column(db.String(20))
    user_agent = db.Column(db.String(256))

    # subscribing = db.relationship('Book',
    #                              secondary=subscribe,
    #                              primaryjoin=(subscribe.c.user_id==id),
    #                              backref=db.backref('subscribe',lazy='dynamic'),
    #                              lazy='dynamic')

    def __repr__(self):
        return '<User {%s}>' % self.name

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    # # 以下几个方法存在不明bug
    # def is_subscribing(self,book):
    #     return self.subscribing.filter(subscribe.c.book_id == book.id).count() > 0
    #
    # def subscribe(self,book):
    #     if not self.is_subscribing(book):
    #         self.subscribing.append(book)
    #
    # def un_subscribe(self,book):
    #     if self.is_subscribing(book):
    #         self.subscribing.remove(book)


class Subscribe(db.Model):
    __tablename__ = 'subscribe'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    book_id = db.Column(db.String(128))
    book_name = db.Column(db.String(128))
    chapter = db.Column(db.String(128))
    source_id = db.Column(db.String(128))
    time = db.Column(db.DateTime,default=datetime.now())

    user = db.relationship('User', backref=db.backref('subscribing', lazy='dynamic'))

    def __repr__(self):
        return '<User>{%s} subscribing <Book>{%s} reading <chapter>{%s}' % (self.user_id, self.book_id, self.chapter)


# class Book(db.Model):
#     __tablename__ = 'book'
#     id = db.Column(db.Integer,primary_key=True)
#     _id = db.Column(db.String(50),unique=True)
#     name = db.Column(db.String(50))
#
#     subscribed = db.relationship('User',
#                                  secondary=subscribe,
#                                  primaryjoin=(subscribe.c.book_id==id),
#                                  backref=db.backref('subscribe',lazy='dynamic'),
#                                  lazy='dynamic')
#
#     def __repr__(self):
#         return '<Book {%s}>' % self.name


@login.user_loader
def load_user(id):
    user = User.query.get(int(id))
    return user
