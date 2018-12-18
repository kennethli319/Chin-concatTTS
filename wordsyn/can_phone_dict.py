# -*- coding: utf-8 -*-
 
from pprint import pprint
# New user please install: pip3 install -U pycantonese
import pycantonese as pc

hkcan_corpus = pc.hkcancor()

pprint(hkcan_corpus.search(character="乾"))