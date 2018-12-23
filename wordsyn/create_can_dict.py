import pycantonese as pc
from pprint import pprint
from collections import defaultdict
import json 

phonedict = dict([])
f = open('output2.txt', 'r')

phonedict = json.loads(f.read())
print(phonedict2)

# hkcan_corpus = pc.hkcancor()

# outdict = dict([])

# for each in phonedict:
#     pron = defaultdict(int)
#     eachpron = defaultdict(int)
#     wordinfo = hkcan_corpus.search(character=each)
#     try:
#         if wordinfo == []:
#             wordinfo = phonedict[each]
#             outdict[each] = [wordinfo, 1]
#         else:
#             for eachentry in wordinfo:
#                 pronpart = eachentry[2]
#                 word_index_in_token = eachentry[0].index(each)
#                 pron = pc.parse_jyutping(pronpart)[word_index_in_token]
#                 pron = "".join(list(pron))
#                 eachpron[pron] += 1
#             outdict[each] = [(k, eachpron[k]) for k in sorted(eachpron, key=eachpron.get, reverse=True)]
#     except:
#         pass
# for each in outdict:
#     print(each, outdict[each][0][0])