import re
import json

word2phone = dict([])
wordlist = list()

# with open('phonedict', 'r') as f:
with open('phonedict_pth', 'r') as f:

    lines = f.readlines()

    for eachline in lines:
        eachline = re.sub(', ', ' ', eachline) # split words by space instead of comma
        eachline = re.sub('\t', ' ', eachline) # turn the tab to space (all split by space now)
        wordlist = eachline.split()
        
        phone = wordlist[0]
        words = wordlist[1:]

        for eachword in words:

            if eachword in word2phone.keys():
            # append to the existing array at this slot
                word2phone[eachword].append(phone)
            else:
            # create a new array in this slot
                word2phone[eachword] = [phone]

# outfile = open('phonedict_dict', 'w+')
outfile = open('phonedict_dict_pth', 'w+')
outfile.write(json.dumps(word2phone))
