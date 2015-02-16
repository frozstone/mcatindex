import xml.dom.minidom as dom
import os, re

def cut_nomeaning_text(mml):
    target = [] # removing in for loop cause the problem that the node next to the removed node is skipped.
    for child in mml.childNodes:
        if child.nodeType == child.TEXT_NODE:
            if re.match(r'\A\s*\Z', child.data):
                target.append(child)
        else:
            cut_nomeaning_text(child)
    for child in target:
        mml.removeChild(child)
        child.unlink()
    return

def parse_file(path):
    mml_obj = dom.parse(path)
    cut_nomeaning_text(mml_obj)
    mml_obj.normalize()
    return mml_obj.getElementsByTagName('math') + mml_obj.getElementsByTagName('m:math')
