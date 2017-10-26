from __future__ import unicode_literals

from lxml import etree


def extract_glade(fileobj, keywords, comment_tags, options):
    tree = etree.parse(fileobj)
    root = tree.getroot()
    to_translate = []
    for elem in root.iter():
        # do we need to check if the element starts with "gtk-"?
        if elem.get("translatable") == "yes":
            line_no = elem.sourceline
            func_name = None
            message = elem.text
            comment = []
            if elem.get("comments"):
                comment = [elem.get("comments")]
            to_translate.append([line_no, func_name, message, comment])
    return to_translate


# All localestrings from https://specifications.freedesktop.org/desktop-entry-spec/latest/ar01s05.html
TRANSLATABLE = (
    'Name',
    'GenericName',
    'Comment',
    'Icon',
    'Keywords',
)

def extract_desktop(fileobj, keywords, comment_tags, options):
    for lineno, line in enumerate(fileobj, 1):
        if line.startswith(b'[Desktop Entry]'):
            continue

        for t in TRANSLATABLE:
            if not line.startswith(t.encode('utf-8')):
                continue
            else:
                l = line.decode('utf-8')
                comments = []
                key_value = l.split('=', 1)
                key, value = key_value[0:2]

                funcname = key # FIXME: Why can I not assign that name to funcname?
                funcname = ''
                message = value
                comments.append(key)
                yield (lineno, funcname, message.strip(), comments)


