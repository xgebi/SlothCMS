from flask import request, flash, url_for, current_app, abort, redirect, render_template
import json
import psycopg2
from psycopg2 import sql, errors
import uuid
from time import time
import os
import traceback
import re

from app.authorization.authorize import authorize_web
import datetime

from app.post.post_types import PostTypes
from app.authorization.authorize import authorize_rest
from app.utilities.db_connection import db_connection
from app.post.posts_generator import PostsGenerator
from app.post.post_generator_2 import PostGenerator as PostGenerator2

from app.post import post

reserved_folder_names = ('tag', 'category')


# WEB
@post.route("/post/<post_type>")
@authorize_web(0)
@db_connection
def show_posts_list(*args, permission_level, connection, post_type, **kwargs):
    if connection is None:
        return redirect("/database-error")
    post_type_info = {
        "uuid": post_type
    }

    post_types = PostTypes()
    post_types_result = post_types.get_post_type_list(connection)

    cur = connection.cursor()

    raw_items = []
    # uuid, post_type, title, publish_date, update_date, post_status, categories, deleted
    try:
        cur.execute(
            sql.SQL("SELECT display_name FROM sloth_post_types WHERE uuid = %s"), [post_type]
        )

        post_type_info["name"] = cur.fetchall()[0][0]
        cur.execute(
            sql.SQL("""SELECT A.uuid, A.title, A.publish_date, A.update_date, A.post_status, B.display_name 
            FROM sloth_posts AS A INNER JOIN sloth_users AS B ON A.author = B.uuid 
            WHERE A.post_type = %s ORDER BY  A.update_date DESC"""),
            [post_type]
        )
        raw_items = cur.fetchall()
    except Exception as e:
        print("db error Q")
        abort(500)

    cur.close()
    connection.close()

    items = []
    for item in raw_items:
        items.append({
            "uuid": item[0],
            "title": item[1],
            "publish_date":
                datetime.datetime.fromtimestamp(float(item[2]) / 1000.0).strftime("%Y-%m-%d") if item[
                                                                                                     2] is not None else "",
            "update_date":
                datetime.datetime.fromtimestamp(float(item[3]) / 1000.0).strftime("%Y-%m-%d") if item[
                                                                                                     3] is not None else "",
            "status": item[4],
            "author": item[5]
        })

    return render_template("post-list.html",
                           post_types=post_types_result,
                           permission_level=permission_level,
                           post_list=items,
                           post_type=post_type_info,
                           )


