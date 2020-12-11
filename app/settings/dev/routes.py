from flask import request, abort, redirect, render_template
from psycopg2 import sql
import os
import json
from pathlib import Path

from app.utilities import get_default_language
from app.utilities.db_connection import db_connection
from app.authorization.authorize import authorize_web, authorize_rest

from app.post.post_types import PostTypes
from app.post.posts_generator import PostsGenerator

from app.settings.dev import dev_settings


@dev_settings.route("/settings/dev")
@authorize_web(1)
@db_connection
def show_dev_settings(*args, permission_level, connection, **kwargs):
    if connection is None:
        return redirect("/database-error")

    post_types = PostTypes()
    post_types_result = post_types.get_post_type_list(connection)

    default_language = get_default_language(connection=connection)
    connection.close()

    if os.environ["FLASK_ENV"] != "development":
        return render_template("dev-settings-prod.html",
                               post_types=post_types_result,
                               permission_level=permission_level,
                               default_lang=default_language
                               )

    return render_template("dev-settings.html",
                           post_types=post_types_result,
                           permission_level=permission_level,
                           default_lang=default_language
                           )