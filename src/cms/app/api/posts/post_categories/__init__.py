from flask import Blueprint
post_categories = Blueprint('post_categories', __name__, template_folder = 'templates')
from app.api.posts.post_categories import routes