@post.route("/post/<post_id>/edit")
@authorize_web(0)
@db_connection
def show_post_edit(*args, permission_level, connection, post_id, **kwargs):
    post_types = PostTypes()
    post_types_result = post_types.get_post_type_list(connection)

    cur = connection.cursor()
    media = []
    post_type_name = ""
    raw_post = {}
    raw_tags = []
    raw_post_categories = []
    raw_all_categories = []
    temp_thumbnail_info = []
    try:
        cur.execute(
            sql.SQL("SELECT uuid, file_path, alt FROM sloth_media")
        )
        media = cur.fetchall()

        cur.execute(
            sql.SQL("""SELECT A.title, A.slug, A.content, A.excerpt, A.css, A.use_theme_css, A.js, A.use_theme_js, A.thumbnail, 
            A.publish_date, A.update_date, A.post_status, B.display_name, A.post_type, A.imported, A.import_approved,
            A.password
                    FROM sloth_posts AS A INNER JOIN sloth_users AS B ON A.author = B.uuid WHERE A.uuid = %s"""),
            [post_id]
        )
        raw_post = cur.fetchone()
        cur.execute(
            sql.SQL("SELECT display_name FROM sloth_post_types WHERE uuid = %s"),
            [raw_post[13]]
        )
        post_type_name = cur.fetchone()[0]
        gen = PostsGenerator(connection=connection)
        taxonomies = gen.get_taxonomy_for_post(post_id)

        cur.execute(
            sql.SQL("""SELECT uuid, display_name FROM sloth_taxonomy
                                WHERE post_type = %s AND taxonomy_type=%s"""),
            [raw_post[13], 'category']
        )
        raw_all_categories = cur.fetchall()
        cur.execute(
            sql.SQL("SELECT unnest(enum_range(NULL::sloth_post_status))")
        )
        temp_post_statuses = cur.fetchall()
        if raw_post[8] is not None:
            cur.execute(
                sql.SQL("""SELECT alt, 
                        concat((SELECT settings_value FROM sloth_settings WHERE settings_name = 'site_url'), '/',file_path)
                        FROM sloth_media WHERE uuid=%s"""),
                [raw_post[8]]
            )
            temp_thumbnail_info = cur.fetchone()

    except Exception as e:
        print("db error B")
        print(e)
        abort(500)

    cur.close()
    connection.close()

    token = request.cookies.get('sloth_session')

    post_categories = [cat["uuid"] for cat in taxonomies["categories"]]

    all_categories = []
    for category in raw_all_categories:
        selected = False
        if category[0] in post_categories:
            selected = True
        all_categories.append({
            "uuid": category[0],
            "display_name": category[1],
            "selected": selected
        })

    publish_datetime = datetime.datetime.fromtimestamp(raw_post[9] / 1000) if raw_post[9] else None

    data = {
        "uuid": post_id,
        "title": raw_post[0],
        "slug": raw_post[1],
        "content": raw_post[2],
        "excerpt": raw_post[3],
        "css": raw_post[4],
        "use_theme_css": raw_post[5],
        "js": raw_post[6],
        "use_theme_js": raw_post[7],
        "thumbnail_path": temp_thumbnail_info[1] if len(temp_thumbnail_info) >= 2 else None,
        "thumbnail_uuid": raw_post[8] if raw_post[8] is not None else "",
        "thumbnail_alt": temp_thumbnail_info[0] if len(temp_thumbnail_info) > 0 else None,
        "publish_date": publish_datetime.strftime("%Y-%m-%d") if publish_datetime else None,
        "publish_time": publish_datetime.strftime("%H:%M") if publish_datetime else None,
        "update_date": raw_post[10],
        "status": raw_post[11],
        "display_name": raw_post[12],
        "post_categories": taxonomies["categories"],
        "all_categories": all_categories,
        "tags": [tag["display_name"] for tag in taxonomies["tags"]],
        "post_type": raw_post[13],
        "imported": raw_post[14],
        "approved": raw_post[15],
        "password": raw_post[16]
    }

    return render_template(
        "post-edit.html",
        post_types=post_types_result,
        permission_level=permission_level,
        token=token,
        post_type_name=post_type_name,
        data=data,
        media=media,
        all_categories=all_categories,
        post_statuses=[item for sublist in temp_post_statuses for item in sublist]
    )


@post.route("/post/<post_type>/new")
@authorize_web(0)
@db_connection
def show_post_new(*args, permission_level, connection, post_type, **kwargs):
    post_types = PostTypes()
    post_types_result = post_types.get_post_type_list(connection)

    cur = connection.cursor()
    media = []
    temp_post_statuses = []
    post_type_name = ""
    raw_all_categories = []
    try:

        cur.execute(
            sql.SQL("SELECT uuid, file_path, alt FROM sloth_media")
        )
        media = cur.fetchall()
        cur.execute(
            sql.SQL("SELECT display_name FROM sloth_post_types WHERE uuid = %s"),
            [post_type]
        )
        post_type_name = cur.fetchone()[0]
        cur.execute(
            sql.SQL("SELECT unnest(enum_range(NULL::sloth_post_status))")
        )
        temp_post_statuses = cur.fetchall()
        cur.execute(
            sql.SQL(
                "SELECT uuid, display_name FROM sloth_taxonomy WHERE taxonomy_type = 'category' AND post_type = %s;"),
            [post_type]
        )
        raw_all_categories = cur.fetchall()
    except Exception as e:
        print("db error A")
        abort(500)

    cur.close()
    connection.close()

    post_statuses = [item for sublist in temp_post_statuses for item in sublist]

    all_categories = []
    for category in raw_all_categories:
        selected = False
        all_categories.append({
            "uuid": category[0],
            "display_name": category[1],
            "selected": selected
        })

    data = {
        "new": True,
        "use_theme_js": True,
        "use_theme_css": True,
        "status": "draft",
        "uuid": uuid.uuid4(),
        "post_type": post_type
    }

    return render_template("post-edit.html", post_types=post_types_result, permission_level=permission_level,
                           media=media, post_type_name=post_type_name, post_statuses=post_statuses,
                           data=data, all_categories=all_categories)


