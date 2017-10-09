# -*- coding: utf-8 -*-
# vim: sw=4 ts=4 fenc=utf-8
# =============================================================================
# $Id: __init__.py 235 2007-07-20 15:23:26Z palgarvio $
# =============================================================================
#             $URL: http://svn.edgewall.org/repos/babel/contrib/GladeBabelExtractor/babelglade/__init__.py $
# $LastChangedDate: 2007-07-20 16:23:26 +0100 (Fri, 20 Jul 2007) $
#             $Rev: 235 $
#   $LastChangedBy: palgarvio $
# =============================================================================
# Copyright (C) 2006 Ufsoft.org - Pedro Algarvio <ufs@ufsoft.org>
#
# Please view LICENSE for additional licensing information.
# =============================================================================
from __future__ import unicode_literals

from xml.parsers import expat


class GladeParser(object):
    def __init__(self, source):
        self.source = source

        parser = expat.ParserCreate("utf-8")
        parser.buffer_text = True
        parser.ordered_attributes = True
        parser.StartElementHandler = self._handle_start
        parser.EndElementHandler = self._handle_end
        parser.CharacterDataHandler = self._handle_data

        if not hasattr(parser, 'CurrentLineNumber'):
            self._getpos = self._getpos_unknown

        self.expat = parser
        self._queue = []
        self._comments = []
        self._translate = False
        self._data = []

    def parse(self):
        try:
            bufsize = 4 * 1024 # 4K
            done = False
            while not done and len(self._queue) == 0:
                data = self.source.read(bufsize)
                if data == b'':  # end of data
                    if hasattr(self, 'expat'):
                        self.expat.Parse('', True)
                        del self.expat # get rid of circular references
                    done = True
                else:
                    self.expat.Parse(data, False)
                for event in self._queue:
                    yield event
                self._queue = []
                if done:
                    break
        except expat.ExpatError as e:
            msg = str(e)
            raise ParseError(msg, self.filename, e.lineno, e.offset)

    def _handle_start(self, tag, attrib):
        if 'translatable' in attrib:
            if attrib[attrib.index('translatable')+1] == 'yes':
                self._translate = True
                if 'comments' in attrib:
                    self._comments.append(attrib[attrib.index('comments')+1])

    def _handle_end(self, tag):
        if self._translate is True:
            if self._data:
                self._enqueue(tag, self._data, self._comments)
            self._translate = False
            self._data = []
            self._comments = []

    def _handle_data(self, text):
        if self._translate:
            if not text.startswith('gtk-'):
                self._data.append(text)
            else:
                self._translate = False
                self._data = []
                self._comments = []

    def _enqueue(self, kind, data=None, comments=None, pos=None):
        if pos is None:
            pos = self._getpos()
        if kind == 'property':
            if '\n' in data:
                lines = data.splitlines()
                lineno = pos[0] - len(lines) + 1
                offset = -1
            else:
                lineno = pos[0]
                offset = pos[1] - len(data)
            pos = (lineno, offset)
            self._queue.append((data, comments, pos[0]))

    def _getpos(self):
        return (self.expat.CurrentLineNumber,
                self.expat.CurrentColumnNumber)
    def _getpos_unknown(self):
        return (-1, -1)

def extract_glade(fileobj, keywords, comment_tags, options):
    parser = GladeParser(fileobj)
    def get_messages():
        for message, comments, lineno in parser.parse():
            if comment_tags:
                yield (lineno, None, message, comments)
            else:
                yield (lineno, None, message, [])
    return get_messages()




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


