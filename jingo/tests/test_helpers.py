# -*- coding: utf-8 -*-
"""Tests for the jingo's builtin helpers."""

from __future__ import unicode_literals

from datetime import datetime
from collections import namedtuple

from django.utils import six
from jinja2 import Markup
try:
    from unittest.mock import patch
except ImportError:
    from mock import patch
from nose.tools import eq_

from jingo import helpers
from jingo import register

from .utils import htmleq_, render


def test_f():
    s = render('{{ "{0} : {z}"|f("a", z="b") }}')
    eq_(s, 'a : b')

    s = helpers.f(Markup('this is {0}'), '<b>markup</b>')
    eq_(s, 'this is <b>markup</b>')

def test_fe_helper():
    context = {'var': '<bad>'}
    template = '{{ "<em>{t}</em>"|fe(t=var) }}'
    eq_('<em>&lt;bad&gt;</em>', render(template, context))


def test_fe_positional():
    context = {'var': '<bad>'}
    template = '{{ "<em>{0}</em>"|fe(var) }}'
    eq_('<em>&lt;bad&gt;</em>', render(template, context))


def test_fe_unicode():
    context = {'var': 'Français'}
    template = '{{ "Speak {0}"|fe(var) }}'
    eq_('Speak Français', render(template, context))


def test_fe_markup():
    context = {'var': Markup('<mark>safe</mark>')}
    template = '{{ "<em>{0}</em>"|fe(var) }}'
    eq_('<em><mark>safe</mark></em>', render(template, context))
    template = '{{ "<em>{t}</em>"|fe(t=var) }}'
    eq_('<em><mark>safe</mark></em>', render(template, context))


def test_nl2br():
    text = "some\ntext\n\nwith\nnewlines"
    s = render('{{ x|nl2br }}', {'x': text})
    eq_(s, "some<br>text<br><br>with<br>newlines")

    text = None
    s = render('{{ x|nl2br }}', {'x': text})
    eq_(s, '')


def test_datetime():
    time = datetime(2009, 12, 25, 10, 11, 12)
    s = render('{{ d|datetime }}', {'d': time})
    eq_(s, 'December 25, 2009')

    s = render('{{ d|datetime("%Y-%m-%d %H:%M:%S") }}', {'d': time})
    eq_(s, '2009-12-25 10:11:12')

    s = render('{{ None|datetime }}')
    eq_(s, '')


def test_datetime_unicode():
    fmt = u"%Y 年 %m 月 %e 日"
    helpers.datetime(datetime.now(), fmt)


def test_ifeq():
    eq_context = {'a': 1, 'b': 1}
    neq_context = {'a': 1, 'b': 2}

    s = render('{{ a|ifeq(b, "<b>something</b>") }}', eq_context)
    eq_(s, '<b>something</b>')

    s = render('{{ a|ifeq(b, "<b>something</b>") }}', neq_context)
    eq_(s, '')


def test_class_selected():
    eq_context = {'a': 1, 'b': 1}
    neq_context = {'a': 1, 'b': 2}

    s = render('{{ a|class_selected(b) }}', eq_context)
    eq_(s, 'class="selected"')

    s = render('{{ a|class_selected(b) }}', neq_context)
    eq_(s, '')


def test_csrf():
    s = render('{{ csrf() }}', {'csrf_token': 'fffuuu'})
    csrf = "<input type='hidden' name='csrfmiddlewaretoken' value='fffuuu' />"
    assert csrf in s


def test_field_attrs():
    class field(object):
        def __init__(self):
            self.field = namedtuple('_', 'widget')
            self.field.widget = namedtuple('_', 'attrs')
            self.field.widget.attrs = {'class': 'foo'}

        def __str__(self):
            attrs = self.field.widget.attrs
            attr_str = ' '.join('%s="%s"' % (k, v)
                                for (k, v) in six.iteritems(attrs))
            return Markup('<input %s />' % attr_str)

        def __html__(self):
            return self.__str__()

    f = field()
    s = render('{{ field|field_attrs(class="bar",name="baz") }}',
               {'field': f})
    htmleq_(s, '<input class="bar" name="baz" />')


def test_url():
    # urls defined in jingo/tests/urls.py
    s = render('{{ url("url-args", 1, "foo") }}')
    eq_(s, "/url/1/foo/")
    s = render('{{ url("url-kwargs", word="bar", num=1) }}')
    eq_(s, "/url/1/bar/")


def url(x, *y, **z):
    return '/' + x + '!'


@patch('django.conf.settings')
def test_custom_url(s):
    # register our url method
    register.function(url)
    # re-register Jinja's
    register.function(helpers.url, override=False)

    # urls defined in jingo/tests/urls.py
    s = render('{{ url("url-args", 1, "foo") }}')
    eq_(s, "/url-args!")
    s = render('{{ url("url-kwargs", word="bar", num=1) }}')
    eq_(s, "/url-kwargs!")

    # teardown
    register.function(helpers.url, override=True)


def test_filter_override():
    def f(s):
        return s.upper()
    # See issue 7688: http://bugs.python.org/issue7688
    f.__name__ = 'a' if six.PY3 else b'a'
    register.filter(f)
    s = render('{{ s|a }}', {'s': 'Str'})
    eq_(s, 'STR')

    def g(s):
        return s.lower()
    g.__name__ = 'a' if six.PY3 else b'a'
    register.filter(override=False)(g)
    s = render('{{ s|a }}', {'s': 'Str'})
    eq_(s, 'STR')

    register.filter(g)
    s = render('{{ s|a }}', {'s': 'Str'})
    eq_(s, 'str')