@post.route("/post/<type_id>/taxonomy")
@authorize_web(0)
@db_connection
def show_post_taxonomy(*args, permission_level, connection, type_id, **kwargs):
    post_types = PostTypes()
    post_types_result = post_types.get_post_type_list(connection)

    cur = connection.cursor()
    taxonomy = {}
    try:
        cur.execute(
            sql.SQL("SELECT unnest(enum_range(NULL::sloth_taxonomy_type))")
        )
        taxonomy_types = [item for sublist in cur.fetchall() for item in sublist]
        for taxonomy_type in taxonomy_types:
            cur.execute(
                sql.SQL("""SELECT uuid, display_name 
                FROM sloth_taxonomy WHERE post_type = %s AND taxonomy_type = %s"""),
                [type_id, taxonomy_type]
            )
            taxonomy[taxonomy_type] = cur.fetchall()
    except Exception as e:
        import pdb;
        pdb.set_trace()
        print("db error C")
        abort(500)

    cur.close()
    connection.close()

    return render_template(
        "taxonomy-list.html",
        post_types=post_types_result,
        permission_level=permission_level,
        taxonomy_types=taxonomy_types,
        taxonomy_list=taxonomy,
        post_uuid=type_id
    )


@post.route("/post/<type_id>/taxonomy/<taxonomy_type>/<taxonomy_id>", methods=["GET"])
@authorize_web(0)
@db_connection
def show_post_taxonomy_item(*args, permission_level, connection, type_id, taxonomy_id, taxonomy_type, **kwargs):
    post_types = PostTypes()
    post_types_result = post_types.get_post_type_list(connection)

    cur = connection.cursor()
    temp_taxonomy = []
    try:
        cur.execute(
            sql.SQL("""SELECT slug, display_name 
            FROM sloth_taxonomy WHERE post_type = %s AND uuid = %s"""),
            [type_id, taxonomy_id]
        )
        temp_taxonomy = cur.fetchone()
    except Exception as e:
        import pdb;
        pdb.set_trace()
        print("db error C")
        abort(500)

    cur.close()
    connection.close()

    taxonomy = {
        "uuid": taxonomy_id,
        "post_uuid": type_id,
        "slug": temp_taxonomy[0],
        "display_name": temp_taxonomy[1]
    }

    return render_template(
        "taxonomy.html",
        post_types=post_types_result,
        permission_level=permission_level,
        taxonomy=taxonomy,
        taxonomy_type=taxonomy_type
    )


@post.route("/post/<type_id>/taxonomy/<taxonomy_type>/<taxonomy_id>", methods=["POST", "PUT"])
@authorize_web(0)
@db_connection
def save_post_taxonomy_item(*args, permission_level, connection, type_id, taxonomy_id, taxonomy_type, **kwargs):
    cur = connection.cursor()
    filled = request.form

    if filled["slug"] or filled["display_name"]:
        redirect(f"/post/{type_id}/taxonomy/{taxonomy_id}?error=missing_data")
    try:
        cur.execute(
            sql.SQL("SELECT display_name FROM sloth_taxonomy WHERE uuid = %s;"),
            [taxonomy_id]
        )
        res = cur.fetchall()
        if len(res) == 0:
            cur.execute(sql.SQL("""INSERT INTO sloth_taxonomy (uuid, slug, display_name, post_type, taxonomy_type) 
            VALUES (%s, %s, %s, %s, %s);"""),
                        [taxonomy_id, filled["slug"], filled["display_name"], type_id, taxonomy_type])
        else:
            cur.execute(sql.SQL("""UPDATE sloth_taxonomy SET slug = %s, display_name = %s WHERE uuid = %s;"""),
                        [filled["slug"], filled["display_name"], taxonomy_id])
        connection.commit()
    except Exception as e:
        return redirect(f"/post/{type_id}/taxonomy/{taxonomy_type}/{taxonomy_id}?error=db")
    cur.close()
    connection.close()
    return redirect(f"/post/{type_id}/taxonomy/{taxonomy_type}/{taxonomy_id}")


@post.route("/post/<type_id>/taxonomy/<taxonomy_type>/new")
@authorize_web(0)
@db_connection
def create_taxonomy_item(*args, permission_level, connection, type_id, taxonomy_type, **kwargs):
    post_types = PostTypes()
    post_types_result = post_types.get_post_type_list(connection)

    connection.close()

    taxonomy = {
        "uuid": uuid.uuid4(),
        "post_uuid": type_id
    }

    return render_template(
        "taxonomy.html",
        post_types=post_types_result,
        permission_level=permission_level,
        taxonomy=taxonomy,
        taxonomy_type=taxonomy_type,
        new=True
    )


