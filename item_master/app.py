from flask import Flask
from config import Config
from flask_session import Session
from src.routes import app_routes
from src.pharma import pharma_routes 
 
app = Flask(__name__)
 
app.config.from_object(Config)

# Session config
app.secret_key = 'your_secret_key'  # Required for sessions to work!
app.config['SESSION_TYPE'] = 'filesystem'  # Or use 'redis', 'mongodb', etc.
Session(app)

app.register_blueprint(app_routes)
app.register_blueprint(pharma_routes, url_prefix='/pharma')


if __name__ == '__main__':
    # print(app.url_map)
    app.run(debug=True)
