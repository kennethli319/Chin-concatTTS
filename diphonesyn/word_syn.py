# PROBLEMS
"""
1 - check sim chin / tran chin, if option given = follow option, if not check number of words in sim, if > 50%, sim else 
2 - check 
""" 

# Pipeline
"""
STRUCTURE
1 - CLASS:  Seq:    sequence
            Char:   char info
                    i)      
                    ii)     tone
                    iii)    tone
PROCEDURE
1 - 
"""


# -*- coding: utf-8 -*-
import json
import sys
import re 
import simpleaudio
import numpy as np

path = ""
dictpath = ""

if sys.argv[2] == "c":
    path = "jyutping-wong-44100-v9/jyutping-wong/"
    dictpath = 'phonedict_dict'
if sys.argv[2] == "p":
    path = "pinyin-yali-44100/"
    dictpath = "phonedict_dict_pth"

# seq info, contain char info in each item in a list
class Seq:
    def __init__(self, string):
        self.seqitem = list(string)

# char info, each char info
class Char:
    # prepare phone dict
    phonedict = dict([])
    f = open(dictpath, 'r')
    phonedict = json.loads(f.read())

    # special char
    phonedict["sil_200"] = ["sil_200"]
    phonedict["sil_400"] = ["sil_400"]

    def __init__(self, string):
        self.char = self.normalize(string)
        self.phone = self.phonedict[self.char]

    def normalize(self, string):
        string = re.sub("，", "sil_200", string)
        string = re.sub(r"[：；。？！]", "sil_400", string)
        return string

# Main part

# input seq get
inputseq = sys.argv[1]
inputseq = Seq(inputseq)

# Turn to class instance
index_of_item = 0
for each in inputseq.seqitem:
    inputseq.seqitem[index_of_item] = Char(each)
    index_of_item += 1

for each in inputseq.seqitem:

    each.eachphone = simpleaudio.Audio()

    # Audio instance to handle audio information
    sound_obj = simpleaudio.Audio(rate=48000)

    if each.phone[0] in ["sil_200","sil_400"]:
        if each.phone[0] == "sil_200":
            sound_obj.create_noise(9600,0)
        if each.phone[0] == "sil_400":
            sound_obj.create_noise(19200,0)
        each.eachphone.data = sound_obj.data
    else:
        phone = str(each.phone[0])
        if not phone[-1].isdigit():
            phone = phone + "5"
        each.path = path + phone + ".wav"
        each.eachphone.load(each.path)

output = simpleaudio.Audio()

for each in inputseq.seqitem:
    output.data = np.concatenate((output.data, each.eachphone.data))

output.play()