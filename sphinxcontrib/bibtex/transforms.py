"""
    New Doctree Transforms
    ~~~~~~~~~~~~~~~~~~~~~~

    .. autoclass:: BibliographyTransform

        .. automethod:: apply
"""

import copy
import docutils.nodes
import docutils.transforms

from pybtex.backends.doctree import Backend as output_backend
from pybtex.plugin import find_plugin

from sphinxcontrib.bibtex.nodes import bibliography

def node_text_transform(node, transform):
    """Apply transformation to all Text nodes within node."""
    for child in node.children:
        if isinstance(child, docutils.nodes.Text):
            node.replace(child, transform(child))
        else:
            node_text_transform(child, transform)

def transform_curly_bracket_strip(textnode):
    """Strip curly brackets from text."""
    text = textnode.astext()
    if '{' in text or '}' in text:
        text = text.replace('{', '').replace('}', '')
        return docutils.nodes.Text(text)
    else:
        return textnode

def transform_url_command(textnode):
    """Convert '\url{...}' into a proper docutils hyperlink."""
    text = textnode.astext()
    if '\url' in text:
        text1, _, text = text.partition('\url')
        text2, _, text3 = text.partition('}')
        text2 = text2.lstrip(' {')
        ref = docutils.nodes.reference(refuri=text2)
        ref += docutils.nodes.Text(text2)
        node = docutils.nodes.inline()
        node += transform_url_command(docutils.nodes.Text(text1))
        node += ref
        node += transform_url_command(docutils.nodes.Text(text3))
        return node
    else:
        return textnode

class BibliographyTransform(docutils.transforms.Transform):
    """Transform each
    :class:`~sphinxcontrib.bibtex.nodes.bibliography` node into a list
    of citations.
    """

    # transform must be applied before references are resolved
    default_priority = 10

    def apply(self):
        env = self.document.settings.env
        for bibnode in self.document.traverse(bibliography):
            # get the information of this bibliography node
            # by looking up its id in the bibliography cache
            id_ = bibnode['ids'][0]
            info = [info for other_id, info
                    in env.bibtex_cache.bibliographies.iteritems()
                    if other_id == id_][0]
            # generate entries
            entries = []
            for bibfile in info.bibfiles:
                # XXX entries are modified below in an unpickable way
                # XXX so fetch a deep copy
                data = env.bibtex_cache.bibfiles[bibfile].data
                entries += copy.deepcopy(list(data.entries.itervalues()))
            # locate and instantiate style plugin
            style_cls = find_plugin(
                'pybtex.style.formatting', info.style)
            style = style_cls()
            # create citation nodes for all references
            nodes = docutils.nodes.paragraph()
            backend = output_backend()
            # XXX style.format_entries modifies entries in unpickable way
            for entry in style.format_entries(entries):
                citation = backend.citation(entry, self.document)
                node_text_transform(citation, transform_url_command)
                if info.curly_bracket_strip:
                    node_text_transform(citation, transform_curly_bracket_strip)
                nodes += citation
            bibnode.replace_self(nodes)
