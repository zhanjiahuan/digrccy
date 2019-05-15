# encoding=utf8
from app.digiccy_app import app

import logging
from logging.handlers import WatchedFileHandler

import gevent.monkey

if __name__ == "__main__":
    gevent.monkey.patch_all()

    acclog = logging.getLogger('gunicorn.access')
    acclog.addHandler(WatchedFileHandler('/logs/pyservice_log/pyservice_access.log'))
    acclog.propagate = False
    errlog = logging.getLogger('gunicorn.error')
    errlog.addHandler(WatchedFileHandler('/logs/pyservice_log/pyservice_error.log'))
    errlog.propagate = False

    print(app.config)
    app.run()
