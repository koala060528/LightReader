from app import app, db
from rq import get_current_job
from app.models import Task, Download, User
from app.routes import get_response, get_text, reg_biquge
import os
from config import Config
from hashlib import md5
from datetime import datetime
from flask_login import current_user

app.app_context().push()


def _set_task_progress(progress):
    job = get_current_job()
    if job:
        job.meta['progress'] = progress
        job.save_meta()
        task = Task.query.get(job.get_id())
        # task.user.add_notification('task_progress', {'task_id': job.get_id(), 'progress': progress})

        if progress >= 100:
            task.complete = True

        db.session.commit()


def download(user_id, source_id, book_id):
    try:
        d = Download.query.filter_by(book_id=book_id, source_id=source_id).first()
        # 这里必须使用id查询user而不能直接使用current_user
        u = User.query.get(user_id)

        # 获取章节信息
        data = get_response('http://api.zhuishushenqi.com/toc/{0}?view=chapters'.format(source_id))
        path = os.path.join(Config.UPLOADS_DEFAULT_DEST, 'downloads')
        if not os.path.exists(path):
            os.makedirs(path)

        # 定义文件名
        fileName = md5((book_id + source_id).encode("utf8")).hexdigest()[:10] + '.txt'
        # fileName = os.path.join(path, book_title + '.txt')
        # if os.path.exists(fileName):
        #     os.remove(fileName)

        chapter_list = data.get('chapters')
        if d:
            # 截取需要下载的章节列表
            new = False
            download_list = chapter_list[d.chapter + 1:]
            book_title = d.book_name
            d.chapter = len(chapter_list) - 1
            d.time = datetime.utcnow()
            d.lock = True  # 给下载加锁
            d.chapter_name = chapter_list[len(chapter_list) - 1].get('title')
        else:
            new = True
            # 获取书籍简介
            data1 = get_response('http://api.zhuishushenqi.com/book/' + book_id)
            book_title = data1.get('title')
            author = data1.get('author')
            longIntro = data1.get('longIntro')
            download_list = chapter_list

            d = Download(user=u, book_id=book_id, source_id=source_id, chapter=len(chapter_list) - 1,
                         book_name=book_title, time=datetime.utcnow(), txt_name=fileName, lock=True,
                         chapter_name=chapter_list[-1].get('title'))
        db.session.add(d)
        db.session.commit()

        with open(os.path.join(path, fileName), 'a', encoding='utf-8') as f:
            _set_task_progress(0)
            i = 0
            if new:
                f.writelines(
                    ['    ', book_title, '\n', '\n', '    ', author, '\n', '\n', '    ', longIntro, '\n', '\n'])
            for chapter in download_list:
                title = chapter.get('title')
                url = chapter.get('link')
                # 为各个源添加特殊处理
                if data['source'] == 'biquge':
                    url = reg_biquge(data['link'], url)

                li = get_text(url)
                f.writelines(['\n', '    ', title, '\n', '\n'])
                for sentence in li:
                    f.writelines(['    ', sentence, '\n', '\n'])
                i += 1
                _set_task_progress(100 * i // len(download_list))
        d.lock = False  # 给下载解锁
        db.session.add(d)
        db.session.commit()
    except Exception as e:
        print(e)
