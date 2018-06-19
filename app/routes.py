from app import app, db
from app.models import User, Subscribe
import json
from flask import render_template, flash, redirect, url_for, request, jsonify
from app.forms import LoginForm, RegistrationForm, SearchForm
from flask_login import current_user, login_required, login_user, logout_user
from werkzeug.urls import url_parse
from datetime import datetime
from time import time
import requests
from config import Config


def get_response(url):
    data = requests.get(url).text
    js = json.loads(data)
    return js


# @app.before_request
# def before_request():
#     if current_user.is_authenticated:
#         current_user.last_seen = datetime.utcnow()
#         # 教程上说不需要加这一行，亲测需要
#         db.session.add(current_user)
#         db.session.commit()


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        u = User.query.filter_by(name=form.username.data).first()
        if u is None or not u.check_password(form.password.data):
            flash('登录失败')
            return redirect('login')
        login_user(u, remember=form.remember_me.data)
        # 网页回调，使用户登录后返回登录前页面
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).decode_netloc() != '':
            next_page = url_for('index')
        return redirect(next_page)
    return render_template('login.html', title='登录', form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        u = User(name=form.username.data)
        u.set_password(form.password.data)
        db.session.add(u)
        db.session.commit()
        flash('注册成功')
        return redirect(url_for('login'))
    return render_template('register.html', form=form, title='注册')


@app.route('/', methods=['GET', 'POST'])
@app.route('/index', methods=['GET', 'POST'])
# @login_required
def index():
    dic = {}

    # 获取订阅信息
    if current_user.is_authenticated:
        dic['subscribe'] = []
        for s in current_user.subscribing:
            js = get_response('http://api.zhuishushenqi.com/book/' + s.book_id)
            dic['subscribe'].append({
                'title': js['title'],
                '_id': s.book_id,
                'last_chapter': js['lastChapter'],
                'updated': js['updated']
            })
    # 获取榜单信息
    # todo

    # 搜索框
    form = SearchForm()
    if form.validate_on_submit():
        data = get_response('http://api.zhuishushenqi.com/book/fuzzy-search/?query=' + form.search.data)
        lis = []
        for book in data.get('books'):
            lis.append(book)
        return render_template('book_list.html', data=lis, title='搜索结果', form=form)

    return render_template('index.html', data=dic, form=form, title='首页')


@app.route('/subscribe/')
@login_required
def subscribe():
    _id = request.args.get('id')
    js = get_response('http://api.zhuishushenqi.com/book/' + _id)
    name = js.get('title')
    if not name:
        flash('这本书不存在')
        return redirect(url_for('index'))

    s = Subscribe(user=current_user, book_id=_id, book_name=name)
    db.session.add(s)
    db.session.commit()
    flash('订阅成功')
    next_page = request.args.get('next')
    if not next_page or url_parse(next_page).decode_netloc() != '':
        next_page = url_for('index')
    return redirect(next_page)


@app.route('/unsubscribe/')
@login_required
def unsubscribe():
    _id = request.args.get('id')
    s = current_user.subscribing.filter(Subscribe.book_id == _id).first()
    db.session.delete(s)
    db.session.commit()
    flash('取消订阅成功')
    next_page = request.args.get('next')
    if not next_page or url_parse(next_page).decode_netloc() != '':
        next_page = url_for('index')
    return redirect(next_page)


@app.route('/chapter/<id>', methods=['GET'])
def chapter(id):
    page = request.args.get('page')
    bookId = id
    data = get_response('http://api.zhuishushenqi.com/mix-atoc/' + str(bookId))
    lis = []
    l = []
    chap = data.get('mixToc').get('chapters')
    page_count = int(len(chap) / Config.CHAPTER_PER_PAGE)
    if len(chap) % Config.CHAPTER_PER_PAGE == 0:
        page_count -= 1
    if page is not None:
        page = int(page)
        if page > page_count:
            page = page_count
        lis = chap[page * Config.CHAPTER_PER_PAGE:(page + 1) * Config.CHAPTER_PER_PAGE]
        i = 0
    for c in lis:
        l.append({
            'index': page * Config.CHAPTER_PER_PAGE + i,
            'title': c.get('title')
        })
        i += 1

    return render_template('chapter.html', data=l, title='章节列表', page_count=page_count, page=page, id=bookId)


@app.route('/read/', methods=['GET'])
# @login_required
def read():
    index = int(request.args.get('index'))
    bookId = request.args.get('bookId')
    data = get_response('http://api.zhuishushenqi.com/mix-atoc/' + str(bookId))
    page = int(index / Config.CHAPTER_PER_PAGE)
    chap = data.get('mixToc').get('chapters')
    title = chap[index]['title']
    url = chap[index]['link']
    chapter_url = Config.CHAPTER_DETAIL.format(url.replace('/', '%2F').replace('?', '%3F'))
    data = get_response(chapter_url)
    body = data.get('chapter').get('body')
    lis = body.split('\n')

    if current_user.is_authenticated:
        s = Subscribe.query.filter(Subscribe.book_id == bookId, Subscribe.user == current_user).first()
        s.chapter = index
        db.session.commit()

    return render_template('read.html', body=lis, title=title, next=(index + 1) if len(chap) - index > 1 else None,
                           pre=(index - 1) if index > 0 else None,
                           bookId=bookId, page=page)


# @app.route('/search/', methods=['GET', 'POST'])
# def search():
#     form = SearchForm()
#     if form.validate_on_submit():
#         data = get_response('http://api.zhuishushenqi.com/book/fuzzy-search/?query=' + form.search.data)
#         lis = []
#         for book in data.get('books'):
#             lis.append(book)
#         return render_template('book_list.html', data=lis, title='搜索结果')
#     return render_template('book_list.html', form=form, title='搜索')


UTC_FORMAT = '%Y-%m-%dT%H:%M:%S.%fZ'
LOCAL_FORMAT = '%Y-%m-%d %H:%M:%S'


def utc2local(utc_st):
    now_stamp = time()
    local_time = datetime.fromtimestamp(now_stamp)
    utc_time = datetime.utcfromtimestamp(now_stamp)
    offset = local_time - utc_time
    local_st = utc_st + offset
    return local_st


def local2utc(local_st):
    time_struct = time.mktime(local_st.timetuple())
    utc_st = datetime.datetime.utcfromtimestamp(time_struct)
    return utc_st


@app.route('/book_detail', methods=['GET'])
def book_detail():
    bookId = request.args.get('id')
    data = get_response('http://api.zhuishushenqi.com/book/' + bookId)
    t = data['updated']  # = datetime(data['updated']).strftime('%Y-%m-%d %H:%M:%S')
    t = datetime.strptime(t, '%Y-%m-%dT%H:%M:%S.%fZ')
    data['updated'] = utc2local(t).strftime('%Y-%m-%d %H:%M:%S')
    lis = data.get('longIntro').split('\n')
    data['longIntro']=lis
    if current_user.is_authenticated:
        s = current_user.subscribing.filter(Subscribe.book_id == bookId).first()
        if s:
            data['is_subscribe'] = True
            c = s.chapter
            if not c:
                c = 0
            data['reading'] = c
            d = get_response('http://api.zhuishushenqi.com/mix-atoc/' + str(bookId))
            chap = d.get('mixToc').get('chapters')
            # chapter_title = chap[int(c)]['title']
            data['readingChapter'] = chap[int(c)]['title']

    return render_template('book_detail.html', data=data, title=data.get('title'))
