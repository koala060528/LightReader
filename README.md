# LightReader
## 简阅小说网

使用了追书神器API

可以订阅、换源

后台任务依赖RQ和Redis

需要先安装Redis：

sudo apt install redis-server

然后运行：

rq worker lightreader-tasks

因追书神器停更所有起点系小说，简阅受到波及，暂时停止更新和维护，恢复时间未知
