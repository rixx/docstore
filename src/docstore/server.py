import collections
import datetime
import functools
import os
from urllib.parse import parse_qsl, urlparse, urlencode

from flask import Flask, render_template, request, send_from_directory
from werkzeug.middleware.profiler import ProfilerMiddleware

from docstore.files import read_documents


def create_app(root):
    app = Flask(__name__)
    app.jinja_env.trim_blocks = True
    app.jinja_env.lstrip_blocks = True

    @app.route("/")
    def list_documents():
        request_tags = set(request.args.getlist("tag"))
        documents = [
            doc for doc in read_documents(root) if request_tags.issubset(set(doc.tags))
        ]

        tag_tally = collections.Counter()
        for doc in documents:
            for t in doc.tags:
                tag_tally[t] += 1

        try:
            page = int(request.args["page"])
        except KeyError:
            page = 1

        html = render_template(
            "index.html",
            documents=sorted(documents, key=lambda d: d.date_saved, reverse=True),
            request_tags=request_tags,
            query_string=tuple(parse_qsl(urlparse(request.url).query)),
            tag_tally=tag_tally,
            page=page,
        )

        return html

    @app.route("/thumbnails/<shard>/<filename>")
    def thumbnails(shard, filename):
        return send_from_directory(
            os.path.abspath(os.path.join(root, "thumbnails", shard)), filename=filename
        )

    @app.route("/files/<shard>/<filename>")
    def files(shard, filename):
        return send_from_directory(
            os.path.abspath(os.path.join(root, "files", shard)), filename=filename
        )

    @app.template_filter("attrib_tags")
    def attrib_tags(document):
        return [t for t in document.tags if t.startswith("by:")]

    @app.template_filter("display_tags")
    def display_tags(document):
        return sorted(t for t in document.tags if not t.startswith("by:"))

    @app.template_filter("add_tag")
    @functools.lru_cache()
    def add_tag(query_string, tag):
        return "?" + urlencode(
            [(k, v) for k, v in query_string if k != "page"] + [("tag", tag)]
        )

    @app.template_filter("remove_tag")
    def remove_tag(query_string, tag):
        return "?" + urlencode(
            [(k, v) for k, v in query_string if (k, v) != ("tag", tag)]
        )

    @app.template_filter("set_page")
    @functools.lru_cache()
    def set_page(query_string, page):
        pageless_qs = [(k, v) for k, v in query_string if k != "page"]
        if page == 1:
            return "?" + urlencode(pageless_qs)
        else:
            return "?" + urlencode(pageless_qs + [("page", page)])

    @app.template_filter("hostname")
    def hostname(url):
        return url.split("/")[2]

    @app.template_filter("pretty_date")
    def pretty_date(d):
        delta = datetime.datetime.now() - d
        if delta.seconds < 120:
            return "just now"
        elif delta.seconds < 60 * 60:
            return f"{int(delta.seconds / 60)} minutes ago"
        elif d.date() == datetime.date.today():
            return "earlier today"
        elif d.date() == datetime.date.today() - datetime.timedelta(days=1):
            return "yesterday"
        elif delta.days < 7:
            return f"{delta.days} days ago"
        else:
            return d.strftime("%-d %b %Y")

    return app


def run_profiler(*, root, host, port):
    app = create_app(root)
    app.config["PROFILE"] = True
    app.wsgi_app = ProfilerMiddleware(app.wsgi_app, restrictions=[30])
    app.run(host=host, port=port, debug=True)


def run_server(*, root, host, port, debug):
    app = create_app(root)
    app.run(host=host, port=port, debug=debug)
