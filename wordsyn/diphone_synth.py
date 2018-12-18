"""
README
Description: A basic text-to-speech app that synthesises an input phrase using diphone unit selection.
Usage  : python3 synth.py "input sequence" [options -p -o <outputfile> -s -c -v <0-100>

Remarks: Done task 1 and all extensions in task 2 (marked with task number in comment), 
a few further implementations to enhance robustness of multi-option situation is marked as "(EXTRA)", 
e.g. emphrasis on spelling/date, spelling out digits/dates, translate stand alone numbers in text, and
potential output error warning etc.
"""
import os
import sys
import pyaudio
import simpleaudio
import argparse
import nltk
from nltk.corpus import cmudict
import re
import numpy as np

# Given argparse auguments
parser = argparse.ArgumentParser(
    description='A basic text-to-speech app that synthesises an input phrase using diphone unit selection.')
parser.add_argument('--diphones', default="./diphones", help="Folder containing diphone wavs")
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

# (PART I) Parse arguments from the command line
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

# (PART II) Utterance class for processing text normalization and annotation
class Utterance:
    """
    Description: Normalize an input text, generate its corresponding diphone sequence and 
    extract feature information for further processing in Synth class (e.g. diphone list, 
    number translation, interprete emphasis marking...)
    """

    def __init__(self, input_text):
        # Step 0 - Get the original input text
        self.text = input_text
        # Step 1 - Normalize the input text (e.g. lowercase, remove punctuation...)
        self.norm_text = self.normalise_text(self.text)
        # Step 2 - Get the corresponding phone sequence and feature information (emphasis) based on the normalized text
        self.phone_seq, self.emphasis = self.get_phone_seq(self.norm_text)
        # Step 3 - Construct diphone sequence and pass on the feature information
        self.diphone_seq, self.diph_emphasis = self.to_diphones(self.phone_seq)
        # NOTE: self.emphasis could be named as "self.features" if lexical stress/pitch/tone features associated with each phone/diphone 
        # are also used in the TTS system, by storing features with the associated phone/diphone indexes, it allows extendable feature 
        # addition for each phone/diphone in a more complex system.
   
    # Task 1 and 2 - Normalise the input text
    # (Task 1) - Basic text normalisation e.g. lowercase, remove unnecessary punctuation marks
    # (Task 2) - Text annotation/expendsion for punctuation, date, number, emphasis markup
    def normalise_text(self, text):
        '''
        Description: Normalise the input text, including basic text normalisation (e.g. lowercase, remove unnecessary 
        punctuation marks) and text annotation for punctuation, date, number, and emphasis markup.

        Input : A string that contains sequence of text (with raw numbers, markup annotation...)
        Output: Normalized text as a new string
        '''

        # (1) - Basic text normalization
        # Remove characters that do not belong to alphanumeric, space, or a limited set of puncuations.
        text = re.sub(r'[^0-9a-z {}/,.:?!-[\'s]]', '', text.lower()) 
        # Special case '-': replace it with white space
        text = re.sub(r'[-]', ' ', text) 
        # Special case "'s": replace it with intermediate representation
        text = re.sub(r'\'s', ' _s', text) 

        # (2) - Translate number sequences to word sequence in an utterance
        text = self.translate_num_pattern(text)
        # (3) - Mark words with emphrasis with ALL CAP for feature extreation in later stages
        text = self.mark_emphasis(text)
        # (4) - Special handling for additional space inserted in some previous steps: strip and replace multiple space with one white space
        text = re.sub(r"\s+", " ", text.strip())
        
        # (5) - Extentsion B Punctuation (anotation of short "s_short" and long "s_long" silence)
        text = re.sub(r",", " s_short", text)
        text = re.sub(r"[.:?!]", " s_long", text)
        # (6) - Extentsion Spelling
        if args.spell == True:
            # For spelling, handle other pause from punciuation 
            # then insert annotation of short pause (#) after each word e.g. "This#is#pause"
            text = re.sub(r"\s*", "", text)
            text = re.sub("s_short", "#", text)
            text = re.sub("s_long", "#", text)
            # Avoid error in spelling digits in date
            text = re.sub(r"[_/]", "", text)
            # For spelling, add short pause between each letter e.g. "#a#b#c#d#e#"
            text = re.sub("", "#", text)
            # Remove first and last "#" e.g. "#a#b#c#" -> a#b#c
            text = text[1:-1]
        
        # Return the normalized string
        return text
    
    # Extension F - Text Normalization for Dates
    # (EXTRA) - Text Normalization for all number expressions (e.g. stand alone number expressions in range 0-99 e.g. In the sample "The meaning of life is 42")
    def translate_num_pattern(self, text):
        '''
        Description: Search and translate number expressions, such as stand alone numbers or date expression
        
        Input : A string that contains sequence of text (with raw numbers)
        Output: Normalized text (with numbers as words) as a new string
        '''
        searching = True
        number_pattern = r"([^0-9]*)([0-9]+/*[0-9]*/*[0-9]*)([^0-9]*)"
        # Continuous searching for number expressions (including stand alone numbers and date expressions)
        # Don't translate number to word while spelling, keep them as digits for spelling
        while searching == True and args.spell != True:
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

    # Extension F - Text Normalisation for numbers in date expressions
    # (EXTRA) Handle years outside the range of 19xx, e.g. 0000-9999
    def number_to_word(self, number_seq):
        '''
        Description: Convert numbers to words

        Input : A string that contains number sequence
        Output: Translated number in words as a new string
        '''

        # Words corresponding to the dates in digits
        dict_date = {   "1" : "first", "2" : "second", "3" : "third", "4" : "fourth", "5" : "fifth", "6" : "sixth", "7" : "seventh", "8" : "eighth", "9" : "ninth", "10" : "tenth", "11" : "eleventh", "12" : "twelfth", "13" : "thirteenth", "14" : "fourteenth", "15" : "fifteenth", "16" : "sixteenth", "17" : "seventeenth", "18" : "eighteenth", "19" : "nineteenth", "20" : "twentieth", "21" : "twenty first", "22" : "twenty second", "23" : "twenty third", "24" : "twenty fourth", "25" : "twenty fifth", "26" : "twenty sixth", "27" : "twenty seventh", "28" : "twenty eighth", "29" : "twenty ninth", "30" : "thirtieth", "31" : "thirty first", }

        # Words correspoding to the months in digits
        dict_month = {  "1" : "january", "2" : "february", "3" : "march", "4" : "april", "5" : "may", "6" : "june", "7" : "july", "8" : "august", "9" : "september", "10" : "october", "11" : "november", "12" : "december", }

        output =""
        
        # For date expressions, split the input by the delimilater "/"
        number_list = number_seq.split("/")

        # Handle stand alone numbers
        if len(number_list) == 1:
            output = self.construct_number_words(number_list[0])

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
            output = " " + dict_month[str(month)] + " " + dict_date[str(date)] + " "

            # Coversion of year part
            if len(number_list) == 3:
                year = number_list[2]
                # NOTE: Assume this program in default will deal with years in 19xx
                year_first2digits = "nineteen"    
                    # (EXTRA) Handle years outside the range of 19xx
                if len(year) == 4:
                    year_first2digits = year[:2]
                    # (EXTRA) Construct the word of the number
                    year_first2digits = self.construct_number_words(year_first2digits)
                # Convert the last 2 digits of year expressions
                year_last2digits = year[-2:]
                year_last2digits = self.construct_number_words(year_last2digits)
                # Correct "zero" to specific pronunciation of zero in year expression
                year_last2digits = re.sub("zero", "o", year_last2digits)
                # Append the year part to the date output
                output = output + " " + year_first2digits + " " + year_last2digits + " "

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
        dict_number = {   "0" : "zero", "1" : "one", "2" : "two", "3" : "three", "4" : "four", "5" : "five", "6" : "six", "7" : "seven", "8" : "eight", "9" : "nine", "10" : "ten", "11" : "eleven", "12" : "twelve", "13" : "thirteen", "14" : "fourteen", "15" : "fifteen", "16" : "sixteen", "17" : "seventeen", "18" : "eighteen", "19" : "nineteen", "20" : "twenty", "30" : "thirty",  "40" : "forty",  "50" : "fifty",  "60" : "sixty", "70" : "seventy",  "80" : "eighty",  "90" : "ninety", 
        }

        # (EXTRA) - Spell out digits in long numbers 
        if len(number) > 2:
            number = number.replace("", " ", len(number))
            return number
        
        # Contruct number to words
        try:
            # Pick their corresponding words in the dictionary 
            number_words = " " + dict_number[number] + " "
        except:
            # If the expression is not in the dictionary, decompose the number to the ten position and digit position,
            # then recreate it based on the numerical value
            tens = str(int(number)//10 * 10)
            remainder = str(int(number) % 10)
            # Look for their word forms seperatly
            number_words = " " + dict_number[tens] + " " + dict_number[remainder] + " "
        # Return the word form of number expressions
        return number_words

    # Extension D - Emphasis markup
    def mark_emphasis(self, text):
        '''
        Description: Search and change the annotation of emphasis words as ALL CAP

        Input : A string that contains sequence of text (with diphone_index blanket annotation for emphasis)
        Output: Normalized text (with ALL CAP annotation for emphasis) as a new string
        '''
         # Change annotation of emphrasis to capital letters
        searching = True
        stress_pattern = r'(.*)({.*})(.*)'
        # Continuous searching for an expressions
        while searching == True:
            # Detect if there is any emphrasis expressions in the text
            if re.match(stress_pattern, text):
                # If yes, annotate all emphrasised words (can be more than one token)
                stress = re.match(stress_pattern, text)
                # Remove the previous annotation '{}'
                new = re.sub(r'[{}]', ' ' ,stress.group(2))
                # Replace the text by the new annotation with all capital letters
                # NOTE: Since we lowercase all text in the previous steps, now capital only means emphrasis
                text = text.replace(stress.group(2), new.upper(), 1)
            else:
                # No further match of emphrasis words, then stop searching for emphrasis patterns
                searching = False
                break
        return text
    
    # Task 1 and 2 - Convert a text squence to a pronunciable phone sequence
    # (Task 1) - Word pronunciation sequence
    # (Task 2) - Spell out sequence of letters
    def get_phone_seq(self, norm_text):
        '''
        Description: Convert a text squence to a pronunciable phone sequence

        Input : A string that contains normalized text
        Output: A list of phone sequence 
        '''
        # Get pronunciation dictionary form CMU dict
        try:
            phoneDict = cmudict.dict()
        # If user does not have CMU dict, download before load
        except LookupError:
            nltk.download('cmudict')
            phoneDict = cmudict.dict()
        
        # Task 1 and 2 - Tokenize the text sequence
        # (Task 1) - For normal pronuciation, split the text to token list accourding to while space
        # (Task 2) - For spelling, special annotation for spelling sequence
        if not args.spell:
            # For normal sequence, split according to white space to tokens
            all_tokens = norm_text.split(" ")
        else:
            # For spelling, the string text contains all tokens
            all_tokens = norm_text

        # Local variable to store phone list and word index of emphasis word tokens
        wordindex = 0
        startphone_index = 0
        pron_list = []
        emphasis = set()
        emp_wordlist = []

        # Get the phones for each word and store in phone dictionary
        for each_token in all_tokens:

            emp_flag = False
            
            # Some special procedures for annotation before checking their pronunciation in the dictionary
            # (EXTRA) - Spell out digits in long numbers 
            if each_token.isdigit():
                each_token = self.construct_number_words(each_token)
            # Task 2 - Use letter pronunciation when spelling
            if args.spell and each_token.isalpha() and len(each_token) == 1:   
                each_token = each_token+'.'

            # Task 2 - Check exphrasis word tokens, normalize them and turn the flag True (for later marking)
            if each_token.isupper():
                each_token = each_token.lower()
                emp_flag = True

            # Extract pronunciation of each token from pronunciation dict
            # NOTE: ASSUMPTION: For words with multiple possible pronunciation in CMU dict, we use the 1st one
            try:
                pron_list.extend(phoneDict[each_token.strip()][0])
            # Special handling for tokens not in the CMU dict
            except:
                # Annotation of 200ms silence
                # (EXTRA) - Change short pause annotation '#' to 200ms silence between each word in spelling
                if each_token == "s_short" or '#' in each_token:
                    pron_list.extend(["s_short"])
                # Annotation of 400ms silence
                elif each_token == "s_long":
                    pron_list.extend(["s_long"])
                # For annoation of 's, pronunce as 'S'
                elif each_token == "_s":
                    pron_list.extend(["S"])
                # For empty character (after inserting in-program conversion of number), skip
                elif each_token.strip() == '':
                    continue
                # For unhandled case, show error meassage : Unknown token in the dictioinary
                else:
                    print("ERROR: This word is not in the CMU dict:", each_token)
                    exit() 

            # When flag for emphasis token is true, save indexes of emphrasised phones
            if emp_flag == True:
                # Record the emphasisd tokens
                emp_wordlist.append(each_token)
                # The index covers the starting phone of this token to the last phone this token
                for phone_index in range(startphone_index,len(pron_list)):
                    emphasis.add(phone_index)

            # Update indexes
            wordindex += 1
            startphone_index = len(pron_list)
        
        # Imform user the emphasised words
        print("Emphasised tokens:", emp_wordlist)

        # Return phone list and emphasis
        return pron_list, emphasis

    # Task 1 - Covert phone sequence to diphone sequence
    def to_diphones(self, phone_seq):
        '''
        Description: Convert a phone squence to a concatable diphone sequence

        Input : A string that contains required phones in their ordered
        Output: A list of diphone sequence and a list marking the diphone features (in this case emphasis only) 
        '''
        # Initial value
        current = ""
        previous = "pau"
        final = "pau"
        
        # Store the diphone sequence as a list
        diphone_seq = list()
        diph_emphasis = set()

        # Phone index
        phone_index = 0
        
        # Diphone index value (Different from the phone index due to insertion of pause and silence)
        diph_index = 0    
        
        # Construct phone sequence to diphone sequence
        for eachphone in phone_seq:
            
            # Normalize the phone annotation
            current = re.sub(r'[0-9]', '', eachphone.lower())

            # Insert extra 'pau-X' or 'X-pau' transition diphones before and after silence
            if current == "s_short" or current == "s_long":
                diphone_seq.append(previous+"-pau")
                diphone_seq.append(current)
                previous = "pau"
                phone_index += 1
                diph_index += 2
                continue
            else:
                # For normal diphones, append diphone in the correct format
                diphone_seq.append(previous+"-"+current)

            # Mark index of emphasis diphones in diph_emphasis
            if phone_index in self.emphasis:
                diph_emphasis.add(diph_index)

            # When it is the last diphone, add extra pause transition to the end
            if phone_index == len(phone_seq)-1:
                diphone_seq.append(current+"-"+final)
            
            # Update
            previous = current
            phone_index += 1
            diph_index += 1

        # Return diphone sequence and the emphasis marked set
        return diphone_seq, diph_emphasis

# (PART III) Synth class for synthesizing audio signal
class Synth():
    """
    Description: This class takes the required diphones, diphone_features and generate the audio 
    based on the given feature information (e.g. emphasiss).
    """

    def __init__(self, wav_folder, diphone_seq=None, diph_emphasis=None):
        """
        Description: Go through a pipeline to generate the required audio: (1) get the diphones, (2) concatenate them to an Audio object
        
        Input : A path to wav_folder, a list of requested diphones, a set of diphone index which marked with emphasis
        Output: Return nothing but save information in self attribute (self.diphones and self.output)
        """
        # Step 0 - Infomation about diphone sequence from text annotation part done in Utterence
        self.diphone_seq = diphone_seq
        self.diph_emphasis = diph_emphasis
        # Step 1 - Get unique diphone audio data (numpy array that represent their audio signal) from the diphone database
        self.diphones = self.get_wavs(wav_folder=wav_folder)
        # Step 2 - Concatenate the audio in diphones and put them to an output audio instance 
        self.output = self.concat_diphones(diph_emphasis=self.diph_emphasis, smoother=bool(args.crossfade))

    # Task 1 - Basic synthesis
    def get_wavs(self, wav_folder):
        """
        Description: Construct a unique set of required diphones, load the corresponding numpy array 
        from their .wav file, and save the array to a dictionary
        
        Input : A path to wav_folder, a list of requested diphones, a list of diphone features
        Output: A dictionary of diphone audio numpy array
        NOTE  : Focus on efficiecy 
                (1) Only load data from database for each REQUIRED UNIQUE diphones 
                (2) Save data in numpy array instead of object instance
        """
        # Variables to store diphones
        diphone_path = dict([])
        diphones = dict([])
        
        # To ensure efficiency, I create a list of unique diphones that we need to retrive from the file.
        # This avoid reloading the same file again and again if the syntheisis sentence is long and contains
        # lots of repeating words, e.g. Long sentence with repeating the, a, he, she .... 
        unique_diphones = set(map(lambda each_diphone: each_diphone, self.diphone_seq))

        # Only go through the database once, storing a complete dictionary of avaliable diphone and their path
        # is still necessary because my required diphone might be a missing diphone, I need to know what other
        # similar diphones in the database I can use.
        for root, dirs, files in os.walk(wav_folder, topdown=False):
            for file in files:
                diphone_path[file] = root + '/' + file

        # Go through the required diphones, use the method in an Audio instance to load the numpy array data,
        # then only store the np array data in the diphone dictionary (i.e. key: diphone, value: np array)
        for required_diphone in unique_diphones:

            # Audio instance to handle audio information
            sound_obj = simpleaudio.Audio(rate=16000)
            
            # Extension B Punctuation: Short silence (200 ms)
            if required_diphone == "s_short":
                sound_obj.create_noise(3200,0)
                diphones[required_diphone] = sound_obj.data
            # Extension B Punctuation: Long silence (400 ms)
            elif required_diphone == "s_long":
                sound_obj.create_noise(6400,0)
                diphones[required_diphone] = sound_obj.data
            else:
                # Handle normal diphones
                try:
                    # Load the audio data from the corresponding path
                    path = diphone_path[required_diphone+".wav"]
                    sound_obj.load(path)
                    # Save the array data in a dictionary
                    diphones[required_diphone] = sound_obj.data
                except KeyError:
                    # Show error message to user when there is a KeyError which refers to missing diphone in the diphone database
                    print("*** This is a missing diphone: ", required_diphone)
                    # Instead of quiting the program, use the method sub_diphone to find corresponding suitable subsitude diphone
                    sub_diphone = self.sub_diphone(required_diphone)
                    # NOTE: Show message to user about subsitution of diphone
                    print("*** Using subsitude diphone: ", sub_diphone)
                    # Save the array data in the dictionary
                    path = diphone_path[sub_diphone+".wav"]
                    sound_obj.load(path)
                    diphones[required_diphone] = sound_obj.data
                    
        # Return the complete dictionary that contains diphone array data
        return diphones

    # (EXTRA) - Handle missing diphones
    def sub_diphone(self, missing_diphone):
        """
        Description: Replace missing diphone by other suitable diphone
        
        Input : A string of missing diphone
        Output: A string of corresponding subsitution diphone
        """
        if missing_diphone == 'w-er': 
            # Special handling for known case 
            return 'w-uh'
        else:
            # For others, use a schwa like sound (The -b is almost unnoticiable in this diphone)
            return 'er-b'

    # Task 1 and 2 - Basic synthesis, diphone emphasis and smoother
    # (Task 1) - Basic diphone concatination
    # (Task 2) - Extentions: Diphone emphasis and smoother
    def concat_diphones(self, diph_emphasis=None, smoother=False):
        """
        Description: 
        
        Input : A string of missing diphone
        Output: A string of corresponding subsitution diphone
        """
        # Audio instance to store the TTS audio output
        output = simpleaudio.Audio(rate=16000)
        
        # Variable to track diphone index and processing diphone_index
        diphone_index = 0

        # Go through the diphones in the ordered diphone sequence
        for each_diphone in self.diphone_seq:

            # Create an Audio instance to store temporary audio data 
            temp_diphone = simpleaudio.Audio(rate=16000)
            temp_diphone.data = self.diphones[each_diphone]

            # Extension D Emphasis markup
            # If any emphasis marking is used
            if len(diph_emphasis) > 0:
                # Dont rescale silence (Avoid numpy warning error)
                if each_diphone == "s_short" or each_diphone == "s_long":
                    continue
                # Adjust the volume of the diphone if it's index is marked as emphasis diphone in the set
                elif diphone_index in diph_emphasis:
                    # (EXTRA) Loud fricatives make unpleasant noise, thus the adjustment volume (0.60) is slight less than other emphasis diphones (0.65)
                    if 's' in each_diphone or 'th' in each_diphone or 'f' in each_diphone:
                        adjust_value = 0.60
                    else:
                        adjust_value = 0.65
                    temp_diphone.rescale(adjust_value)
                # (EXTRA) To make a smoother transition of emphasis enhancement, also slightly adjust the diphone that directly follow the emphasis diphones (0.525)
                elif diphone_index-1 in diph_emphasis:
                    adjust_value = 0.525
                    temp_diphone.rescale(adjust_value)

            # Normal concatenation without smoother
            if smoother == False:
                output.data = np.concatenate((output.data, temp_diphone.data))
            # If smoother is used, implement Extension E - Smoother Concatenation
            else:            
                adjust_level = 0.0
                # This loop rescales the 160 data points (10 msc) near the both edges of the diphone
                for index in range(0,161):    
                    if diphone_index > 0:
                        # Except the first diphone:
                        # Scale the data points in the initial 10 msc of current working diphone
                        # Order: Start scaling from the 1st point, 2nd, 3rd... througout the loop (From edge of diphone towards the middle)
                        temp_diphone.data[index] = temp_diphone.data[index] * adjust_level/160.0
                    if diphone_index < len(diphone_seq)-1:
                        # Except the last diphone:
                        # Scale the data points in the last 10 msc of of current working diphone
                        # Order: Start scaling from the last point, 2nd last, 3rd last... througout the loop (From edge of diphone towards the middle)
                        temp_diphone.data[-(index+1)] = temp_diphone.data[-(index+1)] * adjust_level/160.0
                    # Turn louder when moving inward in the next round of the loop
                    adjust_level+=1
                
                # After rescale all, seperate the whole diphone into two portions: (1) initial 10msc, and (2) everything after 10msc
                np.initial10msc = temp_diphone.data[:160]
                np.after10msc = temp_diphone.data[160:]

                # Combine diphone portions together in the output.data
                if diphone_index == 0:
                    # For the 1st diphone, concatenate the whole rocessed diphone data
                    output.data = np.concatenate((output.data, temp_diphone.data))
                else:
                    # For later diphones, addup/cross-fade the first 10 msc of the current diphone with last 10 msc of the previous diphone (which saved in the output.data in the previous round)
                    output.data[-160:] = output.data[-160:] + np.initial10msc
                    # Concatenate the remaining part of the processed diphone data
                    output.data = np.concatenate((output.data, np.after10msc))
            # Increase monitereing index
            diphone_index += 1
        # Return 
        return output

# (PART IV) Three user interface control functions

# Extention A Volume Control
def adjust_volume(volume=None, object=None):
    """
    Description: Extention A Volume Control
    
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

def play_audio(play=False, object=None):
    """
    Description: Basic user interface to play the audio
    """
    if play == True:
        object.play()

# (PART V) Main module
if __name__ == "__main__":

    # Step 1 - Create an Utterance instance to handle text normalization and annotatioin (incl. translation of number) of input text
    utt = Utterance(input_text=args.phrase[0])

    # Step 2 - Get diphone sequence and feature information (emphrasis) after text normalization
    diph_emphasis = utt.diph_emphasis
    diphone_seq = utt.diphone_seq

    # Step 3 - Create a Synth instance to work on synthesing sound based on the given infomation
    diphone_synth = Synth(wav_folder=args.diphones, diphone_seq=diphone_seq, diph_emphasis=diph_emphasis)
    
    # Step 4 - Clone the data from the Synth instance 'diphone_synth' that contains concatenated audio data to an output Audio instance 'output'
    output = simpleaudio.Audio(rate=16000)
    output.data = diphone_synth.output.data

    # Step 5 - Further adjustment on overall volume to the final output (if the user use -v <0-100>)
    output = adjust_volume(volume=args.volume, object=output)

    # Step 6 - Save it to the target file (if the user use -o <args.outfile>)
    save(output_file=args.outfile, object=output)
    
    # Step 7 - Play the final sound output (if the user use -p)
    play_audio(play=args.play, object=output)