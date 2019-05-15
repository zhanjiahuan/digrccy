from flask_script import Manager
from flask_migrate import MigrateCommand, Migrate

from app.digiccy_app import app
from app import db

# 创建管理工具对象
manager = Manager(app)
Migrate(app, db)
manager.add_command("db", MigrateCommand)

if __name__ == '__main__':
    manager.run()

    # python manage.py db init

    # python manage.py db migrate

    # python manage.py db upgrade
