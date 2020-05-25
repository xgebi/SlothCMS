from flask import request, flash, url_for, current_app, abort, redirect, render_template
from app.utilities.db_connection import db_connection
from app.authorization.authorize import authorize_web
from app.posts.post_types import PostTypes
import psycopg2
from psycopg2 import sql
import datetime

from app.web.messages import messages

@messages.route("/messages")
@authorize_web(0)
@db_connection
def show_message_list(*args, permission_level, connection, **kwargs):
	if connection is None:
		return render_toe(template="settings.toe", path_to_templates=current_app.config["TEMPLATES_PATH"], data={ "error": "No connection to database" })

	postTypes = PostTypes()
	postTypesResult = postTypes.get_post_type_list(connection)

	cur = connection.cursor()

	raw_messages = []
	try:
		cur.execute(
			sql.SQL("SELECT uuid, name, sent_date, status FROM sloth_messages WHERE status != 'deleted' ORDER BY sent_date DESC LIMIT 10")
		)
		raw_messages = cur.fetchall()
	except Exception as e:
		print("db error")
		abort(500)

	cur.close()
	connection.close()

	messages = []
	for message in raw_messages:
		messages.append({
			"uuid": message[0],
			"name": message[1],
			"sent_date": datetime.datetime.fromtimestamp(float(message[2])/1000.0).strftime("%Y-%m-%d"),
			"status": message[3]
		})

	return render_template("message-list.html", post_types=postTypesResult, permission_level=permission_level, messages=messages)

@messages.route("/messages/<msg>")
@authorize_web(0)
@db_connection
def show_message(*args, permission_level, connection, msg, **kwargs):
	if connection is None:
		return render_toe(template="settings.toe", path_to_templates=current_app.config["TEMPLATES_PATH"], data={ "error": "No connection to database" })

	postTypes = PostTypes()
	postTypesResult = postTypes.get_post_type_list(connection)

	cur = connection.cursor()

	raw_items = []
	try:
		cur.execute(
			sql.SQL("SELECT name, sent_date, status, body FROM sloth_messages WHERE uuid = %"), [msg]
		)
		raw_messages = cur.fetchone()
	except Exception as e:
		print("db error")
		abort(500)

	cur.close()
	connection.close()
	import pdb; pdb.set_trace()
	messages = []
	for message in raw_items:
		messages.append({
			"name": message[0],
			"sent_date": datetime.datetime.fromtimestamp(float(message[1])/1000.0).strftime("%Y-%m-%d"),
			"status": message[2],
			"body": message[3]
		})

	return render_template("message.html", post_types=postTypesResult, permission_level=permission_level, messages=messages)