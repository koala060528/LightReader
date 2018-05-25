from app import app, db
from app.models import User, Subscribe
import json
from flask import render_template, flash, redirect, url_for, request, jsonify
from app.forms import LoginForm, RegistrationForm,ResetPasswordForm,ResetPasswordRequestForm
from flask_login import current_user, login_required, login_user, logout_user
from werkzeug.urls import url_parse
from datetime import datetime
import requests


def get_response(url):
    data = requests.get(url).text
    js = json.loads(data)
    return js


@app.before_request
def before_request():
    if current_user.is_authenticated:
        current_user.last_seen=datetime.utcnow()
        # 教程上说不需要加这一行，亲测需要
        db.session.add(current_user)
        db.session.commit()


@app.route('/login',methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        u = User.query.filter_by(name = form.username.data).first()
        if u is None or not u.check_password(form.password.data):
            flash('登录失败')
            return redirect('login')
        login_user(u, remember=form.remember_me.data)
        # 网页回调，使用户登录后返回登录前页面
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).decode_netloc() != '':
            next_page = url_for('index')
        return redirect(next_page)
    return render_template('login.html',title = '登录', form = form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    # todo
    pass


@app.route('/reset_password_request',methods=['POST','GET'])
def reset_password_request():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = ResetPasswordRequestForm()
    # 少了括号会报错validate_on_submit() missing 1 required positional argument: 'self'
    if form.validate_on_submit():
        user=User.query.filter_by(email=form.email.data).first()
        if user:
            # send_password_reset_email(user)
            pass
            # todo
        flash('Check your email for the instructions to reset your password')
        return redirect(url_for('login'))
    return render_template('reset_password_request.html',title='Reset Password',form=form)


@app.route('/reset_password/<token>',methods=['GET','POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    user=User.verify_reset_password_token(token)
    if not user:
        return redirect(url_for('index'))
    form=ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        flash('Your password has been reset')
        return redirect(url_for('login'))
    return render_template('reset_password.html',title='Reset Password',form=form)


@app.route('/', methods=['GET'])
@app.route('/index', methods=['GET'])
@login_required
def index():
    data = {}
    # 获取订阅信息
    data['subscribe'] = []
    for b in current_user.subscribing:
        js = get_response('http://api.zhuishushenqi.com/book/' + b._id)
        data['subscribe'] . append({
            'title': js['title'],
            '_id': b._id,
            'last_chapter': js['lastChapter'],
            'updated': js['updated']
        })
    # 获取榜单信息

    return jsonify(data)


@app.route('/subscribe/<_id>', methods=['GET'])
@login_required
def subscribe(_id):
    js = get_response('http://api.zhuishushenqi.com/book/' + _id)
    name = js.get('title')
    if not name:
        flash('这本书不存在')
        return '', 403

    s = Subscribe(user=current_user, book_id=_id, book_name=name)
    db.session.add(s)
    db.session.commit()
    flash('订阅成功')


@app.route('/unsubscribe/<_id>', methods=['DELETE'])
@login_required
def unsubscribe(_id):
    s = Subscribe.query.filter_by(user=current_user, book_id=_id)
    db.session.remove(s)
    db.session.commit()
    flash('取消订阅成功')




