#!/usr/bin/env python

import random

from scapy.all import sendp
from scapy.all import Ether


def random_sentence():
    nouns = ("puppy", "car", "rabbit", "girl", "monkey")
    verbs = ("runs", "hits", "jumps", "drives", "barfs") 
    adv = ("crazily. ", "dutifully. ", "foolishly. ", "merrily. ", "occasionally. ")
    adj = ("adorable", "clueless", "dirty", "odd", "stupid")
    l = [nouns, verbs, adj, adv]
    sentence = ' '.join([random.choice(i) for i in l])
    while len(sentence) < 100:
        sentence += ' '.join([random.choice(i) for i in l])
    return sentence

def main():
    payload = random_sentence()
    pkt = Ether(dst='00:04:00:00:00:01', type=0x1234) / payload
    pkt.show()
    sendp(pkt)

if __name__ == '__main__':
    main()
