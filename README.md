# Chin-concatTTS
Cantonese and Mandarin concatenation TTS system in Python <br>
For DNN TTS, please check https://github.com/kennethli319/Chin-dnnTTS

# Usage
"""
New user please install: 
    pip install -U pycantonese
    pip install opencc-python-reimplemented
    pip install pkuseg

Usage:
    python word_syn.py <input_sequence> <language: c or p>

Example:
    python3 word_syn.py "1/1/2001，999！翻译都要执行多个翻译系统，这带来巨大的计算成本。如今，许多领域都正在被神经网路技术颠覆。" -l p -p -v 80 -c
    python3 word_syn.py "1/01/1991，32。翻译都要执行多个翻译系统，这带来巨大的计算成本。如今，许多领域都正在被神经网路技术颠覆。" -l c -p -v 80 -c
"""

# LOGBK and PROBLEMS
"""
16 DEC - Done word-wav data in Can and Manderin
18 DEC - Done overall documentation
19 DEC - (ING) Class structure -> token -> multichar prob!
19 DEC - NSW Date conversion
23 DEC - Done crossfade
23 DEC - Updated cantonese phonedict (according to website and hkcan corpus per percentage)

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