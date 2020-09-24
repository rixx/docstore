import hashlib
import os
import re
import secrets
import shutil

from unidecode import unidecode

from docstore.models import Document, File, Thumbnail, from_json, to_json
from docstore.thumbnails import create_thumbnail


_cached_documents = {
    'last_modified': None,
    'contents': None,
}

def get_documents(root):
    """
    Get a list of all the documents.
    """
    db_path = os.path.join(root, 'documents.json')

    # JSON parsing is somewhat expensive.  By caching the result rather than
    # going to disk each time, we see a ~10x speedup in returning responses
    # from the server.
    if (
        _cached_documents['last_modified'] is not None and
        os.stat(db_path).st_mtime <= _cached_documents['last_modified']
    ):
        return _cached_documents['contents']

    try:
        with open(db_path) as infile:
            result = from_json(infile.read())
    except FileNotFoundError:
        return []

    _cached_documents['last_modified'] = os.stat(db_path).st_mtime
    _cached_documents['contents'] = result

    return result



def write_documents(*, root, documents):
    db_path = os.path.join(root, 'documents.json')
    json_string = to_json(documents)
    with open(db_path, 'w') as out_file:
        out_file.write(json_string)


def slugify(u):
    """
    Convert Unicode string into blog slug.

    Based on http://www.leancrew.com/all-this/2014/10/asciifying/

    """
    u = re.sub(u'[–—/:;,._]', '-', u)   # replace separating punctuation
    a = unidecode(u).lower()            # best ASCII substitutions, lowercased
    a = re.sub(r'[^a-z0-9 -]', '', a)   # delete any other characters
    a = a.replace(' ', '-')             # spaces to hyphens
    a = re.sub(r'-+', '-', a)           # condense repeated hyphens
    return a


def _sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as infile:
        h.update(infile.read())

    return 'sha256:%s' % h.hexdigest()


def store_new_document(*, root, path, title, tags, source_url, date_saved):
    filename = os.path.basename(path)
    name, ext = os.path.splitext(filename)
    slug = slugify(name) + ext

    out_path = os.path.join('files', slug[0], slug)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    while os.path.exists(out_path):
        out_path = os.path.join(
            'files', slug[0], slugify(name) + '_' + secrets.token_hex(2) + ext
        )

    shutil.move(path, out_path)

    thumbnail_path = create_thumbnail(out_path)
    thumbnail_name = os.path.basename(thumbnail_path)
    thumb_out_path = os.path.join('thumbnails', thumbnail_name[0], thumbnail_name)
    os.makedirs(os.path.dirname(thumb_out_path), exist_ok=True)
    shutil.move(thumbnail_path, thumb_out_path)

    documents = get_documents(root)
    documents.append(
        Document(
            title=title,
            date_saved=date_saved,
            tags=tags,
            files=[
                File(
                    filename=filename,
                    path=out_path,
                    size=os.stat(out_path).st_size,
                    checksum=_sha256(out_path),
                    source_url=source_url,
                    thumbnail=Thumbnail(thumb_out_path),
                    date_saved=date_saved,
                )
            ]
        )
    )

    write_documents(root=root, documents=documents)
