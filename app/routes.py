from app import app, db, text, redis
from app.models import User, Subscribe, Download, Task
import json, os, re
from flask import render_template, flash, redirect, url_for, request, jsonify, current_app
from app.forms import LoginForm, RegistrationForm, SearchForm, JumpForm
from flask_login import current_user, login_required, login_user, logout_user
from werkzeug.urls import url_parse
from datetime import datetime
from time import time
import requests
from config import Config
from hashlib import md5


def get_response(url):
    i = 0
    while i < 5:
        js = None
        try:
            data = requests.get(url).text
            js = json.loads(data)
            break
        except:
            i += 1
    return js


@app.before_request
def before_request():
    if current_user.is_authenticated:
        current_user.last_seen = datetime.utcnow()
        current_user.user_ip = request.headers.environ.get('REMOTE_ADDR')
        current_user.user_agent = request.headers.environ.get('HTTP_USER_AGENT')
        # 教程上说不需要加这一行，亲测需要
        db.session.add(current_user)
        db.session.commit()


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


@app.route('/delete_user/<id>', methods=['GET'])
def delete_user(id):
    if not current_user.is_admin:
        return render_template('permission_denied.html', message=None, title='权限不足')
    u = User.query.get(id)
    db.session.delete(u)
    db.session.commit()
    flash('删除用户成功！')
    return redirect(url_for('user_list'))


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

    s = Subscribe(user=current_user, book_id=_id, book_name=name, source_id=data[1]['_id'], chapter=0)
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
    # 为各个源添加特殊处理
    if data['source'] == 'biquge':
        url = reg_biquge(data['link'], url)
    # 设定redis key
    key = md5((source_id + str(index)).encode("utf8")).hexdigest()[:10]

    # chapter_url = Config.CHAPTER_DETAIL.format(url.replace('/', '%2F').replace('?', '%3F'))
    # data = get_response(chapter_url)
    # if not data:
    #     body = '检测到阅读接口发生故障，请刷新页面或稍后再试'
    # else:
    #     if data['ok']:
    #         body = data.get('chapter').get('cpContent')
    #     else:
    #         body = '此来源暂不可用，请换源'
    #     if not body:
    #         body = data.get('chapter').get('body')
    # lis = body.split('\n')
    # li = []
    # for l in lis:
    #     if l != '' and l != '\t':
    #         li.append(l)
    li = get_content_list(key=key, url=url)
    if index < len(chap):
        next_key = md5((source_id + str(index + 1)).encode("utf8")).hexdigest()[:10]
        next_url = chap[index + 1]['link']
        # 使用后台任务缓存下一章节
        try:
            current_app.task_queue.enqueue('app.tasks.cache', next_key, next_url)
        except:
            print('后台任务未开启！')

    if current_user.is_authenticated:
        s = Subscribe.query.filter(Subscribe.book_id == book_id, Subscribe.user == current_user).first()
        if s:
            s.chapter = index
            s.chapter_name = title
            s.source_id = source_id
            s.time = datetime.utcnow()
            db.session.commit()

    return render_template('read.html', body=li, title=title, next=(index + 1) if len(chap) - index > 1 else None,
                           pre=(index - 1) if index > 0 else None,
                           book_id=book_id, page=page, source_id=source_id)


def reg_biquge(book_url, chapter_url):
    reg_normal = r'(http:\/\/www.biquge.la\/book\/[0-9]*\/[0-9]*.html)'
    reg_error = r'(http:\/\/www.biquge.la[0-9]*.html)'
    reg_chapter = r'([0-9]*.html)'
    reg = re.compile(reg_normal)
    lis = re.findall(reg, chapter_url)
    if lis:
        return chapter_url
    else:
        reg = re.compile(reg_error)
        lis = re.findall(reg, chapter_url)
        if lis:
            reg = re.compile(reg_chapter)
            lis = re.findall(reg, chapter_url)
            if lis:
                return book_url + lis[0]
    return chapter_url


def get_content_text(url):
    chapter_url = Config.CHAPTER_DETAIL.format(url.replace('/', '%2F').replace('?', '%3F'))
    data = get_response(chapter_url)
    if not data:
        txt = '检测到阅读接口发生故障，请刷新页面或稍后再试'
    else:
        if data['ok']:
            txt = data.get('chapter').get('cpContent')
        else:
            txt = '此来源暂不可用，请换源'
        if not txt:
            txt = data.get('chapter').get('body')
    return txt


