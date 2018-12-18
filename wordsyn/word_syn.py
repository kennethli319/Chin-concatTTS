# -*- coding: utf-8 -*-

# Usage
"""
New user please install: 
    pip install -U pycantonese
    pip install opencc-python-reimplemented

Usage:
    python word_syn.py <input_sequence> <language: c or p>

Example:
    python word_syn.py 翻译都要执行多个翻译系统，这带来巨大的计算成本。如今，许多领域都正在被神经网路技术颠覆。 -l p
    python word_syn.py 翻譯都要執行多個翻譯系統，這帶來巨大的計算成本。如今，許多領域都正在被神經網路技術顛覆。 -l c
"""

# PROBLEMS
"""
1 - check sim chin / tran chin, if option given = follow option, if not check number of words in sim, if > 50%, mandarin else cantonese
2 - cantonese corpus = very slow -> change it to a txt file with count / % only 
3 - change chin char (simplified chinese vs traditional chinese)
4 - word seg and POS tag
5 - multi pronouncaition for the same word -> depends on the previous history : can be solve by POS + history(or word seg token)
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
3 - Frontend :
    3.1 - Get sequence
    3.2 - Normalization -> remove (unnecessary) punct, change all remaining punct to 全/半形
    3.3 - Classify cantonese / mandarin / english / mixture
    3.4 - Word seg -> to tokens
    3.5 - POS of token seq
    3.6 - Based on POS -> check the phones/words/diphones (from dict)
    3.7 - Change the phone/diphone/word-pron seq according to Consonant-Vowel Coarticulation rules in that lang
    3.8 - Intonation
    3.9 - 
4 - Waveform Generation
    4.1 - WORD UNIT VERION
        4.1.1 - load all required word wav
        4.1.2 - smoothing on boundaries?
        4.1.3 - output fine tune: eg volume/speed 1x 1.5x 2x?
    4.2 - DIPHONE UNIT VERSION
5 - Output
    5.1 - Output wav
    5.2 - Output all relations
    5.3 - Output all parameters
    5.4 - Output full info
"""

# (Part 0) - Import necessary libraries
import json, sys, re, argparse
import numpy as np
from pprint import pprint
# Please put the py file in the same dir
# FOLLOWUP: later should optimize this and re-write the load methods
import simpleaudio
# New user please install: pip install -U pycantonese
import pycantonese as pc
# New user please install: pip install opencc-python-reimplemented
from opencc import OpenCC

# (PART 1) Argv management and global variables
# (1.1) - Argv to argparse
parser = argparse.ArgumentParser(
    description='A basic text-to-speech app for Cantonese and Mandarin that synthesises an input phrase using unit selection.')
# Default paths
parser.add_argument('--canPhones', default="./jyutping-wong-44100-v9/jyutping-wong/", help="Folder containing Cantonese wavs")
parser.add_argument('--mandPhones', default="./pinyin-yali-44100/", help="Folder containing Mandarin wavs")
# User interface
parser.add_argument('phrase', nargs=1, help="The phrase to be synthesised")
parser.add_argument('--language', "-l", action="store", dest="language", type=str, help="Choose the language for output", default=None)
parser.add_argument('--play', '-p', action="store_true", default=False, help="Play the output audio")
parser.add_argument('--outfile', '-o', action="store", dest="outfile", type=str, help="Save the output audio to a file", default=None)
parser.add_argument('--volume', '-v', default=None, type=int, help="An int between 0 and 100 representing the desired volume")
# FOLLOWUP: Add -> voice optioins? speed? emotion? 

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

def check_lang(input_sequence):
    """Determine the language variaty of the input sequence and auto-select the langugae for synthesis."""
    # FOLLOWUP!
    language = 'p'
    return language

def assign_paths(language):
    """Select the required database according to the option given. If no language option is given, auto select by check_lang()."""    
    # If no selected option, auto-select
    if language == None:
        language = check_lang(args.phrase[0])  
        args.language = language  
    # Cantonese
    if language == "c":
        path = args.canPhones
        dictpath = 'phonedict_dict'
    # Mandarin
    elif language == "p":
        path = args.mandPhones
        dictpath = "phonedict_dict_pth_perc"
    return path, dictpath

def text_conversion(input_sequence):
    """S2T/T2S Conversion by OpenCC (https://github.com/BYVoid/OpenCC)"""
    # convert from Traditional Chinese to Simplified Chinese
    if args.language == 'p':
        cc = OpenCC('t2s') 
    # convert from Simplified Chinese to Traditional Chinese
    elif args.language == 'c':
        cc = OpenCC('s2t')  
    return cc.convert(input_sequence)

# (1.3) Global variables
path = ""
dictpath = ""
# (1.4) Select reuired database/dictionary accoring to the given lang option
path, dictpath = assign_paths(args.language)
# (1.5) Convert S2T or T2S to avoid mixed variaty text encoding
args.phrase[0] = text_conversion(args.phrase[0])

# (PART 2) Define classes

class Seq:
    """
    seq info, contain char info in each item in a list
    """
    def __init__(self, string):
        self.seqitem = list(string)

class Char:
    """
    char info, each char info
    """
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

# modified from https://codertw.com/%E7%A8%8B%E5%BC%8F%E8%AA%9E%E8%A8%80/373914/
# DOESNT WORK SAD
def strB2Q(ustring):
    """把字串半形轉全形"""
    rstring = ""
    for uchar in ustring:
        inside_code=ord(uchar)
    if inside_code<0x0020 or inside_code>0x7e:   #不是半形字元就返回原來的字元
        rstring  = uchar
    if inside_code==0x0020: #除了空格其他的全形半形的公式為:半形=全形-0xfee0
        inside_code=0x3000
    else:
        inside_code =0xfee0
        rstring  = chr(inside_code)
    return rstring

def normalizarion(inputString):
    outputString = strB2Q(inputString)
    return outputString

# Main part

# input seq get
inputseq = args.phrase[0]
inputseq = Seq(inputseq)
# inputseq = Seq(normalizarion(inputseq))

# hkcan_corpus = pc.hkcancor()
# for each in inputseq.seqitem:
#     wordinfo = hkcan_corpus.search(character=each)
    # pprint(len(wordinfo))
    # pprint(wordinfo[:3])

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