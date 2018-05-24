import os


class Config(object):
    SECRET_KEY=os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    # database config
    D_USER='hengli'
    D_PASSWORD='hengli43'
    D_HOST='127.0.0.1'
    D_PORT=3306
    D_DATABASE='novelreader'
    # sql连接字符串
    SQLALCHEMY_DATABASE_URI='mysql+pymysql://%s:%s@%s:%s/%s' % (D_USER, D_PASSWORD, D_HOST, D_PORT, D_DATABASE)
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # email config
    MAIL_SERVER=os.environ.get('MAIL_SERVER') or 'smtp.googlemail.com'
    MAIL_PORT=int(os.environ.get('MAIL_PORT') or 587)
    MAIL_USE_TLS=os.environ.get('MAIL_USE_TLS') is not None or 1
    MAIL_USERNAME=os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD=os.environ.get('MAIL_PASSWORD')
    ADMINS=['srt060528@gmail.com']

    # 语言设置
    LANGUAGES=['en-US','zh-CH']

    # 每页显示的blog数量
    CHAPTER_PER_PAGE=20