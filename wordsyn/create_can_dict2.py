import re
import json

word2phone = dict([])
wordlist = list()

with open('output2.txt', 'r') as f:

    lines = f.readlines()

    for eachline in lines:
        wordlist = eachline.split()
        
        phone = wordlist[1]
        words = wordlist[0]

        for eachword in words:

            if eachword in word2phone.keys():
            # append to the existing array at this slot
                word2phone[eachword].append(phone)
            else:
            # create a new array in this slot
                word2phone[eachword] = [phone]

# outfile = open('phonedict_dict', 'w+')
# outfile = open('phonedict_dict_pth', 'w+')
outfile = open('phonedict_dict_can', 'w+')
outfile.write(json.dumps(word2phone))
