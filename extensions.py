# este archivo existe para evitar importaciones circulares
# db vive aqui y tanto app.py como models.py lo importan desde aqui
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO

db = SQLAlchemy()
socketio = SocketIO()