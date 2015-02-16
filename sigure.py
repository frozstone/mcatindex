#! /usr/bin/env python

from xml.dom import minidom
from ctypes import c_longlong
from mathml import cut_nomeaning_text, parse_file

class HashResult:
    def __init__(self, value = 0, var_name = None):
        assert type(value) == int
        self.constant = value
        if var_name:
            self.coef = {var_name: 1}
            self.order = {var_name: 0}
        else:
            self.coef = dict()
            self.order = dict()

    def merge(self, a, op):
        # a must be odd
        a |= 1

        # a * self + op
        for key in self.coef:
            self.coef[key] = c_longlong(self.coef[key] * a).value
        self.constant = c_longlong(self.constant * a).value
        for key in op.coef:
            self.coef[key] = c_longlong(self.coef.get(key, 0) + op.coef[key]).value
        self.constant = c_longlong(self.constant + op.constant).value    

        # merge order
        for key in op.order:
            if key not in self.order:
                self.order[key] = len(self.order)

    def value(self):
        value = self.constant
        for key in self.coef:
            value = c_longlong(value + self.coef[key] * hash(str(self.order[key]))).value
        return value

def hash_leaf(mml_elem):
    # mml_elem : minidom mml element that has no children.
    # returns : hash value singleton.x
    if mml_elem.nodeType == mml_elem.TEXT_NODE:
        var = hash(mml_elem.data)
    else:
        var = hash(mml_elem.localName)
    return HashResult(value = var), [var]

def hash_qvar(mml_elem):
    # mml_elem : minidom mml element that tag name is qvar (defined in NTCIR11-Math nc)
    # returns : hash value singleton
    result = HashResult(var_name = mml_elem.getAttribute('name'))
    return result, [result.value()]

def hash_mi(mml_elem):
    # mml_elem : minidom mml element that tag name is mi or ci.
    # returns : hash value singleton
    if len(mml_elem.childNodes) == 0 or mml_elem.firstChild.nodeType != mml_elem.TEXT_NODE:
        var_name = ""
    else:
        var_name = mml_elem.firstChild.data
    result = HashResult(var_name = var_name)
    return result, [result.value()]

def hash_apply(mml_elem, args):
    # mml_elem : minidom mml element object which tagName equals to "apply".
    # returns : hashed value 
    assert mml_elem.childNodes
    operator = mml_elem.firstChild

    op_var, op_args = args[0].value(), args[1:]
    result = args[0]
    result.constant = op_var
    result.coef = dict()
    for arg in op_args:
        result.merge(op_var, arg)
    return result
    
def hash_node(mml_elem, args):
    # mml_elem : minidom mml internal node.
    # args : hash values from children nodes.
    # returns : hashed value
    a, b = c_longlong(hash(mml_elem.localName[0::2])).value, c_longlong(hash(mml_elem.localName[1::2])).value
    result = HashResult(value = b)
    for arg in args:
        result.merge(a, arg)
    return result

def hash_recursion(mml_elem):
    # mml_elem : minidom mml element object.
    # returns : hash value set for the subtree rooted at mml_elem.
    if mml_elem.localName == "qvar" : return hash_qvar(mml_elem)
    if mml_elem.localName in ["mi", "ci"] : return hash_mi(mml_elem)
    if not mml_elem.hasChildNodes(): return hash_leaf(mml_elem)

    args, subs = [], []
    for childNode in mml_elem.childNodes:
        arg, sub = hash_recursion(childNode)
        args.append(arg)
        subs += sub
    if mml_elem.localName == "apply" : result = hash_apply(mml_elem, args)        
    else: result = hash_node(mml_elem, args)

    return result, subs + [result.value()]

def hash_mml(mml):
    # mml : minidom mml object (top is m:math or math).
    # returns : hashed value set.
    cut_nomeaning_text(mml)
    if mml.nodeType == mml.DOCUMENT_NODE:
        mml_top = mml.documentElement
    else:
        mml_top = mml
    unify = dict()
    var, res = hash_recursion(mml_top)
    return res

def hash_string(string):
    mml = minidom.parseString(string)
    return hash_mml(mml)

def hash_file(path):
    # path : path to mml file.
    # returns : hashed value set.
    mml = minidom.parse(path)
    return hash_mml(mml)
