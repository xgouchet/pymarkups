# vim: ts=8:sts=8:sw=8:noexpandtab

# This file is part of python-markups module
# License: BSD
# Copyright: (C) Dmitry Shachnev, 2012-2017

import markups.common as common
from markups.abstract import AbstractMarkup, ConvertedMarkup
from distutils.version import LooseVersion
from os.path import abspath, dirname, join
from tempfile import mkdtemp
from shutil import rmtree
import warnings


class SphinxConfig(object):
	graphviz_dot = 'dot'
	graphviz_dot_args = []
	graphviz_output_format = 'svg'
	language = None


class SphinxBuilder(object):
	config = SphinxConfig()
	imagedir = "_images"

	def __init__(self):
		self.outdir = mkdtemp(prefix="pymarkups-")
		self.imgpath = join(self.outdir, self.imagedir)

	def __del__(self):
		rmtree(self.outdir)

	def warn(self, message):
		warnings.warn(message, RuntimeWarning)


class SphinxEnvironment(object):
	config = SphinxConfig()

	def __init__(self, filename):
		self._dir = abspath(dirname(filename)) if filename else None

	def relfn2path(self, filename):
		if self._dir and not filename.startswith("/"):
			return None, join(self._dir, filename)
		return None, filename

	def note_dependency(self, filename):
		pass


class ReStructuredTextMarkup(AbstractMarkup):
	"""Markup class for reStructuredText language.
	Inherits :class:`~markups.abstract.AbstractMarkup`.

	:param settings_overrides: optional dictionary of overrides for the
	                           `Docutils settings`_
	:type settings_overrides: dict

	.. _`Docutils settings`: http://docutils.sourceforge.net/docs/user/config.html
	"""
	name = 'reStructuredText'
	attributes = {
		common.LANGUAGE_HOME_PAGE: 'http://docutils.sourceforge.net/rst.html',
		common.MODULE_HOME_PAGE: 'http://docutils.sourceforge.net/',
		common.SYNTAX_DOCUMENTATION: 'http://docutils.sourceforge.net/docs/ref/rst/restructuredtext.html'
	}

	file_extensions = ('.rst', '.rest')
	default_extension = '.rst'

	@staticmethod
	def available():
		try:
			import docutils
		except ImportError:
			return False
		return LooseVersion(docutils.__version__) >= LooseVersion('0.13')

	def __init__(self, filename=None, settings_overrides=None):
		self.overrides = settings_overrides or {}
		self.overrides.update({
			'math_output': 'MathJax %s?config=TeX-AMS_CHTML' % common.MATHJAX_WEB_URL,
			'syntax_highlight': 'short',
		})
		AbstractMarkup.__init__(self, filename)
		from docutils.core import Publisher
		from docutils.io import StringInput, StringOutput
		self._publisher = Publisher(source_class=StringInput,
                                    destination_class=StringOutput)
		self._publisher.set_components('standalone', 'restructuredtext', 'html')
		self._publisher.process_programmatic_settings(None, self.overrides, None)
		self._register_sphinx_directives()

	def _register_sphinx_directives(self):
		from docutils.parsers.rst import directives
		from docutils.writers._html_base import HTMLTranslator
		from docutils.frontend import Values

		try:
			from sphinx.ext.graphviz import Graphviz, GraphvizSimple, html_visit_graphviz
		except ImportError:
			pass
		else:
			directives.register_directive('graphviz', Graphviz)
			directives.register_directive('graph', GraphvizSimple)
			directives.register_directive('digraph', GraphvizSimple)
			class SphinxTranslator(self._publisher.writer.translator_class):
				visit_graphviz = html_visit_graphviz
				builder = SphinxBuilder()
			self._publisher.writer.translator_class = SphinxTranslator
			Values.env = SphinxEnvironment(self.filename)

	def convert(self, text):
		self._publisher.set_source(text, source_path=self.filename)
		output = self._publisher.publish()
		parts = self._publisher.writer.parts

		# Determine head
		head = parts['head']

		# Determine body
		body = parts['html_body']

		# Determine title
		title = parts['title']

		# Determine stylesheet
		origstyle = parts['stylesheet']
		# Cut off <style> and </style> tags
		stylestart = '<style type="text/css">'
		stylesheet = ''
		if stylestart in origstyle:
			stylesheet = origstyle[origstyle.find(stylestart)+25:origstyle.rfind('</style>')]
		stylesheet += common.get_pygments_stylesheet('.code')

		return ConvertedReStructuredText(head, body, title, stylesheet)


class ConvertedReStructuredText(ConvertedMarkup):

	def __init__(self, head, body, title, stylesheet):
		ConvertedMarkup.__init__(self, body, title, stylesheet)
		self.head = head

	def get_javascript(self, webenv=False):
		if 'MathJax.js?config=TeX-AMS_CHTML' not in self.head:
			return ''
		return ('<script type="text/javascript" src="%s?config=TeX-AMS_CHTML"></script>\n' %
		        common.get_mathjax_url(webenv))