# API
@post.route("/api/post/media", methods=["GET"])
@authorize_rest(0)
@db_connection
def get_media_data(*args, connection, **kwargs):
    if connection is None:
        abort(500)

    cur = connection.cursor()
    raw_media = []
    site_url = ""
    try:

        cur.execute(
            sql.SQL("SELECT uuid, file_path, alt FROM sloth_media")
        )
        raw_media = cur.fetchall()
        cur.execute(
            sql.SQL("SELECT settings_value FROM sloth_settings WHERE settings_name = 'site_url'")
        )
        site_url = cur.fetchone()
        site_url = site_url[0] if len(site_url) > 0 else ""
    except Exception as e:
        print("db error")
        abort(500)

    cur.close()
    connection.close()

    media = []
    for medium in raw_media:
        media.append({
            "uuid": medium[0],
            "filePath": f"{site_url}/{medium[1]}",
            "alt": medium[2]
        })

    return json.dumps({"media": media})


@post.route("/api/post/upload-file", methods=['POST'])
@authorize_rest(0)
@db_connection
def upload_image(*args, file_name, connection=None, **kwargs):
    ext = file_name[file_name.rfind("."):]
    if not ext.lower() in (".png", ".jpg", ".jpeg", ".svg", ".bmp", ".tiff"):
        abort(500)
    with open(os.path.join(current_app.config["OUTPUT_PATH"], "sloth-content", file_name), 'wb') as f:
        f.write(request.data)

    file = {}
    cur = connection.cursor()

    try:

        cur.execute(
            sql.SQL("INSERT INTO sloth_media VALUES (%s, %s, %s, %s) RETURNING uuid, file_path, alt"),
            [str(uuid.uuid4()), os.path.join("sloth-content", file_name), "", ""]
        )
        file = cur.fetchone()
        cur.close()
    except Exception as e:
        print(traceback.format_exc())
        connection.close()
        abort(500)

    cur.close()
    connection.close()

    return json.dumps({"media": file}), 201


