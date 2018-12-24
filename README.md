# LightReader
简阅小说网

使用了追书神器API

可以订阅、换源

运行效果请访问：http://read.srtvps.top/

后台任务依赖RQ和Redis

需要先安装Redis：

sudo apt install redis-server

然后运行：

rq worker lightreader-tasks
