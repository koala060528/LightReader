import os


class Config(object):
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    # database config
    D_USER = 'hengli'
    D_PASSWORD = 'hengli43'
    D_HOST = '127.0.0.1'
    D_PORT = 3306
    D_DATABASE = 'novelreader'
    # sql连接字符串
    SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://%s:%s@%s:%s/%s' % (D_USER, D_PASSWORD, D_HOST, D_PORT, D_DATABASE)
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # 语言设置
    LANGUAGES = ['en-US', 'zh-CH']

    # 每页显示的blog数量
    CHAPTER_PER_PAGE = 50

    # api url
    # 书籍详情页
    BOOK_DETAIL = 'http://api.zhuishushenqi.com/book/{book_id}'
    # 章节列表
    CHAPTER_LIST = 'http://api.zhuishushenqi.com/mix-atoc/{book_id}?view=chapters'
    # 章节详情
    CHAPTER_DETAIL = 'http://chapter2.zhuishushenqi.com/chapter/{0}'

    # 文件目录
    UPLOADS_DEFAULT_DEST = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'files')
