# Chin-concatTTS
Cantonese and Mandarin concatenation TTS system in Python <br>
For DNN TTS, please check https://github.com/kennethli319/Chin-dnnTTS<br> 
<br> 

# Usage
<br> 
New user please install the following external modules: <br> 
    pip install -U pycantonese<br> 
    pip install opencc-python-reimplemented<br> 
    pip install pkuseg<br> 
<br> 
<b>Usage: </b> <br> 
    python word_syn.py <"input sequence"> <-language c or p> <-play> <-volume 0-100> <-crossfade> <-outfile filename> <br> 

<br> 
<b>Example: </b> <br> 
    python3 word_syn.py "1/1/2001，999！翻译都要执行多个翻译系统，这带来巨大的计算成本。如今，许多领域都正在被神经网路技术颠覆。" -l p -p -v 80 -c -o output_mandarin.wav<br> 
    <a href="https://drive.google.com/open?id=16t2mE66eJdZEL4jB1_h01Q__zcg5vUax"> output_mandarin.wav </a> <br>
    python3 word_syn.py "1/01/1991，32。翻译都要执行多个翻译系统，这带来巨大的计算成本。如今，许多领域都正在被神经网路技术颠覆。" -l c -p -v 80 -c -o output_cantonese.wav<br> 
    <a href="https://drive.google.com/open?id=10DRGh6Lf3ABBM9Kj1bSCjM2qj7sjRhr6"> output_cantonese.wav </a> <br>
    
"""<br> 
<br> 
# LOGBK and PROBLEMS
"""<br> 
16 DEC - Done word-wav data in Can and Manderin<br> 
18 DEC - Done overall documentation<br> 
19 DEC - (ING) Class structure -> token -> multichar prob!<br> 
19 DEC - NSW Date conversion<br> 
23 DEC - Done crossfade<br> 
23 DEC - Updated cantonese phonedict (according to website and hkcan corpus per percentage)<br> 
<br> 
1 - [DONE-23dec] check sim chin / tran chin+ convert
2 - [DONE-23dec] cantonese corpus = very slow -> change it to a txt file with count / % only <br> 
3 - [DONE-18dec] change chin char (simplified chinese vs traditional chinese)<br> 
4 - [H-DONE-18dec] word seg: use pku module, but not yet merge to the structure<br> 
5 - POS tag<br> 
5 - multi pronouncaition for the same word -> depends on the previous history : can be solve by POS + history(or word seg token)<br> 
""" <br> 
<br> 
# Pipeline
"""<br> 
STRUCTURE<br> 
1 - CLASS:  Sequence:    sequence<br> 
            Char:   char info<br> 
                    i)      Char<br> 
                    ii)     CV - onset, n, coda<br> 
                    iii)    Tone<br> 
<br> 
PROCEDURE<br> 
[PREPARE]<br> 
0 - Import necessary libraries<br> 
1 - Argv management and declear global variables<br> 
2 - Define Methods and Classes<br> 
    2.1 - Methods<br> 
    2.2 - Classes<br> 
[MAIN]<br> 
3 - Frontend :<br> 
    3.1 - Get sequence<br> 
    3.2 - Normalization -> remove (unnecessary) punct, change all remaining punct to 全/半形<br> 
    3.3 - Classify cantonese / mandarin / english / mixture<br> 
    3.4 - Word seg -> to tokens<br> 
    3.5 - POS of token seq<br> 
    3.6 - Based on POS -> check the phones/words/diphones (from dict)<br> 
    3.7 - Change the phone/diphone/word-pron seq according to Consonant-Vowel Coarticulation rules in that lang<br> 
    3.8 - Intonation<br> 
    3.9 - <br> 
4 - Waveform Generation<br> 
    4.1 - WORD UNIT VERION<br> 
        4.1.1 - load all required word wav<br> 
        4.1.2 - smoothing on boundaries?<br> 
        4.1.3 - output fine tune: eg volume/speed 1x 1.5x 2x?<br> 
    4.2 - DIPHONE UNIT VERSION<br> 
5 - Output<br> 
    5.1 - Output wav<br> 
    5.2 - Output all relations<br> 
    5.3 - Output all parameters<br> 
    5.4 - Output full info
