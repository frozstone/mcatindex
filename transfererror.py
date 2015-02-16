from shutil import copyfile
from os import makedirs, path, listdir

lns = open('indexing.log').readlines()
fls = [ln.split()[0] for ln in lns]

mathdir = '../mathmlandextra/math_new'
mathadj = '../mathmlandextra/math_adj'
sentdir = '../splitted/multifiles/'
targetdir = '/home/giovanni/mathmlandextra'

if not path.exists(path.join(targetdir, 'math_new')): makedirs(path.join(targetdir, 'math_new'))
if not path.exists(path.join(targetdir, 'math_adj')): makedirs(path.join(targetdir, 'math_adj'))
if not path.exists(path.join(targetdir, 'sentences')): makedirs(path.join(targetdir, 'sentences'))

def copydir(d1, d2):
    if not path.exists(d2): makedirs(d2)
    for fl in listdir(d1):
        copyfile(path.join(d1, fl), path.join(d2, fl))

for fl in fls:
    papername = path.basename(fl)
    dirname = path.dirname(fl)
    if not path.exists(path.join(targetdir, 'math_new', dirname)): makedirs(path.join(targetdir, 'math_new', dirname))
    if not path.exists(path.join(targetdir, 'math_adj', dirname)): makedirs(path.join(targetdir, 'math_adj', dirname))
    if not path.exists(path.join(targetdir, 'sentences', dirname)): makedirs(path.join(targetdir, 'sentences', dirname))

    copyfile(path.join(mathdir, fl), path.join(targetdir, 'math_new', fl))
    copyfile(path.join(mathadj, fl), path.join(targetdir, 'math_adj', fl))
    copydir(path.join(sentdir, dirname, papername[:papername.rindex('.')]), path.join(targetdir, 'sentences', dirname, papername[:papername.rindex('.')]))


    