def get_content_list(url, key=None):
    if key and redis.exists(key):
        txt = redis.get(key).decode()
    else:
        txt = get_content_text(url)
    lis = txt.split('\n')
    li = []
    for l in lis:
        if l != '' and l != '\t':
            li.append(l)
    return li


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
    # t = data['updated']  # = datetime(data['updated']).strftime('%Y-%m-%d %H:%M:%S')
    # t = datetime.strptime(t, '%Y-%m-%dT%H:%M:%S.%fZ')
    # data['updated'] = utc2local(t).strftime('%Y-%m-%d %H:%M:%S')
    source_id = None
    UTC_FORMAT = '%Y-%m-%dT%H:%M:%S.%fZ'
    t = datetime.strptime(data['updated'], UTC_FORMAT)
    data['updated'] = t
    lis = data.get('longIntro').split('\n')
    data['longIntro'] = lis
    lastIndex = None
    # can_download = False
    if current_user.is_authenticated:
        # can_download = current_user.can_download
        s = current_user.subscribing.filter(Subscribe.book_id == book_id).first()
        if s:
            data['is_subscribe'] = True
            source_id = s.source_id
            c = s.chapter
            if not c:
                c = 0
            data['reading'] = c
            dd = get_response('http://api.zhuishushenqi.com/toc/{0}?view=chapters'.format(source_id))
            chap = dd.get('chapters')
            if chap[-1].get('title') == data.get('lastChapter'):
                lastIndex = len(chap) - 1  # 用来标记最新章节
            # chapter_title = chap[int(c)]['title']
            if int(c) + 1 > len(chap):
                data['readingChapter'] = chap[-1]['title']
            else:
                data['readingChapter'] = chap[int(c)]['title']
        else:
            dd = get_response('http://api.zhuishushenqi.com/toc?view=summary&book=' + book_id)
            for i in range(len(dd))[::-1]:
                if dd[i]['source'] != 'zhuishuvip':
                    source_id = dd[i]['_id']
                    if dd[i]['source'] == 'my176':
                        break
    else:
        dd = get_response('http://api.zhuishushenqi.com/toc?view=summary&book=' + book_id)
        for i in range(len(dd))[::-1]:
            if dd[i]['source'] != 'zhuishuvip':
                source_id = dd[i]['_id']
                if dd[i]['source'] == 'my176':
                    break
    if not source_id:
        return render_template('source_not_found.html', title='暂无资源', message='抱歉，这本书暂无有效资源')
    else:
        return render_template('book_detail.html', data=data, title=data.get('title'), source_id=source_id,
                               book_id=book_id,
                               lastIndex=lastIndex,
                               next=(int(data['reading']) + 1) if data.get(
                                   'reading') is not None and lastIndex is not None and lastIndex > int(
                                   data['reading']) else None)


@app.route('/source/<book_id>', methods=['GET'])
def source(book_id):
    page = request.args.get('page')
    data = get_response('http://api.zhuishushenqi.com/toc?view=summary&book=' + book_id)
    for s in data:
        UTC_FORMAT = '%Y-%m-%dT%H:%M:%S.%fZ'
        t = datetime.strptime(s['updated'], UTC_FORMAT)
        s['updated'] = t
        # t = s['updated']
        # t = datetime.strptime(t, '%Y-%m-%dT%H:%M:%S.%fZ')
        # s['updated'] = utc2local(t).strftime('%Y-%m-%d %H:%M:%S')
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


