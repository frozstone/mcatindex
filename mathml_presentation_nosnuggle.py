import re
import io
#from xml.dom import minidom, Node
from lxml import etree, objectify
from collections import OrderedDict
import requests, json

'''
<math><semantics><mrow><mrow><msubsup><mo>&Sigma;</mo><mrow><mi>i</mi><mo>=</mo><mn>0</mn></mrow><mi>n</mi></msubsup></mrow><msub><mi>a</mi><mi>i</mi></msub></mrow></semantics></math>
'''

class MathMLPresentation:
    re_ns = r'<(\/?)\w+:'
    re_ns_replace = r'<\\1'
    re_node_text = r'\s'
    SEPARATOR = '#'
    url = ''
    parser = etree.XMLParser(remove_blank_text=True, encoding='UTF-8')
    transform = None
    xslt_raw = '''<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
    <xsl:output method="xml" indent="no"/>
    <xsl:template match="/|comment()|processing-instruction()">
        <xsl:copy>
          <xsl:apply-templates/>
        </xsl:copy>
    </xsl:template>
    <xsl:template match="*">
        <xsl:element name="{local-name()}">
          <xsl:apply-templates select="@*|node()"/>
        </xsl:element>
    </xsl:template>
    <xsl:template match="@*">
        <xsl:attribute name="{local-name()}">
          <xsl:value-of select="."/>
        </xsl:attribute>
    </xsl:template>
    </xsl:stylesheet>
    ''' 
    def __init__(self,url):
        self.url = url + '/upconvert/upconvert'    
        xslt_doc = etree.parse(io.BytesIO(self.xslt_raw))
        self.transform = etree.XSLT(xslt_doc)

    def __removeNodes(self, doc, tag):
        delnodes = doc.findall(".//" + tag)
        for delnode in delnodes:
            delnode.getparent().remove(delnode)

    def __make_proper_mathml(self, query):
        #remove any namespance
        query_wo_ns = re.sub(self.re_ns, self.re_ns_replace, query)
        #add xmlns (snuggle does not like it is there is not one)
        doc = etree.fromstring(query_wo_ns, self.parser)
        objectify.deannotate(doc, cleanup_namespaces=True)
        doc.attrib['xmlns'] = 'http://www.w3.org/1998/Math/MathML'
        self.__removeNodes(doc, 'script')
        return etree.tostring(doc)

    def __get_enriched_mathml(self,mathml):
        response = requests.post(self.url, {"q": mathml})
        return response.status_code, response.text.encode('utf-8') 

    def get_doc_with_orig(self, string):
        mathml = self.__make_proper_mathml(string)
#        status_code, emathml = self.__get_enriched_mathml(mathml) # get_enriched_mathml
#        doc = ''
#        if status_code == 200:
#            doc = etree.fromstring(emathml, self.parser)
#        else:
#            doc = etree.fromstring(mathml, self.parser)

        doc = etree.fromstring(mathml, self.parser)
        doc = self.transform(doc)
        objectify.deannotate(doc, cleanup_namespaces=True)
        self.__removeNodes(doc, 'annotation-xml')
        self.__removeNodes(doc, 'annotation')
 
        semantics = doc
        if semantics.find('semantics') is None:
            return None, mathml, ''

        while semantics.find("semantics") is not None:
            semantics = semantics.find("semantics")

        if len(semantics) > 0:
            return semantics[0], mathml, etree.tostring(doc)
        else:
            return None, mathml, ''
        #return semantics, mathml

    def __get_ordered_paths_and_name_inner(self, parent, query, sisters, was_wrapper=False):
        #if parent.nodeType == Node.TEXT_NODE: return [], ''
        name = parent.tag
        text = parent.text and re.sub(self.re_node_text, '_', parent.text.strip())
        if (name == 'mstyle' and len(parent) == 1):
            return self.__get_ordered_paths_and_name_inner(parent[0], query, sisters, was_wrapper)
        wrapper = (name == 'mrow' or name == 'mfenced' or name == 'math') and len(parent) == 1

        wrapped_wrapper = wrapper and was_wrapper
        if (name == 'mi' and text == u'\u25EF') or (name == 'mo' and text == u'\u25FB'):
            curpath = '*'
            curlist = [curpath]
        elif name == 'mrow' or name == 'mfenced' or name == 'math':
            curpath = name
            curlist = []
        else:
            curpath = name
            text = parent.text and parent.text.strip()
            if len(parent) == 0 and text:
                curpath += self.SEPARATOR + text
            curlist = [] if wrapped_wrapper else [curpath]
        lst = [curlist]
        cursisters = []

        i = 0
        for child in parent:
            if not(child.tag == 'mo' and child.text and child.text.strip() == u'\u2062'):
                sublist, subname = self.__get_ordered_paths_and_name_inner(child, query, sisters, wrapper)
                if subname and subname not in ['', 'mrow', 'mfenced', 'math']:
                    cursisters.append(subname)
                i += 1
                if not query: lst.extend(sublist)
                curlist.extend(map(lambda paths: paths if wrapped_wrapper else str(i) + self.SEPARATOR + paths, sublist[0]))
        #if len(cursisters) > 0: sisters.append(self.__uniqList(cursisters))
        if len(cursisters) > 0: sisters.append(cursisters)
        return lst, curpath

    def get_ordered_paths_and_sisters(self, root, query):
        sisters = []
        opaths = self.__get_ordered_paths_and_name_inner(root, query, sisters)[0]
        opaths = map(lambda paths: paths[1:] if len(paths) > 0 and (paths[0] == 'mrow' or paths[0] == 'math') else paths, opaths)
        opaths = [paths for paths in opaths if len(paths) > 0]
        #return opaths, self.__uniqListOfList(sisters)
        return opaths, sisters

    def get_unordered_paths(self, ordered_paths):
        #return self.__uniqListOfList(map(lambda paths: self.__uniqList(map(lambda path: re.sub(r'\d+(%s)' % self.SEPARATOR, r'\1', path), paths)), ordered_paths))
        return map(lambda paths: map(lambda path: re.sub(r'\d+(%s)' % self.SEPARATOR, r'\1', path), paths), ordered_paths)



