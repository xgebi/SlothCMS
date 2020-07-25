from flask import request, flash, url_for, current_app, abort, redirect, render_template
import psycopg2
from psycopg2 import sql
from app.utilities.db_connection import db_connection
from app.authorization.authorize import authorize_web

from app.post.post_types import PostTypes
from app.post.posts_generator import PostsGenerator

from app.web.settings import settings


@settings.route("/settings")
@authorize_web(1)
@db_connection
def show_settings(*args, permission_level, connection, **kwargs):
	if connection is None:
		return redirect("/database-error")	
	settings = {}

	post_types = PostTypes()
	post_types_result = post_types.get_post_type_list(connection)

	cur = connection.cursor()

	raw_items = []
	try:		
		cur.execute(
			"SELECT settings_name, display_name, settings_value, settings_value_type FROM sloth_settings WHERE settings_type = 'sloth'"
		)
		raw_items = cur.fetchall()
	except Exception as e:
		print("db error")
		abort(500)

	cur.close()
	connection.close()

	items = []
	for item in raw_items:
		items.append({
			"settings_name": item[0],
			"display_name": item[1],
			"settings_value": item[2],
			"settings_value_type": item[3]
		})
	
	return render_template("settings.html", post_types=post_types_result, permission_level=permission_level, settings=items)


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
	connection.close()

	generator = PostsGenerator(connection=connection)
	if generator.run(posts=True):
		return redirect("/settings")
	return redirect("/settings?error=generating")

