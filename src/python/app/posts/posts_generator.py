import psycopg2
from psycopg2 import sql, errors
from flask import current_app
from jinja2 import Template

import threading
import time
import os
from pathlib import Path

from app.utilities.db_connection import db_connection

class PostsGenerator:
	post = {}
	config = {}
	settings = {}
	is_runnable = True

	@db_connection
	def __init__(self, post, config, connection=None):
		if connection is None:
			self.is_runnable = False

		self.post = post
		self.config = config
		cur = connection.cursor()
		try:
			cur.execute(
				sql.SQL("SELECT settings_name, settings_value, settings_value_type FROM sloth_settings WHERE settings_name = %s OR settings_type = %s"), ['active_theme', 'sloth']
			)
			raw_items = cur.fetchall()
			for item in raw_items:
				self.settings[str(item[0])] = {
					"settings_name": item[0],
					"settings_value": item[1],
					"settings_value_type": item[2]
				}
		except Exception as e:
			print(e)

	def run(self):
		if not self.is_runnable:
			return
		
		t = threading.Thread(target=self.generateContent)
		t.start()

	def generateContent(self):
		self.generate_post()

		#if (self.post["tags_enabled"]):
		#	generate_tags()
		
		#if (self.post["categories_enabled"]):
		#	generate_categories()
		
		#if (self.post["archive_enabled"]):
		#	generate_archive()
		
		# regenerate home if newly published

	def generate_post(self):
		post_path_dir = Path(self.config["OUTPUT_PATH"], self.post["post_type_slug"], self.post["slug"])
		theme_path = Path(self.config["THEMES_PATH"], self.settings['active_theme']['settings_value'])

		post_template_path = Path(theme_path, "post.html")
		if (Path(theme_path, "post-" + self.post["post_type_slug"] + ".html").is_file()):
			post_template_path = Path(theme_path, "post-" + self.post["post_type_slug"] + ".html")

		template = ""
		with open(post_template_path, 'r') as f:			
			template = Template(f.read())
		
		if not os.path.exists(post_path_dir):
			os.makedirs(post_path_dir)

		with open(os.path.join(post_path_dir, 'index.html'), 'w') as f:
			f.write(template.render(post=self.post, sitename=self.settings["sitename"]["settings_value"]))

	def generate_tags(self):
		tag_template_path = Path(theme_path, "tag.html")
		if (Path(theme_path, "tag-" + self.post["post_type_slug"] + ".html").is_file()):
			tag_template_path = Path(theme_path, "tag-" + self.post["post_type_slug"] + ".html")
		elif (not tag_template_path.is_file()):
			tag_template_path = Path(theme_path, "archive.html")	

		template = ""
		with open(tag_template_path, 'w') as f:
			template = Template(f.read())

		with open(os.path.join(post_path_dir, 'index.html'), 'w') as f:
			f.write(template.render())

	def generate_categories(self):
		category_template_path = Path(theme_path, "category.html")
		if (Path(theme_path, "category-" + self.post["post_type_slug"] + ".html").is_file()):
			category_template_path = Path(theme_path, "category-" + self.post["post_type_slug"] + ".html")
		elif (not category_template_path.is_file()):
			category_template_path = Path(theme_path, "archive.html")

		template = ""
		with open(post_template_path, 'w') as f:
			template = Template(f.read())

		with open(os.path.join(post_path_dir, 'index.html'), 'w') as f:
			f.write(template.render())
	
	def generate_archive(self):
		tags_template_path = Path(theme_path, "archive.html")
		if (Path(theme_path, "archive-" + self.post["post_type_slug"] + ".html").is_file()):
			post_template_path = Path(theme_path, "archive-" + self.post["post_type_slug"] + ".html")

		template = ""
		with open(post_template_path, 'w') as f:
			template = Template(f.read())

		with open(os.path.join(post_path_dir, 'index.html'), 'w') as f:
			f.write(template.render())

		