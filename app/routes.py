from app import app, db
from app.models import User, Subscribe
import json
from flask import render_template, flash, redirect, url_for, request, jsonify
from app.forms import LoginForm, RegistrationForm, SearchForm, JumpForm
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

    # 获取分类
    data = get_response('http://api.zhuishushenqi.com/cats/lv2/statistics')
    # 预分组
    # data['male'] = [data['male'][i:i + 3] for i in range(0, len(data['male']), 3)]
    # data['female'] = [data['female'][i:i + 3] for i in range(0, len(data['female']), 3)]
    # data['press'] = [data['press'][i:i + 3] for i in range(0, len(data['press']), 3)]
    dic['classify'] = data

    # 搜索框
    form = SearchForm()
    if form.validate_on_submit():
        data = get_response('http://api.zhuishushenqi.com/book/fuzzy-search/?query=' + form.search.data)
        lis = []
        for book in data.get('books'):
            lis.append(book)
        return render_template('book_list.html', data=lis, title='搜索结果', form=form)

    return render_template('index.html', data=dic, form=form, title='首页', limit=Config.CHAPTER_PER_PAGE)


@app.route('/subscribe/')
@login_required
def subscribe():
    _id = request.args.get('id')
    js = get_response('http://api.zhuishushenqi.com/book/' + _id)
    name = js.get('title')
    if not name:
        flash('这本书不存在')
        return redirect(url_for('index'))

    data = get_response('http://api.zhuishushenqi.com/toc?view=summary&book=' + _id)

    s = Subscribe(user=current_user, book_id=_id, book_name=name, source_id=data[1]['_id'])
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


@app.route('/chapter/<source_id>', methods=['GET', 'POST'])
def chapter(source_id):
    page = request.args.get('page')
    book_id = request.args.get('book_id')
    data = get_response('http://api.zhuishushenqi.com/toc/{0}?view=chapters'.format(source_id))
    lis = []
    l = []
    chap = data.get('chapters')
    form = JumpForm()
    if form.validate_on_submit():  # 必须使用post方法才能正产传递参数
        page = form.page.data
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

    if form.validate_on_submit():
        return render_template('chapter.html', data=l, title='章节列表', page_count=page_count, page=form.page.data,
                               source_id=source_id,
                               book_id=book_id, form=form)

    return render_template('chapter.html', data=l, title='章节列表', page_count=page_count, page=page, source_id=source_id,
                           book_id=book_id, form=form)


@app.route('/read/', methods=['GET'])
# @login_required
def read():
    index = int(request.args.get('index'))
    source_id = request.args.get('source_id')
    book_id = request.args.get('book_id')
    data = get_response('http://api.zhuishushenqi.com/toc/{0}?view=chapters'.format(source_id))
    page = int(index / Config.CHAPTER_PER_PAGE)
    chap = data.get('chapters')
    title = chap[index]['title']
    url = chap[index]['link']
    chapter_url = Config.CHAPTER_DETAIL.format(url.replace('/', '%2F').replace('?', '%3F'))
    data = get_response(chapter_url)
    body = data.get('chapter').get('cpContent')
    if not body:
        body = data.get('chapter').get('body')
    lis = body.split('\n')
    li = []
    for l in lis:
        if l != '' and l != '\t':
            li.append(l)

    if current_user.is_authenticated:
        s = Subscribe.query.filter(Subscribe.book_id == book_id, Subscribe.user == current_user).first()
        if s:
            s.chapter = index
            s.source_id = source_id
            db.session.commit()

    return render_template('read.html', body=li, title=title, next=(index + 1) if len(chap) - index > 1 else None,
                           pre=(index - 1) if index > 0 else None,
                           book_id=book_id, page=page, source_id=source_id)


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
    book_id = request.args.get('book_id')
    data = get_response('http://api.zhuishushenqi.com/book/' + book_id)
    t = data['updated']  # = datetime(data['updated']).strftime('%Y-%m-%d %H:%M:%S')
    t = datetime.strptime(t, '%Y-%m-%dT%H:%M:%S.%fZ')
    data['updated'] = utc2local(t).strftime('%Y-%m-%d %H:%M:%S')
    lis = data.get('longIntro').split('\n')
    data['longIntro'] = lis
    if current_user.is_authenticated:
        s = current_user.subscribing.filter(Subscribe.book_id == book_id).first()
        if s:
            data['is_subscribe'] = True
            if s.source_id:
                source_id = s.source_id
            else:
                dd = get_response('http://api.zhuishushenqi.com/toc?view=summary&book={0}'.format(book_id))
                s.source_id = dd[0]['_id']
                db.session.commit()
                source_id = dd[0]['_id']
            c = s.chapter
            if not c:
                c = 0
            data['reading'] = c
            dd = get_response('http://api.zhuishushenqi.com/toc/{0}?view=chapters'.format(source_id))
            chap = dd.get('chapters')

            # chapter_title = chap[int(c)]['title']
            if int(c) + 1 > len(chap):
                data['readingChapter'] = chap[-1]['title']
            else:
                data['readingChapter'] = chap[int(c)]['title']
        else:
            dd = get_response('http://api.zhuishushenqi.com/toc?view=summary&book=' + book_id)
            for i in dd:
                if i['source'] != 'zhuishuvip':
                    source_id = i['_id']

    return render_template('book_detail.html', data=data, title=data.get('title'), source_id=source_id, book_id=book_id)


@app.route('/source/<book_id>', methods=['GET'])
def source(book_id):
    page = request.args.get('page')
    data = get_response('http://api.zhuishushenqi.com/toc?view=summary&book=' + book_id)
    for s in data:
        t = s['updated']
        t = datetime.strptime(t, '%Y-%m-%dT%H:%M:%S.%fZ')
        s['updated'] = utc2local(t).strftime('%Y-%m-%d %H:%M:%S')
    if not page:
        page = 0
    return render_template('source.html', data=data[1:], title='换源', page=page, book_id=book_id)


@app.route('/rank', methods=['GET'])
def rank():
    gender = request.args.get('gender')
    _type = request.args.get('type')
    major = request.args.get('major')
    start = request.args.get('start')
    # limit = request.args.get('limit')
    # page = request.args.get('page')
    # tag = request.args.get('tag')
    limit = str(Config.CHAPTER_PER_PAGE)
    data = get_response(
        'http://api.zhuishushenqi.com/book/by-categories?' + (('&major=' + major) if major else '') + (
            ('&gender=' + gender) if gender else '') + (('&type=' + _type) if _type else '') + (
            ('&start=' + start) if start else '') + (('&limit=' + limit) if limit else ''))
    data = data['books']
    next_page = True
    if len(data) < Config.CHAPTER_PER_PAGE:
        next_page = False
    return render_template('rank.html', data=data, title='探索', gender=gender, type=_type, major=major, start=int(start),
                           limit=int(limit), next=next_page)
