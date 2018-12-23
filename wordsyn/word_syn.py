# -*- coding: utf-8 -*-

# Usage
"""
New user please install: 
    pip install -U pycantonese
    pip install opencc-python-reimplemented
    pip install pkuseg

Usage:
    python word_syn.py <input_sequence> <language: c or p>

Example:
    python3 word_syn.py 1/1/2001，999！翻译都要执行多个翻译系统，这带来巨大的计算成本。如今，许多领域都正在被神经网路技术颠覆。 -l p -p -v 80
    python3 word_syn.py 1/01/1991，32。翻译都要执行多个翻译系统，这带来巨大的计算成本。如今，许多领域都正在被神经网路技术颠覆。 -l c -p -v 80
"""

# LOGBK and PROBLEMS
"""
16 DEC - Done word-wav data in Can and Manderin
18 DEC - Done overall documentation
19 DEC - (ING) Class structure -> token -> multichar prob!
19 DEC - NSW Date conversion

1 - check sim chin / tran chin, if option given = follow option, if not check number of words in sim, if > 50%, mandarin else cantonese
2 - cantonese corpus = very slow -> change it to a txt file with count / % only 
3 - [DONE-18dec] change chin char (simplified chinese vs traditional chinese)
4 - [H-DONE-18dec] word seg: use pku module, but not yet merge to the structure
5 - POS tag
5 - multi pronouncaition for the same word -> depends on the previous history : can be solve by POS + history(or word seg token)
""" 

# Pipeline
"""
STRUCTURE
1 - CLASS:  Sequence:    sequence
            Char:   char info
                    i)      Char
                    ii)     CV - onset, n, coda
                    iii)    Tone

PROCEDURE
[PREPARE]
0 - Import necessary libraries
1 - Argv management and declear global variables
2 - Define Methods and Classes
    2.1 - Methods
    2.2 - Classes
[MAIN]
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
import json, sys, re, argparse, pickle
import numpy as np
from pprint import pprint
# Please put the py file in the same dir
# FOLLOWUP: later should optimize this and re-write the load methods
import simpleaudio
# import eng_diphone_synth

# New user please install: pip install -U pycantonese
import pycantonese as pc
# New user please install: pip install opencc-python-reimplemented
from opencc import OpenCC
# New user please install: pip install pkuseg
import pkuseg

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
parser.add_argument('--crossfade', '-c', action="store_true", default=False,
					help="Enable slightly smoother concatenation by cross-fading between tokens")
parser.add_argument('--volume', '-v', default=None, type=int, help="An int between 0 and 100 representing the desired volume")
parser.add_argument('--speed', '-s', default=None, type=float, help="A float between 0 - 3 representing the desired speed")
# FOLLOWUP: Add -> voice options? speed? emotion? 

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
def check_lang(input_sequence):
    """Determine the language variaty of the input sequence and auto-select the langugae for synthesis."""
    # FOLLOWUP!: add classification methods
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
        dictpath = 'phonedict_dict_can'
    # Mandarin
    elif language == "p":
        path = args.mandPhones
        dictpath = "phonedict_dict_pth_perc"
    return path, dictpath

# (1.3) Select reuired database/dictionary accoring to the given lang option
path, dictpath = assign_paths(args.language)

# (PART 2) Define Functions and Classes
"""
(2.1) Operation functions


(2.2) Classes
    Sequence()  : Sequence of surface utterance, attributes including surface form, list of token objects
    Token()    : List of single/multiple Char instance, attributes including position marker, 
    Char()      : Single char

(2.3) User interface functions
    adjust_volume() : Volume Control
    save()          : Basic user interface to save the audio
    play_audio()    : Basic user interface to play the audio