@post.route("/api/post", methods=['POST'])
@authorize_rest(0)
@db_connection
def save_post(*args, connection=None, **kwargs):
    if connection is None:
        abort(500)
    result = {}
    filled = json.loads(request.data)
    filled["thumbnail"] = filled["thumbnail"] if len(filled["thumbnail"]) > 0 else None
    cur = connection.cursor()
    try:
        # process tags
        cur.execute(
            sql.SQL("SELECT uuid, slug, display_name, post_type, taxonomy_type "
                    "FROM sloth_taxonomy WHERE post_type = %s AND taxonomy_type = 'tag';"),
            [filled["post_type_uuid"]]
        )
        existing_tags = cur.fetchall()
        trimmed_tags = [tag.strip() for tag in filled["tags"].split(",")]
        matched_tags = [tag[0] for tag in existing_tags if tag[2] in trimmed_tags]
        new_tags = [tag for tag in trimmed_tags if tag not in
                    [existing_tag[2] for existing_tag in existing_tags]]
        if len(new_tags) > 0:
            for new_tag in new_tags:
                if len(new_tag) == 0:
                    continue
                slug = re.sub("\s+", "-", new_tag.strip())
                new_uuid = str(uuid.uuid4())
                try:
                    cur.execute(
                        sql.SQL("""INSERT INTO sloth_taxonomy (uuid, slug, display_name, post_type, taxonomy_type) 
                                    VALUES (%s, %s, %s, %s, 'tag');"""),
                        [new_uuid, slug, new_tag, filled["post_type_uuid"]]
                    )
                    matched_tags.append(new_uuid)
                except Exception as e:
                    print(e)
            connection.commit()
        # get user
        author = request.headers.get('authorization').split(":")[1]
        publish_date = -1
        if filled["post_status"] == 'published' and filled["publish_date"] is None:
            publish_date = str(time() * 1000)
        elif filled["post_status"] == 'scheduled':
            publish_date = filled["publish_date"]  # TODO scheduling
        else:
            publish_date = None
        # save post
        if filled["new"]:
            unique_post = False
            while filled["new"] and not unique_post:
                cur.execute(
                    sql.SQL("SELECT count(uuid) FROM sloth_posts WHERE uuid = %s"),
                    [filled["uuid"]]
                )
                if cur.fetchone()[0] != 0:
                    filled["uuid"] = str(uuid.uuid4())
                else:
                    unique_post = True

            cur.execute(
                sql.SQL("SELECT count(slug) FROM sloth_posts WHERE slug LIKE %s OR slug LIKE %s AND post_type=%s;"),
                [f"{filled['slug']}-%", f"{filled['slug']}%", filled["post_type_uuid"]]
            )
            similar = cur.fetchone()[0]
            if int(similar) > 0:
                filled['slug'] = f"{filled['slug']}-{str(int(similar) + 1)}"

            cur.execute(
                sql.SQL("""INSERT INTO sloth_posts (uuid, slug, post_type, author, 
                title, content, excerpt, css, js, thumbnail, publish_date, update_date, post_status, lang, password) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'en', %s)"""),
                [filled["uuid"], filled["slug"], filled["post_type_uuid"], author, filled["title"], filled["content"],
                 filled["excerpt"], filled["css"], filled["js"], filled["thumbnail"], publish_date, str(time() * 1000),
                 filled["post_status"], filled["password"]]
            )
            connection.commit()
            for category in filled["categories"]:
                cur.execute(
                    sql.SQL("""INSERT INTO sloth_post_taxonomies (uuid, post, taxonomy) VALUES (%s, %s, %s)"""),
                    [str(uuid.uuid4()), filled["uuid"], category]
                )
            for tag in matched_tags:
                cur.execute(
                    sql.SQL("""INSERT INTO sloth_post_taxonomies (uuid, post, taxonomy) VALUES (%s, %s, %s)"""),
                    [str(uuid.uuid4()), filled["uuid"], tag]
                )
            result["uuid"] = filled["uuid"]
        else:
            cur.execute(
                sql.SQL("""UPDATE sloth_posts SET slug = %s, title = %s, content = %s, excerpt = %s, css = %s, js = %s,
                 thumbnail = %s, publish_date = %s, update_date = %s, post_status = %s, import_approved = %s,
                 password = %s WHERE uuid = %s;"""),
                [filled["slug"], filled["title"], filled["content"], filled["excerpt"], filled["css"], filled["js"],
                 filled["thumbnail"] if filled["thumbnail"] != "None" else None,
                 filled["publish_date"] if filled["publish_date"] is not None else publish_date,
                 str(time() * 1000), filled["post_status"], filled["approved"],
                 filled["password"] if "password" in filled else None, filled["uuid"]]
            )
            connection.commit()
            cur.execute(
                sql.SQL("""DELETE FROM sloth_post_taxonomies WHERE post = %s;"""),
                [filled["uuid"]]
            )
            for category in filled["categories"]:
                cur.execute(
                    sql.SQL("""INSERT INTO sloth_post_taxonomies (uuid, post, taxonomy) VALUES (%s, %s, %s)"""),
                    [str(uuid.uuid4()), filled["uuid"], category]
                )
            for tag in matched_tags:
                cur.execute(
                    sql.SQL("""INSERT INTO sloth_post_taxonomies (uuid, post, taxonomy) VALUES (%s, %s, %s)"""),
                    [str(uuid.uuid4()), filled["uuid"], tag]
                )
        connection.commit()

        cur.execute(
            sql.SQL("""SELECT A.uuid, A.original_lang_entry_uuid, A.lang, A.slug, A.post_type, A.author, A.title, A.content, 
                                A.excerpt, A.css, A.use_theme_css, A.js, A.use_theme_js, A.thumbnail, A.publish_date, A.update_date, 
                                A.post_status, A.imported, A.import_approved FROM sloth_posts as A WHERE A.uuid = %s;"""),
            [filled["uuid"]]
        )
        generatable_post_raw = cur.fetchone()
        generatable_post = {
            "uuid": generatable_post_raw[0],
            "original_lang_entry_uuid": generatable_post_raw[1],
            "lang": generatable_post_raw[2],
            "slug": generatable_post_raw[3],
            "post_type": generatable_post_raw[4],
            "author": generatable_post_raw[5],
            "title": generatable_post_raw[6],
            "content": generatable_post_raw[7],
            "excerpt": generatable_post_raw[8],
            "css": generatable_post_raw[9],
            "use_theme_css": generatable_post_raw[10],
            "js": generatable_post_raw[11],
            "use_theme_js": generatable_post_raw[12],
            "thumbnail": generatable_post_raw[13],
            "publish_date": generatable_post_raw[14],
            "publish_date_formatted": datetime.datetime.fromtimestamp(float(generatable_post_raw[14]) / 1000).strftime(
                "%Y-%m-%d %H:%M") if generatable_post_raw[14] is not None else None,
            "update_date": generatable_post_raw[15],
            "update_date_formatted": datetime.datetime.fromtimestamp(float(generatable_post_raw[15]) / 1000).strftime(
                "%Y-%m-%d %H:%M") if generatable_post_raw[15] is not None else None,
            "post_status": generatable_post_raw[16],
            "imported": generatable_post_raw[17],
            "approved": generatable_post_raw[18]
        }

        # get post
        if filled["post_status"] == 'published':
            gen = PostsGenerator(connection=connection)
            taxonomies = gen.get_taxonomy_for_post(generatable_post_raw[0])
            gen.run(post=generatable_post)

        if filled["post_status"] == 'protected':
            # get post type slug
            cur.execute(
                sql.SQL("""SELECT slug FROM sloth_post_types WHERE uuid = %s;"""),
                [generatable_post["post_type"]]
            )
            post_type_slug = cur.fetchone()
            # get post slug
            gen = PostsGenerator()
            gen.delete_post_files(post_type=post_type_slug[0], post=generatable_post["slug"])
    except Exception as e:
        return json.dumps({"error": str(e)}), 500

    cur.close()

    result["saved"] = True
    return json.dumps(result)


