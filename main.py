from flask import Flask
from routes import app

application = Flask(__name__)
application.register_blueprint(app)

if __name__=='__main__':
    application.run()
