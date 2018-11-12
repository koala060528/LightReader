import os


class Config(object):
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    # database config
    D_USER = os.environ.get('D_USER') or 'hengli'
    D_PASSWORD = os.environ.get('D_PASSWORD') or 'hengli43'
    D_HOST = '127.0.0.1'
    D_PORT = 3306
    D_DATABASE = 'lightreader'
    # sql连接字符串
    SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://%s:%s@%s:%s/%s' % (D_USER, D_PASSWORD, D_HOST, D_PORT, D_DATABASE)
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # redis设置
    REDIS_URL = os.environ.get('REDIS_URL') or 'redis://'

    # 语言设置
    LANGUAGES = ['zh-CN']

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