import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev_key')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'postgresql+psycopg2://gen_user:z%5C(%5EP1CAc%5Cyg3L@77.232.135.72:5432/default_db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
