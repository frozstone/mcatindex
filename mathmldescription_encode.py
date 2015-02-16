#location will be in pymathcat
from mathml_presentation_nosnuggle import MathMLPresentation
from mathml_content import MathMLContent, CErrorException
import subtree, sigure, modular
from os import listdir, path
from sys import argv
import re
import solr

kmcsregex = r'(__(?:PRE|CODE|SPAN|FIGURE|TABLE|DIV|MATH)_\d+__)'
mathDir = '../mathmlandextra/math_new/'
mathadjDir = '../mathmlandextra/math_adj/'
featureDir = '../features/feats/'
tagDir = '../features/tags/'
sentDir = '../splitted/multifiles/' #'maths/sentence'

def getCleanSentence(sentence):
    ms = re.findall(kmcsregex, sentence)
    for m in ms: 
        sentence = sentence.replace(m, '')
    return sentence, ms

def getUnicodeText(string):
    if type(string) is str:
        return string.decode('utf-8')
    else:
        return string

def getDep(filename):
    '''
    input: file in math_adj
    use new heuristics, no need to take the longest first
    '''
    adj = {} #{mathid: [child1, child2]}
    for ln in open(filename).readlines():
        midparent, midchildren = ln.strip().split('\t')
        mids = midchildren.split(' ')
        for idx in reversed(range(len(mids))):
            if 'xhtml' not in mids[idx]:
                mids[idx - 1] += ' %s' % mids[idx]
                del mids[idx]
        adj[midparent] = mids
    return adj

def extractDescription(featurepaper, tagpaper):
    '''
    input: tags/6/0812.0981 and features/6/0812.0981
    Paraname + kmcs-id is enough to be the key, since sentence for extractoion replace XML elements with kmcs-id
    return dictionary which its key is mathID triple and its value is description
    '''
    desc = {} #{(para, kmcsid): [desc1, desc2]}
    for fl in listdir(tagpaper):
        taglns = open(path.join(tagpaper, fl)).readlines()
        fetlns = open(path.join(featurepaper, fl).replace('arff', 'txt')).readlines()
        for idx, ln in enumerate(taglns):
            if ln.startswith('True'):
               fetcells = fetlns[idx].strip().split('\t')
               description = getUnicodeText(getCleanSentence(' '.join(fetcells[1:]))[0])
               if (fl, fetcells[0]) in desc:
                   desc[(fl.replace('arff', 'txt'), fetcells[0])].append(description)
               else:
                   desc[(fl.replace('arff', 'txt'), fetcells[0])] = [description]
    #get unique value, overlap will be considered as unique
    for k in desc.iterkeys():
        desc[k] = list(set(desc[k]))
    return desc

def extractContext(sentencepaper):
    '''
    input: splitted/multifiles/6/0812.0981
    return dictionary which its key is mathID triple and its value is context
    '''
    context = {}
    for fl in listdir(sentencepaper):
        lns = open(path.join(sentencepaper, fl)).readlines()
        for ln in lns:
            cleansent, matches = getCleanSentence(ln.strip())
            for m in matches:
                if (fl, m) in context: print 'double kmcs-id'
                context[(fl, m)] = getUnicodeText(cleansent)
    return context
    

def encodePresentation(procPres, mathml):
    semantics, mts_string, mts_presentation = procPres.get_doc_with_orig(mathml)
    opaths = []
    upaths = []
    sisters = []
    subhash = []
    sighash = []
    modhash = []
    if semantics is not None:
        opaths, sisters = procPres.get_ordered_paths_and_sisters(semantics, False)
        upaths = map(lambda paths: ' '.join(map(getUnicodeText, paths)), procPres.get_unordered_paths(opaths))
        sisters = map(lambda family: ' '.join(map(getUnicodeText, family)), sisters)
        opaths = map(lambda paths: ' '.join(map(getUnicodeText, paths)), opaths) 
        subhash = subtree.hash_string(mts_presentation)
        sighash = sigure.hash_string(mts_presentation)
        modhash = modular.hash_string_generator(2 ** 32)(mts_presentation)
    return opaths, upaths, sisters, subhash, sighash, modhash