@app.route('/download', methods=['GET'])
@login_required
def download():
    if not current_user.is_authenticated:
        return render_template('permission_denied.html', title='权限不足', message='下载功能并非向所有人开放，请联系管理员索取权限')
    else:
        if not current_user.can_download:
            return render_template('permission_denied.html', title='权限不足', message='下载功能并非向所有人开放，请联系管理员索取权限')
    source_id = request.args.get('source_id')
    book_id = request.args.get('book_id')
    data = get_response('http://api.zhuishushenqi.com/book/' + book_id)
    book_name = data.get('title')

    d = Download.query.filter_by(book_id=book_id, source_id=source_id).first()

    # 检测资源锁
    if d:
        if d.lock:
            # 检测文件锁
            flash('文件正在生成，请稍后再试！')
            return redirect(url_for('book_detail', book_id=book_id))
        else:
            # 检测服务器是否已经下载了文件的最新版本
            data = get_response('http://api.zhuishushenqi.com/toc/{0}?view=chapters'.format(source_id))
            chapter_list = data.get('chapters')
            download_list = chapter_list[d.chapter + 1:]

            if len(download_list) == 0:
                # 如果不存在新章节，返回文件链接
                book_title = d.book_name
                fileName = md5((book_id + source_id).encode("utf8")).hexdigest()[:10] + '.txt'
                return render_template('view_documents.html', title=book_title + '--下载', url=text.url(fileName),
                                       book_title=book_title)

    # from app.tasks import download
    # download(source_id,book_id)

    # 进入后台任务处理流程
    # if current_user.get_task_in_progress('download'):
    #     flash('下载任务已经存在于您的任务列表当中！')
    # else:
    # 使用用户身份开启任务
    task = current_user.launch_task('download', book_name, source_id, book_id)
    db.session.commit()
    flash('下载任务已经提交，请稍后回来下载')
    return redirect(url_for('book_detail', book_id=book_id))

    # # 获取章节信息
    # data = get_response('http://api.zhuishushenqi.com/toc/{0}?view=chapters'.format(source_id))
    # path = os.path.join(Config.UPLOADS_DEFAULT_DEST, 'downloads')
    # if not os.path.exists(path):
    #     os.makedirs(path)
    #
    # # 定义文件名
    # fileName = md5((book_id + source_id).encode("utf8")).hexdigest()[:10] + '.txt'
    # # fileName = os.path.join(path, book_title + '.txt')
    # # if os.path.exists(fileName):
    # #     os.remove(fileName)
    #
    # chapter_list = data.get('chapters')
    # if d:
    #     # 截取需要下载的章节列表
    #     new = False
    #     download_list = chapter_list[d.chapter + 1:]
    #     book_title = d.book_name
    #     d.chapter = len(chapter_list) - 1
    #     d.time = datetime.utcnow()
    #     d.lock = True  # 给下载加锁
    #     d.chapter_name = chapter_list[len(chapter_list) - 1].get('title')
    # else:
    #     new = True
    #     # 获取书籍简介
    #     data1 = get_response('http://api.zhuishushenqi.com/book/' + book_id)
    #     book_title = data1.get('title')
    #     author = data1.get('author')
    #     longIntro = data1.get('longIntro')
    #     download_list = chapter_list
    #     d = Download(user=current_user, book_id=book_id, source_id=source_id, chapter=len(chapter_list) - 1,
    #                  book_name=book_title, time=datetime.utcnow(), txt_name=fileName, lock=True,
    #                  chapter_name=chapter_list[-1].get('title'))
    #
    # db.session.add(d)
    # db.session.commit()
    #
    # with open(os.path.join(path, fileName), 'a', encoding='gbk') as f:
    #     if new:
    #         f.writelines(
    #             ['    ', book_title, '\n', '\n', '    ', author, '\n', '\n', '    ', longIntro, '\n', '\n'])
    #     for chapter in download_list:
    #         title = chapter.get('title')
    #         url = chapter.get('link')
    #         # 为各个源添加特殊处理
    #         if data['source'] == 'biquge':
    #             url = reg_biquge(data['link'], url)
    #
    #         li = get_text(url)
    #         f.writelines(['\n', '    ', title, '\n', '\n'])
    #         for sentence in li:
    #             try:
    #                 f.writelines(['    ', sentence, '\n', '\n'])
    #             except:
    #                 pass
    # d.lock = False  # 给下载解锁
    # db.session.add(d)
    # db.session.commit()
    # return render_template('view_documents.html', title=book_title + '--下载', url=text.url(fileName),
    #                        book_title=book_title)


@app.route('/background', methods=['GET'])
@login_required
def background():
    if not current_user.is_admin:
        return render_template('permission_denied.html', message=None, title='权限不足')
    return render_template('background.html', title='后台管理')


