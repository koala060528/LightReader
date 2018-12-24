from app import app, db
from app.models import User, Subscribe, Download, Task


@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'User': User, 'Subscribe': Subscribe, 'Download': Download, 'Task': Task}
