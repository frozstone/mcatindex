#! /usr/bin/env python

from xml.dom import minidom
from ctypes import c_longlong
from mathml import cut_nomeaning_text, parse_file

def hash_leaf(mml_elem):
    # mml_elem : minidom mml element that has no children.
    # returns : hash value singleton.
    if mml_elem.nodeType == mml_elem.TEXT_NODE:
        var = hash(mml_elem.data)
    else:
        var = hash(mml_elem.localName)
    return var, []

def hash_qvar(mml_elem):
    # mml_elem : minidom mml element that tag name is qvar (defined in NTCIR11-Math nc)
    # returns : hash value singleton
    return hash(mml_elem.getAttribute('name')), []

def hash_apply(mml_elem, args):
    # mml_elem : minidom mml element object which tagName equals to "apply".
    # returns : hashed value 
    assert mml_elem.childNodes
    operator = mml_elem.firstChild
    if operator.localName == "":
        pass
    elif operator.localName == "":
        pass
    else: # unknown operator
        op_var, op_args = args[0], args[1:]
        var = c_longlong(op_var)
        op_var |= 1
        for arg in op_args:
            var = c_longlong(var.value * op_var + arg)
        return var.value
    
def hash_node(mml_elem, args):
    # mml_elem : minidom mml internal node.
    # args : hash values from children nodes.
    # returns : hashed value
    a = hash(mml_elem.localName)
    var = c_longlong(a)
    a |= 1
    for arg in args:
        var = c_longlong(var.value * a + arg)
    return var.value

def hash_recursion(mml_elem):
    # mml_elem : minidom mml element object.
    # returns : hash value set for the subtree rooted at mml_elem.
    if mml_elem.localName == "qvar" : return hash_qvar(mml_elem)
    if not mml_elem.hasChildNodes(): return hash_leaf(mml_elem)

    args, subs = [], []
    for childNode in mml_elem.childNodes:
        arg, sub = hash_recursion(childNode)
        args.append(arg)
        subs += sub
    if mml_elem.localName == "apply" : var = hash_apply(mml_elem, args)        
    else: var = hash_node(mml_elem, args)

    return var, subs + args

def hash_mml(mml):
    # mml : minidom mml object (top is m:math or math).
    # returns : hashed value set.
    cut_nomeaning_text(mml)
    if mml.nodeType == mml.DOCUMENT_NODE:
        var, res = hash_recursion(mml.documentElement)
    else:
        var, res = hash_recursion(mml)
    return res + [var]

def hash_string(string):
    mml = minidom.parseString(string)
    return hash_mml(mml)

def hash_file(path):
    # path : path to mml file.
    # returns : hashed value set.
    mml = minidom.parse(path)
    return hash_mml(mml)
