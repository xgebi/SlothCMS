from flask import request, abort, redirect, render_template, make_response
from psycopg2 import sql
import os
import json
from pathlib import Path

from app.post.post_generator import PostGenerator
from app.utilities.db_connection import db_connection
from app.authorization.authorize import authorize_web, authorize_rest
from app.toes.toes import render_toe_from_path
from app.toes.hooks import Hooks

from app.post.post_types import PostTypes

from app.settings import settings
from app.utilities import get_default_language, get_languages


@settings.route("/settings")
@authorize_web(1)
@db_connection
def show_settings(*args, permission_level, connection, **kwargs):
    if connection is None:
        return redirect("/database-error")

    post_types = PostTypes()
    post_types_result = post_types.get_post_type_list(connection)

    cur = connection.cursor()

    raw_items = []
    try:
        cur.execute(
            """SELECT settings_name, display_name, settings_value, settings_value_type FROM sloth_settings 
            WHERE settings_type = 'sloth'"""
        )
        raw_items = cur.fetchall()
    except Exception as e:
        print("db error")
        abort(500)

    cur.close()
    default_language = get_default_language(connection=connection)
    languages = get_languages(connection=connection)
    connection.close()

    items = []
    for item in raw_items:
        formatted_item = {
            "settings_name": item[0],
            "display_name": item[1],
            "settings_value": item[2],
            "settings_value_type": item[3],
            "possible_values": []
        }
        if item[0] == 'main_language':
            formatted_item["possible_values"] = languages
        items.append(formatted_item)

    return render_toe_from_path(
        path_to_templates=os.path.join(os.getcwd(), 'app', 'templates'),
        template="settings.toe.html",
        data={
            "title": "Settings",
            "post_types": post_types_result,
            "permission_level": permission_level,
            "default_lang": default_language,
            "settings": items
        },
        hooks=Hooks()
    )


@settings.route("/settings/save", methods=["POST"])
@authorize_web(1)
@db_connection
def save_settings(*args, permission_level, connection, **kwargs):
    if connection is None:
        return redirect("/settings?error=db")
    filled = request.form

    cur = connection.cursor()

    for key in filled.keys():
        try:
            cur.execute(
                sql.SQL("UPDATE sloth_settings SET settings_value = %s WHERE settings_name = %s"),
                [filled[key], key]
            )
            connection.commit()
        except Exception as e:
            print("db error")
            abort(500)

    cur.close()

    generator = PostGenerator()
    if generator.run(everything=True):
        return redirect("/settings")
    return redirect("/settings?error=generating")


@settings.route("/api/settings/generation-lock", methods=["DELETE"])
@authorize_rest(1)
def clear_content(*args, **kwargs):
    if Path(os.path.join(os.getcwd(), 'generating.lock')).is_file():
        os.remove(Path(os.path.join(os.getcwd(), 'generating.lock')))

    response = make_response(json.dumps({"post_generation": "unlocked"}))
    response.headers['Content-Type'] = 'application/json'
    code = 204

    return response, code
