import random
import sys

def gen():
    # Read nouns from file
    with open('nouns.txt') as f:
        nouns = [line.strip() for line in f]
        
    nouns = list(filter(lambda x: len(x) > 1, nouns))

    # Read adjectives from file
    with open('adjectives.txt') as f:
        adjectives = [line.strip() for line in f]

    adjectives = list(filter(lambda x: len(x) > 1, adjectives))

    adjectives += nouns

    ret = ""
    adj1 = random.choice(adjectives)
    noun = random.choice(nouns)
    if adj1 in adjectives and adj1 in nouns:
        if random.random() < 0.2: # 20% chance of adding "-powered"
            adj1 += '-powered'
    ret += adj1 + " "
    if random.random() < 0.1:
        adj2 = random.choice(adjectives)
        if adj2 != adj1:
            ret += adj2 + " "
    ret += noun
    return ret

if __name__ == '__main__':
    n = 1
    if len(sys.argv) > 1:
        n = int(sys.argv[1])
    for i in range(n):
        print(gen())
