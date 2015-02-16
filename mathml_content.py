#!/usr/bin/env python
# vim: sts=4:ts=4:sw=4
import re
from xml.dom import minidom, Node
from lxml import etree, objectify

class CErrorException(Exception):
    pass

class MathMLContent:
    parser = etree.XMLParser(remove_blank_text=True, encoding='UTF-8')
    re_node_text = r'\s'

    def __getText(self, text):
        return re.sub(self.re_node_text, '_', text)

    def __content(self, node):
        if len(node) == 0 and node.text is None:
            return [u'%s' % node.tag]
        elif len(node) == 0:
            if node.tag == u'csymbol' or node.tag == u'cerror':
                return [u'%s:%s' % (node.tag, self.__getText(node.text))]
            return [u'%s' % node.tag, u'%s' % self.__getText(node.text)]
        if node.tag == u'cerror':
            print 'error'
            raise CErrorException()
        return self.__encode_subtree(node)

    def __text_content(self, node):
        if len(node) == 0:
            if node.text:
                return u'%s:%s' % (node.tag, self.__getText(node.text))
            return u'%s' % node.tag
        return u':'.join(text_content(child) for child in node)

    def __encode_subtree(self, root):
        try:
            if root.tag == u'cerror':
                return [u'cerror'] + [self.__encode_subtree(child) for child in root]
            elif len(root) == 0:
                return self.__content(root)
            else:# root.tag == u'apply':
                if len(root) > 0 and len(root[0]) == 0:
                    return [self.__text_content(root[0])] + [self.__encode_subtree(child) for child in root[1:]]
                return [u'%s' % root.tag] + [self.__encode_subtree(child) for child in root]
        except:
            return []

    def encode_mathml_as_tree(self, string):
        doc = etree.fromstring(string, self.parser)
        cmathmls = doc.findall(u'.//annotation-xml')
        return [self.__encode_subtree(cmathml[0]) for cmathml in cmathmls if len(cmathml) > 0], [etree.tostring(cmathml) for cmathml in cmathmls if len(cmathml) > 0]

    def encode_paths(self, tree):
        global_ooper = []
        global_oarg = []
        def encode_paths_inner(tree):
            ooper = []
            oarg = []
            #if tree[0] == u'cn' or tree[0] == 'ci': #need to extend to support nodes (besides cn and ci) that are leaves
            if len(tree) == 2 and all(type(elem) is unicode for elem in tree):
                ooper.append(tree[0])
                oarg.append(u'#'.join(tree))
            else:
                if len(tree) > 1:
                    for index, child in enumerate(tree[1:], start=1):
                        child_ooper, child_oarg = encode_paths_inner(child)
                        ooper.extend("%s#%s#%s" % (tree[0], index, e) for e in child_ooper)
                        oarg.extend("%s#%s#%s" % (tree[0], index, e) for e in child_oarg)
                else:
                    ooper.append(tree[0])
            global_ooper.extend(ooper)
            global_oarg.extend(oarg)
            return ooper, oarg

        encode_paths_inner(tree)
        return global_ooper, global_oarg

    def get_unordered_paths(self, ordered_paths):
        '''
        ordered_paths is a set : set([path1, path2])
        '''
        return map(lambda path: re.sub(r'\d+(#)', r'\1', path), list(ordered_paths))
                
"""
<annotation-xml encoding="MathML-Content" id="I1.i2.p1.1.m5.1.cmml" xref="I1.i2.p1.1.m5.1">
  <apply id="I1.i2.p1.1.m5.1.9.cmml" xref="I1.i2.p1.1.m5.1.9">
    <csymbol cd="ambiguous" id="I1.i2.p1.1.m5.1.9.1.cmml">superscript</csymbol>
    <apply id="I1.i2.p1.1.m5.1.9.2.cmml" xref="I1.i2.p1.1.m5.1.9.2">
      <minus id="I1.i2.p1.1.m5.1.4.cmml" xref="I1.i2.p1.1.m5.1.4"/>
      <apply id="I1.i2.p1.1.m5.1.9.2.1.cmml" xref="I1.i2.p1.1.m5.1.9.2.1">
        <csymbol cd="ambiguous" id="I1.i2.p1.1.m5.1.9.2.1.1.cmml">subscript</csymbol>
        <ci id="I1.i2.p1.1.m5.1.2.cmml" xref="I1.i2.p1.1.m5.1.2">t</ci>
        <ci id="I1.i2.p1.1.m5.1.3.1.cmml" xref="I1.i2.p1.1.m5.1.3.1">k</ci>
      </apply>
      <apply id="I1.i2.p1.1.m5.1.9.2.2.cmml" xref="I1.i2.p1.1.m5.1.9.2.2">
        <csymbol cd="ambiguous" id="I1.i2.p1.1.m5.1.9.2.2.1.cmml">subscript</csymbol>
        <ci id="I1.i2.p1.1.m5.1.5.cmml" xref="I1.i2.p1.1.m5.1.5">t</ci>
        <apply id="I1.i2.p1.1.m5.1.6.1.cmml" xref="I1.i2.p1.1.m5.1.6.1">
          <minus id="I1.i2.p1.1.m5.1.6.1.2.cmml" xref="I1.i2.p1.1.m5.1.6.1.2"/>
          <ci id="I1.i2.p1.1.m5.1.6.1.1.cmml" xref="I1.i2.p1.1.m5.1.6.1.1">k</ci>
          <cn id="I1.i2.p1.1.m5.1.6.1.3.cmml" type="integer" xref="I1.i2.p1.1.m5.1.6.1.3">1</cn>
        </apply>
      </apply>
    </apply>
    <ci id="I1.i2.p1.1.m5.1.8.1.cmml" xref="I1.i2.p1.1.m5.1.8.1">r</ci>
  </apply>
</annotation-xml>

\left(t_{k}-t_{k-1}\right)^{r}
[u'superscript', [u'minus', [u'subscript', [u'ci', u't'], [u'ci', u'k']], [u'subscript', [u'ci', u't'], [u'minus', [u'ci', u'k'], [u'cn', u'1']]]], [u'ci', u'r']]
"""