@app.route('/user_list', methods=['GET'])
@login_required
def user_list():
    if not current_user.is_admin:
        return render_template('permission_denied.html', message=None, title='权限不足')
    users = User.query.all()
    lis = list()
    for u in users:
        lis.append((u.id, u.name, u.is_admin, u.last_seen if u.last_seen else None))

    return render_template('user_list.html', title='用户列表', lis=lis)


@app.route('/user_detail/<id>', methods=['GET'])
@login_required
def user_detail(id):
    if not current_user.is_admin:
        return render_template('permission_denied.html', message=None, title='权限不足')
    u = User.query.get(id)
    dic = {
        'id': u.id,
        'name': u.name,
        'is_admin': u.is_admin,
        'can_download': u.can_download,
        'last_seen': u.last_seen if u.last_seen else None,
        'user_agent': u.user_agent,
        'user_ip': u.user_ip,
    }
    lis = list()
    for s in u.subscribing:
        lis.append({
            'book_id': s.book_id,
            'book_name': s.book_name,
            'source_id': s.source_id,
            'chapter': s.chapter,
            'chapter_name': s.chapter_name,
            'time': s.time if s.time else None
        })
    dic['subscribing'] = lis
    return render_template('user_detail.html', dic=dic, title='用户详情--%s' % u.name)


@app.route('/change_download_permission/<id>', methods=['GET'])
@login_required
def change_download_permission(id):
    if not current_user.is_admin:
        return render_template('permission_denied.html', message=None, title='权限不足')
    u = User.query.get(id)
    if u.can_download:
        u.can_download = False
    else:
        u.can_download = True
    db.session.add(u)
    db.session.commit()
    flash('修改下载权限成功！')
    return redirect(url_for('user_detail', id=id))


@app.route('/download_list', methods=['GET'])
@login_required
def download_list():
    if not current_user.is_admin:
        return render_template('permission_denied.html', message=None, title='权限不足')
    ds = Download.query.all()
    lis = list()
    path = os.path.join(Config.UPLOADS_DEFAULT_DEST, 'downloads')
    for d in ds:
        data = get_response('http://api.zhuishushenqi.com/toc/{0}?view=chapters'.format(d.source_id))
        source_name = data.get('name')
        if os.path.exists(os.path.join(path, d.txt_name)):
            txt_size = os.path.getsize(os.path.join(path, d.txt_name))
            txt_size = txt_size / float(1024 * 1024)
            txt_size = round(txt_size, 2)
        else:
            txt_size = '文件缺失'
        lis.append({
            'id': d.id,
            'user_id': d.user_id,
            'user_name': d.user.name,
            'book_name': d.book_name,
            'book_id': d.book_id,
            'chapter': d.chapter,
            'source_id': d.source_id,
            'source_name': source_name,
            'time': d.time if d.time else None,
            'txt_name': d.txt_name,
            'chapter_name': d.chapter_name,
            'txt_size': txt_size
        })
    return render_template('download_list.html', lis=lis, title='下载列表')


@app.route('/delete_download_file/<id>', methods=['GET'])
@login_required
def delete_download_file(id):
    if not current_user.is_admin:
        return render_template('permission_denied.html', message=None, title='权限不足')
    d = Download.query.get(id)

    path = os.path.join(Config.UPLOADS_DEFAULT_DEST, 'downloads')
    if os.path.exists(os.path.join(path, d.txt_name)):
        os.remove(os.path.join(path, d.txt_name))
    db.session.delete(d)
    db.session.commit()
    flash('删除下载项目成功！')
    return redirect(url_for('download_list'))


@app.route('/download_file/', methods=['GET'])
@login_required
def download_file():
    file_name = request.args.get('file_name')
    book_name = request.args.get('book_name')
    path = os.path.join(Config.UPLOADS_DEFAULT_DEST, 'downloads')
    if os.path.exists(os.path.join(path, file_name)):
        return render_template('view_documents.html', title='下载文件', url=text.url(file_name), book_title=book_name)


@app.route('/get_task_progress', methods=['POST'])
@login_required
def get_task_progress():
    ids = json.loads(request.get_data())
    lis = []
    for id in ids:
        task = Task.query.filter_by(id=id).first()
        lis.append({
            'id': task.id,
            'progress': task.get_progress()
        })
    return jsonify(lis)