def encodeContent(procCont, mathml):
    oopers = []
    oargs = []
    uopers = []
    uargs = []
    trees, cmathmls_str = procCont.encode_mathml_as_tree(mathml)
    for tree in trees:
        ooper, oarg = procCont.encode_paths(tree)
        uoper = procCont.get_unordered_paths(ooper)
        uarg = procCont.get_unordered_paths(oarg)
        oopers.extend(map(getUnicodeText, ooper))
        oargs.extend(map(getUnicodeText, oarg))
        uopers.extend(map(getUnicodeText, uoper))
        uargs.extend(map(getUnicodeText, uarg))
    subhash = []
    sighash = []
    modhash = []
    for cmathml_str in cmathmls_str:
        subhash.extend(subtree.hash_string(cmathml_str))
        sighash.extend(sigure.hash_string(cmathml_str))
        modhash.extend(modular.hash_string_generator(2 ** 32)(cmathml_str))
    return oopers, oargs, uopers, uargs, subhash, sighash, modhash


def encode_file(filepath, solr):
    procPres = MathMLPresentation('http://localhost:9000')
    procCont = MathMLContent()
    '''
    input: 1/0705.0912.txt
    For each math:
    1. get the related maths by look at createNewDep return value.
    2. get its own description
    3. get its own context
    4. get its childen's description
    5. get its children's context
    6. push the data from 2, 3, 4, 5 to fields of lucene
    '''
    paperpath = filepath[:filepath.rindex('.')] # filepath: 1/0704.0097.txt --> paperpath: 1/0704.0097
    mathfl = path.join(mathDir, filepath)
    mathadjfl = path.join(mathadjDir, filepath)
    featurefl = path.join(featureDir, paperpath)
    tagfl = path.join(tagDir, paperpath)
    sentfl = path.join(sentDir, paperpath)

    adj = getDep(mathadjfl)
    contextDict = extractContext(sentfl)
    descDict = extractDescription(featurefl, tagfl)

    docs = []
    
    mathlns = open(mathfl).readlines()
    for ln in mathlns:
        cells = ln.split('\t')
        paraname = cells[1]
        parapath = path.join(paperpath, paraname)
        kmcsid = cells[2]
        latexmlid = cells[0]
        
        gmid = getUnicodeText('#'.join([parapath, kmcsid, latexmlid]))
        mid ='#'.join([paraname, kmcsid, latexmlid])
        mathml = '\t'.join(cells[3:])
        
        opaths, upaths, sisters, psubhash, psighash, pmodhash = encodePresentation(procPres, mathml)
        oopers, oargs, uopers, uargs, csubhash, csighash, cmodhash = encodeContent(procCont, mathml)

        textdictid = tuple([paraname.replace('xhtml', 'txt'), kmcsid])
        context = contextDict[textdictid] if textdictid in contextDict else '' # a string
        descs = descDict[textdictid] if textdictid in descDict else [] # a list of string

        children = adj[mid] if mid in adj else []
        context_children = [] # a list of string
        desc_children = []
        for child in children:
            paraname_child, kmcsid_child, latexmlid_child = child.split('#')
            textdictchildid = tuple([paraname_child.replace('xhtml', 'txt'), kmcsid_child])
            if textdictchildid in contextDict: context_children.append(contextDict[textdictchildid])
            if textdictchildid in descDict: desc_children.extend(descDict[textdictchildid])

        #TODO: push the gmid, math-related, and text-related data to lucene
        doc = {"gmid": gmid, 
               "gpid": parapath, 
               "mathml": mathml,
        }
        if context.strip() != '':
            doc["context_en"] = [context]
            doc["context_xhtml"] = [context]
        if len(descs) > 0:
            doc["description_en"] = descs
            doc["description_xhtml"] = descs
        if len(context_children) > 0:
            doc["context_children"] = context_children
        if len(desc_children) > 0:
            doc["description_children"] = desc_children
        if len(psubhash) > 0:
            doc["opaths"] = opaths
            doc["upaths"] = upaths
            doc["sisters"] = sisters
            doc["subtree_presentation"] = psubhash
            doc["sigure_presentation"] = psighash
            doc["modular_presentation"] = pmodhash
        if len(csubhash) > 0:
            doc["ooper"] = oopers
            doc["oarg"] = oargs
            doc["uoper"] = uopers
            doc["uarg"] = uargs
            doc["subtree_content"] = csubhash
            doc["sigure_content"] = csighash
            doc["modular_content"] = cmodhash
        docs.append(doc)
    solr.add_many(docs)

if __name__ == '__main__':
    s = solr.SolrConnection('http://localhost:9000/solr/mcd.20150129')
    inp = argv[1]
    filepath = path.relpath(inp, '.')
    try:
        encode_file(filepath, s)
    except:
        print filepath + ' error'

