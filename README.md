# NovelReader
基于python-flask实现的一个小说阅读网站

运行效果请访问：http://read.srtvps.top/

由于后台任务使用了Python-RQ，所以不支持在Windows平台上部署，如果强行部署在Windows平台，将会出现无法下载小说的问题。

在Linux上部署时，请进虚拟环境之后在终端上运行：

rq worker novelreader-tasks
