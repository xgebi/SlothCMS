from psycopg2 import sql
from typing import Tuple, List, Dict, Any
import datetime
import sys

from app.utilities.utility_exceptions import NoPositiveMinimumException


def get_languages(*args, connection, lang_id: str = "", as_list:bool= True, **kwargs) \
        -> Tuple[Dict[str, Any], List[Dict[str, Any]]] or List[Dict[str, Any]]:
    cur = connection.cursor()
    temp_languages = []
    try:
        cur.execute(
            sql.SQL("""SELECT uuid, long_name, short_name FROM sloth_language_settings""")
        )
        temp_languages = cur.fetchall()
    except Exception as e:
        print(e)
        return ()

    if len(lang_id) != 0:
        languages = [{
            "uuid": lang[0],
            "long_name": lang[1],
            "short_name": lang[2]
        } for lang in temp_languages if lang[0] != lang_id]
        current_lang = [{
            "uuid": lang[0],
            "long_name": lang[1],
            "short_name": lang[2]
        } for lang in temp_languages if lang[0] == lang_id][0]

        return current_lang, languages
    if as_list:
        return [{
            "uuid": lang[0],
            "long_name": lang[1],
            "short_name": lang[2]
        } for lang in temp_languages]
    return {lang[0]: {
        "uuid": lang[0],
        "long_name": lang[1],
        "short_name": lang[2]
    } for lang in temp_languages}


def get_default_language(*args, connection, **kwargs) -> Dict[str, str]:
    cur = connection.cursor()
    try:
        cur.execute(
            sql.SQL("""SELECT uuid, long_name FROM sloth_language_settings 
            WHERE uuid = (SELECT settings_value FROM sloth_settings WHERE settings_name = 'main_language')""")
        )
        main_language = cur.fetchone()
    except Exception as e:
        print(e)
        return {}

    return {
        "uuid": main_language[0],
        "long_name": main_language[1]
    }


def get_related_posts(*args, post, connection, **kwargs):
    cur = connection.cursor()
    if post["original_lang_entry_uuid"] is not None and len(post["original_lang_entry_uuid"]) > 0:
        cur.execute(
            sql.SQL(
                """SELECT A.uuid, A.original_lang_entry_uuid, A.lang, A.slug, A.post_type, A.author, A.title,
                 A.css, A.use_theme_css, A.js, A.use_theme_js, A.thumbnail, A.publish_date, 
                 A.update_date, A.post_status, A.imported, A.import_approved FROM sloth_posts as A 
                 WHERE A.uuid = %s OR (A.original_lang_entry_uuid = %s AND A.uuid <> %s);"""),
            (post["original_lang_entry_uuid"], post["original_lang_entry_uuid"],
             post["uuid"])
        )
    else:
        cur.execute(
            sql.SQL(
                """SELECT A.uuid, A.original_lang_entry_uuid, A.lang, A.slug, A.post_type, A.author, A.title, 
                A.css, A.use_theme_css, A.js, A.use_theme_js, A.thumbnail, A.publish_date, 
                A.update_date, A.post_status, A.imported, A.import_approved FROM sloth_posts as A 
                WHERE A.original_lang_entry_uuid = %s;"""),
            (post["uuid"],)
        )
    related_posts_raw = cur.fetchall()
    posts = []
    for related_post in related_posts_raw:
        cur.execute(
            sql.SQL(
                """SELECT content, section_type, position
                FROM sloth_post_sections
                WHERE post = %s
                ORDER BY position ASC;"""
            ),
            (related_post[0],)
        )
        sections = [{
            "content": section[0],
            "type": section[1],
            "position": section[2]
        } for section in cur.fetchall()]
        parse_raw_post(related_post, sections=sections)

    for post in posts:
        cur.execute(
            sql.SQL(
                """SELECT sl.location, spl.hook_name
                FROM sloth_post_libraries AS spl
                INNER JOIN sloth_libraries sl on sl.uuid = spl.library
                WHERE spl.post = %s;"""
            ),
            (post["uuid"],)
        )
        post["libraries"] = [{
            "location": lib[0],
            "hook_name": lib[1]
        } for lib in cur.fetchall()]
    cur.close()
    return posts


def parse_raw_post(raw_post, sections) -> Dict[str, str] or Any:
    result = {
        "uuid": raw_post[0],
        "original_lang_entry_uuid": raw_post[1],
        "lang": raw_post[2],
        "slug": raw_post[3],
        "post_type": raw_post[4],
        "author": raw_post[5],
        "title": raw_post[6],
        "css": raw_post[7],
        "use_theme_css": raw_post[8],
        "js": raw_post[9],
        "use_theme_js": raw_post[10],
        "thumbnail": raw_post[11],
        "publish_date": raw_post[12],
        "publish_date_formatted": datetime.datetime.fromtimestamp(float(raw_post[12]) / 1000).strftime(
            "%Y-%m-%d %H:%M") if raw_post[12] is not None else None,
        "update_date": raw_post[13],
        "update_date_formatted": datetime.datetime.fromtimestamp(float(raw_post[13]) / 1000).strftime(
            "%Y-%m-%d %H:%M") if raw_post[13] is not None else None,
        "post_status": raw_post[14],
        "imported": raw_post[15],
        "approved": raw_post[16],
        "meta_description": raw_post[17] if len(raw_post) >= 18 and raw_post[17] is not None and len(raw_post[17]) > 0 else sections[0]["content"][:161 if len(sections[0]) > 161 else len(sections[0]["content"])],
        "social_description": raw_post[18] if len(raw_post) >= 19 and raw_post[18] is not None and len(raw_post[18]) > 0 else sections[0]["content"][:161 if len(sections[0]) > 161 else len(sections[0]["content"])],
        "format_uuid": raw_post[19] if len(raw_post) >= 20 and raw_post[19] is not None else None,
        "format_slug": raw_post[20] if len(raw_post) >= 21 and raw_post[20] is not None else None,
        "format_name": raw_post[21] if len(raw_post) >= 22 and raw_post[21] is not None else None,
        "sections": sections
    }

    return result


def positive_min(*args, floats: bool = False):
    if floats:
        args = [float(arg) for arg in args if arg >= 0]
    else:
        args = [int(arg) for arg in args if arg >= 0]
    positive_minimum = sys.maxsize
    pm_change = False
    for arg in args:
        if arg < positive_minimum:
            pm_change = True
            positive_minimum = arg
    if not pm_change:
        raise NoPositiveMinimumException()
    return positive_minimum