"""

class Sequence:
    """
    seq info, contain char info in each item in a list
    """

    def __init__(self, string=""): 
        
        # (Step 0) - Define attributes
        self.utterance = ""
        self.norm_utterance = ""
        self.tokens = []
        # (Step 1) - Entire pipeline structure for TTS
        self.sayText(string)
        # (Step 2) - Print all linguistic infomation
        self.print_seq_info()

    def sayText(self,string):
        self.utterance = string
        self.norm_utterance = self.normalize(self.utterance) 
        self.seglist = self.word_seg(self.norm_utterance)
        self.tokens = []
        for each in self.seglist:
            self.tokens.append(Token(each))

    # FOLLOWUP: SUPER SLOW!
    def word_seg(self, string):
        """Word seg"""
        print('Around 15s:')
        seg = pkuseg.pkuseg()   #以默认配置加载模型
        tokens = seg.cut(string)	#进行分词
        return tokens

    def normalize(self, string):
        string = self.punct_conversion(string)
        # Convert S2T or T2S to avoid mixed variaty text encoding
        string = self.text_conversion(string)
        string = self.nsw_conversion(string)
        return string

    def punct_conversion(self, string):
        # FOLLOWUP: Remove unnecessary punct
        # FOLLOWUP: Convert half punct to full 
        return string

    def text_conversion(self, string):
        """S2T/T2S Conversion by OpenCC (https://github.com/BYVoid/OpenCC)"""
        # convert from Traditional Chinese to Simplified Chinese
        if args.language == 'p':
            cc = OpenCC('t2s') 
        # convert from Simplified Chinese to Traditional Chinese
        elif args.language == 'c':
            cc = OpenCC('s2t')  
        return cc.convert(string)

    def nsw_conversion(self, string):
        string = self.translate_num_pattern(string)
        return string
    
    # Text Normalization for dates and all number expressions
    def translate_num_pattern(self, text):
        '''
        Description: Search and translate number expressions, such as stand alone numbers or date expression
        
        Input : A string that contains sequence of text (with raw numbers)
        Output: Normalized text (with numbers as words) as a new string
        '''
        searching = True
        number_pattern = r"([^0-9]*)([0-9]+/*[0-9]*/*[0-9]*)([^0-9]*)"
        # Continuous searching for number expressions (including stand alone numbers and date expressions)
        while searching == True:
            # Detect if there is any number expressions in the text
            if re.match(number_pattern, text):
                # If yes, extract the number portion (group 2) and convert it to words
                num = re.match(number_pattern, text)
                number_word = self.number_to_word(num.group(2))
                # Replace the numbers with their corresponding pronunciable words
                text = text.replace(num.group(2),number_word,1)
            else:
                # No further match of numbers, then stop searching for number patterns
                searching = False
                break
        return text

    # Text Normalisation for numbers in date expressions
    def number_to_word(self, number_seq):
        '''
        Description: Convert numbers to words

        Input : A string that contains number sequence
        Output: Translated number in words as a new string
        '''
        output =""
        
        # For date expressions, split the input by the delimilater "/"
        number_list = number_seq.split("/")

        # Handle stand alone numbers
        if len(number_list) == 1:
            num = number_list[0]
            output = self.construct_number_words(num)

        # Handle date and month coversion, and optional year conversion
        elif len(number_list) >= 2:
            # Get words for date and month from a full entry dictionary
            date = int(number_list[0])
            assert date <= 31, "ERROR: Incorrect date format (date > 31 in DD/MM/YY)"
            assert date > 0, "ERROR: Incorrect date format (date < 0 in DD/MM/YY)"
            month = int(number_list[1])
            assert month <= 12, "ERROR: Incorrect month format (month > 12 in DD/MM/YY)"
            assert month > 0, "ERROR: Incorrect month format (month < 0 in DD/MM/YY)" 
            # Combine the converted words to the output
            output = self.construct_number_words(month) + "月" + self.construct_number_words(date) + "日"

            # Coversion of year part
            if len(number_list) == 3:
                year = number_list[2]
                # NOTE: Assume this program in default will deal with years in 20xx
                year_output = "二零"    
                # (EXTRA) Handle years outside the range of 20xx
                for each in year:
                    char = self.construct_number_words(each)
                    year_output += char
                if len(year) == 4:
                    year_output = ""
                    for each in year:
                        char = self.construct_number_words(each)
                        year_output += char
                output = year_output + "年" + output 

        # Provide a message to inform users about the auto number/date conversion
        print("Translated number expressions: " + number_seq + " ->" + re.sub("\s+"," ",output))

        return output

    # Extension F - Text Normalisation for number expressions
    # (EXTRA) Translates stand alone number expressions (range: 0-99)
    # (EXTRA) For long number, spell out digits one by one
    def construct_number_words(self, number):
        '''
        Description: Convert numbers to words

        Input : A string that contains number sequence
        Output: Translated number in words as a new string
        '''

        # Words corresponding to the numbers in digits
        dict_digit = {"0": "零", "1" : "一", "2" : "二", "3" : "三", "4" : "四", "5" : "五", "6" : "六", "7" : "七", "8" : "八", "9" : "九", "10" : "十"}
        
        number = str(number)
        number_words = ""
        
        # Contruct number to words
        try:
            # Pick their corresponding words in the dictionary 
            number_words = dict_digit[number]
        except:
            # If the expression is not in the dictionary, decompose the number to the ten position and digit position,
            # then recreate it based on the numerical value
            hunds = str(int(number)//100) 
            if hunds != '0':
                number_words = dict_digit[hunds] + "百"
            tens = str(int(number) % 100 // 10)
            remainder = str(int(number) % 10)
            # Look for their word forms seperatly
            number_words = number_words + dict_digit[tens] + "十" + dict_digit[remainder]
        # Return the word form of number expressions
        return number_words

    def print_seq_info(self):
        pprint("Surface utterance sequence: {}".format(self.utterance))
        print()
        pprint("Normalized utterance sequence: {}".format(self.norm_utterance))
        print()
        tokenlist = [] 
        for eachtoken in self.tokens:
            token = ""
            for eachchar in eachtoken.chars:
                token = token + eachchar.char
            tokenlist.append(token)
        pprint("List of tokens: {}".format(tokenlist))
        print()

        charlist = [] 
        for eachtoken in self.tokens:
            for eachchar in eachtoken.chars:
                charlist.append(eachchar.char)
        
        pprint("List of chars: {}".format(charlist))
        print()

    # def strB2Q(ustring):
    #     # modified from https://codertw.com/%E7%A8%8B%E5%BC%8F%E8%AA%9E%E8%A8%80/373914/
    #     # DOESNT WORK SAD
    #     """把字串半形轉全形"""
    #     rstring = ""
    #     for uchar in ustring:
    #         inside_code=ord(uchar)
    #     if inside_code<0x0020 or inside_code>0x7e:   #不是半形字元就返回原來的字元
    #         rstring  = uchar
    #     if inside_code==0x0020: #除了空格其他的全形半形的公式為:半形=全形-0xfee0
    #         inside_code=0x3000
    #     else:
    #         inside_code =0xfee0
    #         rstring  = chr(inside_code)
    #     return rstring

    # def normalizarion(inputString):
    #     outputString = strB2Q(inputString)
    #     return outputString

class Token:
    def __init__(self, string):

        self.token = []

        self.chars = []
        for each in string:
            self.chars.append(Char(each))

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
        self.onset = ""
        self.nu = ""
        self.coda = ""
        self.tone = ""
        self.stress = False

    def normalize(self, string):
        string = re.sub("，", "sil_200", string)
        string = re.sub(r"[：；。？！]", "sil_400", string)
        return string

# (2.3) User interface functions

def adjust_volume(volume=None, object=None):
    """
    Description: Volume Control
    
    Input: Required volume adjustment value 0 to 100 and the object to adjust
    Output:The volume adjusted audio object
    """
    if volume != None:
        # Ensure the volume scaling is in the expected range
        if volume < 0 or volume > 100:
            raise ValueError("Expected scaling factor between 0 and 100.")
        # Conver the input int 0-100 to a float number between 0-1 and rescale accordingly
        object.rescale(volume/100.0)
    # Return the modified audio object
    return object 

def save(output_file=None, object=None):
    """
    Description: Basic user interface to save the audio
    """
    if output_file != None:
        object.save(output_file)
        print("It is saved as:", output_file)
        # (EXTRA) Ensure user understand the potential error
        if ".wav" not in output_file:
            print("*** WARNING: File might not be saved properly if your file extension is not .wav")

def save_pickle(output_file=None, object=None):
    """
    Description: Basic user interface to save the pickle file 
    """
    if output_file != None:
        with open(output_file+'.pickle', 'wb') as out:
            pickle.dump(object, out)

def play_audio(play=False, object=None):
    """
    Description: Basic user interface to play the audio
    """
    if play == True:
        object.play()

# Main module
def main():
    # Step 1 - Get input utterance sequence
    inputseq = args.phrase[0]
    # Step 2 - Put the text in a Sequence instance
    inputseq = Sequence(inputseq)

    # hkcan_corpus = pc.hkcancor()
    # for each in inputseq.tokens:
    #     wordinfo = hkcan_corpus.search(character=each)
        # pprint(len(wordinfo))
        # pprint(wordinfo[:3])
    
    for eachtoken in inputseq.tokens:
        for eachchar in eachtoken.chars:
 
            eachchar.eachphone = simpleaudio.Audio()

            # Audio instance to handle audio information
            sound_obj = simpleaudio.Audio(rate=48000)

            if eachchar.phone[0] in ["sil_200","sil_400"]:
                if eachchar.phone[0] == "sil_200":
                    sound_obj.create_noise(9600,0)
                if eachchar.phone[0] == "sil_400":
                    sound_obj.create_noise(19200,0)
                eachchar.eachphone.data = sound_obj.data
            else:
                phone = str(eachchar.phone[0])
                if not phone[-1].isdigit():
                    phone = phone + "5"
                eachchar.path = path + phone + ".wav"
                eachchar.eachphone.load(eachchar.path)

    output = simpleaudio.Audio()

    # for eachtoken in inputseq.tokens:
    #     for eachchar in eachtoken.chars:
    #         output.data = np.concatenate((output.data, eachchar.eachphone.data))
    
    # Variable to track diphone index and processing char_index
    char_index = 0
    # Normal concatenation without smoother
    charlist = []
    for eachtoken in inputseq.tokens:
        for eachchar in eachtoken.chars:
            charlist.append(eachchar.char)
    
    for eachtoken in inputseq.tokens:
        for eachchar in eachtoken.chars:
            temp_diphone = simpleaudio.Audio(rate=32000)
            temp_diphone.data = eachchar.eachphone.data
            if args.crossfade == False:
                output.data = np.concatenate((output.data, temp_diphone.data))
            # If smoother is used, implement Extension E - Smoother Concatenation
            else:            
                adjust_level = 0.0
                # This loop rescales the 320 data points (10 msc) near the both edges of the diphone
                for index in range(0,321):    
                    if char_index > 0:
                        # Except the first diphone:
                        # Scale the data points in the initial 10 msc of current working diphone
                        # Order: Start scaling from the 1st point, 2nd, 3rd... througout the loop (From edge of diphone towards the middle)
                        temp_diphone.data[index] = temp_diphone.data[index] * adjust_level/320.0
                    if char_index < len(charlist)-1:
                        # Except the last diphone:
                        # Scale the data points in the last 10 msc of of current working diphone
                        # Order: Start scaling from the last point, 2nd last, 3rd last... througout the loop (From edge of diphone towards the middle)
                        temp_diphone.data[-(index+1)] = temp_diphone.data[-(index+1)] * adjust_level/320.0
                    # Turn louder when moving inward in the next round of the loop
                    adjust_level+=1
                
                # After rescale all, seperate the whole diphone into two portions: (1) initial 10msc, and (2) everything after 10msc
                np.initial10msc = temp_diphone.data[:320]
                np.after10msc = temp_diphone.data[320:]

                # Combine diphone portions together in the output.data
                if char_index == 0:
                    # For the 1st diphone, concatenate the whole rocessed diphone data
                    output.data = np.concatenate((output.data, temp_diphone.data))
                else:
                    # For later diphones, addup/cross-fade the first 10 msc of the current diphone with last 10 msc of the previous diphone (which saved in the output.data in the previous round)
                    output.data[-320:] = output.data[-320:] + np.initial10msc
                    # Concatenate the remaining part of the processed diphone data
                    output.data = np.concatenate((output.data, np.after10msc))
            # Increase monitereing index
            char_index += 1
    # for each in inputseq.tokens:

    #     each.eachphone = simpleaudio.Audio()

    #     # Audio instance to handle audio information
    #     sound_obj = simpleaudio.Audio(rate=48000)

    #     if each.phone[0] in ["sil_200","sil_400"]:
    #         if each.phone[0] == "sil_200":
    #             sound_obj.create_noise(9600,0)
    #         if each.phone[0] == "sil_400":
    #             sound_obj.create_noise(19200,0)
    #         each.eachphone.data = sound_obj.data
    #     else:
    #         phone = str(each.phone[0])
    #         if not phone[-1].isdigit():
    #             phone = phone + "5"
    #         each.path = path + phone + ".wav"
    #         each.eachphone.load(each.path)

    # output = simpleaudio.Audio()

    # for each in inputseq.tokens:
    #     output.data = np.concatenate((output.data, each.eachphone.data))

    # Step 5 - Further adjustment on overall volume to the final output (if the user use -v <0-100>)
    output = adjust_volume(volume=args.volume, object=output)

    # Step 6 - Save it to the target file (if the user use -o <args.outfile>)
    save(output_file=args.outfile, object=output)

    save_pickle(output_file=args.outfile, object=output)
        
    # Step 7 - Play the final sound output (if the user use -p)
    play_audio(play=args.play, object=output)

if __name__ == "__main__":
    main()