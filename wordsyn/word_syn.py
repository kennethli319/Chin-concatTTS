# -*- coding: utf-8 -*-

# Usage
"""
Usage:      python3 word_syn.py <input_sequence> <language: c or p>
Example:    python3 word_syn.py 中文 c
"""

# PROBLEMS
"""
1 - check sim chin / tran chin, if option given = follow option, if not check number of words in sim, if > 50%, sim else 
2 - cantonese corpus = very slow -> change it to a txt file with count / % only 
3 - change chin char (simplified chinese vs traditional chinese)
4 - POS tag
5 - multi pronouncaition for the same word -> depends on the previous history : can be solve by POS + history
""" 

# Pipeline
"""
STRUCTURE
1 - CLASS:  Seq:    sequence
            Char:   char info
                    i)      Char
                    ii)     CV - onset, n, coda
                    iii)    Tone

PROCEDURE
0 - Import necessary libraries
1 - Argv management and global variables
2 - Define Classes
"""

# (Part 0) - Import necessary libraries
import json
import sys
import re 
import argparse
import numpy as np
from pprint import pprint
# Please put the py file in the same dir
import simpleaudio
# New user please install: pip3 install -U pycantonese
import pycantonese as pc

# (PART 1) Argv management and global variables

# (1.1) - Argv to argparse
parser = argparse.ArgumentParser(
    description='A basic text-to-speech app for Cantonese and Mandarin that synthesises an input phrase using unit selection.')
parser.add_argument('--canPhones', default="./jyutping-wong-44100-v9/jyutping-wong/", help="Folder containing Cantonese wavs")
parser.add_argument('--mandPhones', default="./pinyin-yali-44100/", help="Folder containing Mandarin wavs")
parser.add_argument('--language', "-l", action="store", dest="language", type=str, help="Choose the language for output",
                    default=None)
parser.add_argument('--play', '-p', action="store_true", default=False, help="Play the output audio")
parser.add_argument('--outfile', '-o', action="store", dest="outfile", type=str, help="Save the output audio to a file",
                    default=None)
parser.add_argument('phrase', nargs=1, help="The phrase to be synthesised")
parser.add_argument('--spell', '-s', action="store_true", default=False,
                    help="Spell the phrase instead of pronouncing it")
parser.add_argument('--crossfade', '-c', action="store_true", default=False,
					help="Enable slightly smoother concatenation by cross-fading between diphone tokens")
parser.add_argument('--volume', '-v', default=None, type=int,
                    help="An int between 0 and 100 representing the desired volume")

# (1.2) Parse arguments from the command line
try: 
    # Test if the user gave any argument
    assert len(sys.argv) > 1
    # If yes, parse all arguments 
    args = parser.parse_args() 
except:
    if len(sys.argv) == 1: 
        # If the user didn't input any argument, show the usage information
        print(parser.format_usage()) 
        # Gives instructions before quit
        print("*** ERROR: Required input phrase is missing, please provide an input string argument for synthesis.")
    else:
        # Otherwise, refer to an error message
        print("*** ERROR: Please check the missing/incorrect argument.")
        print("Usage Examples with input types:")
        print("\t  -volume \t<int: 0-100>")
        print("\t  -outfile \t<string: filename>")
    exit()

# (1.3) Global variables
path = ""
dictpath = ""

if args.language == "c":
    path = args.canPhones
    dictpath = 'phonedict_dict'
if args.language == "p":
    path = args.mandPhones
    dictpath = "phonedict_dict_pth_perc"

# (PART 2) Define classes

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

hkcan_corpus = pc.hkcancor()
for each in inputseq.seqitem:
    wordinfo = hkcan_corpus.search(character=each)
    pprint(len(wordinfo))
    pprint(wordinfo[:3])

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