@post.route("/api/post/delete", methods=['POST', 'DELETE'])
@authorize_rest(0)
@db_connection
def delete_post(*args, permission_level, connection, **kwargs):
    if connection is None:
        abort(500)

    filled = json.loads(request.data)

    cur = connection.cursor()
    res = {}
    count = []
    try:
        cur.execute(
            sql.SQL("""SELECT A.post_type, A.slug, spt.slug 
            FROM sloth_posts as A INNER JOIN sloth_post_types spt on A.post_type = spt.uuid WHERE A.uuid = %s"""),
            [filled["post"]]
        )
        res = cur.fetchone()
        cur.execute(
            sql.SQL("DELETE FROM sloth_posts WHERE uuid = %s"),
            [filled["post"]]
        )
        connection.commit()
        cur.execute(
            sql.SQL("SELECT COUNT(uuid) FROM sloth_posts")
        )
        count = cur.fetchone()
    except Exception as e:
        abort(500)
    cur.close()
    gen = PostsGenerator(connection=connection)
    if count[0] == 0:
        gen.delete_post_type_post_files({"slug": res[2]})
    else:
        gen.delete_post_files({"slug": res[2]}, {"slug": res[1]})
        gen.run(post_type=res[2])

    return json.dumps(res[0])


@post.route("/api/post/taxonomy/<taxonomy_id>", methods=["DELETE"])
@authorize_rest(0)
@db_connection
def delete_taxonomy(*args, permission_level, connection, taxonomy_id, **kwargs):
    if connection is None:
        abort(500)

    cur = connection.cursor()

    try:
        cur.execute(
            sql.SQL("DELETE FROM sloth_taxonomy WHERE uuid = %s;"),
            [taxonomy_id]
        )
        connection.commit()
    except Exception as e:
        return json.dumps({"error": "db"})
    cur.close()
    connection.close()
    return json.dumps({"deleted": True})


@post.route("/api/post/regenerate-all", methods=["POST", "PUT"])
@authorize_rest(0)
@db_connection
def regenerate_all(*args, permission_level, connection, **kwargs):
    if connection is None:
        abort(500)

    gen = PostsGenerator(connection=connection)
    gen.run(posts=True)

    return json.dumps({"generating": True})


@post.route("/api/post/secret", methods=["POST"])
@db_connection
def get_protected_post(*args, connection, **kwargs):
    filled = json.loads(request.data)

    raw_post = []

    try:
        cur = connection.cursor()
        cur.execute(
            sql.SQL("""SELECT uuid 
            FROM sloth_posts WHERE password = %s AND slug = %s;"""),
            [filled["password"], filled["slug"]]
        )
        raw_post = cur.fetchone()
    except Exception as e:
        print(e)

    if len(raw_post) != 1:
        return json.dumps({"unauthorized": True}), 401

    gen = PostGenerator2(connection=connection)
    protected_post = gen.get_protected_post(uuid=raw_post[0])

    if type(protected_post) is str:
        return json.dumps({
            "content": protected_post
        }), 200
    else:
        return json.dumps(protected_post), 200
