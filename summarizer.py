from nltk.corpus import stopwords
from nltk.cluster.util import cosine_distance
import numpy as np
import networkx as nx
import os
import nltk

# init
req = [nltk.download(i) for i in ['punkt', 'stopwords', 'cosine_distance']]

# clear terminal
os.system('clear')

def read_article(file_name):
    print('[+] Reading file...')
    with open(file_name, 'r') as f:
        filedata = f.read()
    if not filedata:
        return []
    article = filedata.split(". ")
    sentences = []

    for sentence in article:
        sentences.append(sentence.replace("[^a-zA-Z]", " ").split(" "))
    sentences.pop() 
    
    return sentences


def sentence_similarity(sent1, sent2, stopwords=None):
    print('[+] Finding similarities...')
    if stopwords is None:
        stopwords = []
 
    sent1 = [w.lower() for w in sent1]
    sent2 = [w.lower() for w in sent2]
 
    all_words = list(set(sent1 + sent2))
 
    vector1 = [0] * len(all_words)
    vector2 = [0] * len(all_words)

    for w in sent1:
        if w in stopwords:
            continue
        vector1[all_words.index(w)] += 1

    for w in sent2:
        if w in stopwords:
            continue
        vector2[all_words.index(w)] += 1
 
    return 1 - cosine_distance(vector1, vector2)
 
def build_similarity_matrix(sentences, stop_words):
    print('[+] Building sentence structure...')
    print('[+] Building sentence matrix...')
    similarity_matrix = np.zeros((len(sentences), len(sentences)))
 
    for idx1 in range(len(sentences)):
        for idx2 in range(len(sentences)):
            if idx1 == idx2:
                continue 
            similarity_matrix[idx1][idx2] = sentence_similarity(sentences[idx1], sentences[idx2], stop_words)

    return similarity_matrix

def generate_summary(file_name, top_n=5):
    print('[+] Generating sentence...')
    stop_words = stopwords.words('english')
    summarize_text = []
    sentences =  read_article(file_name)
    sentence_similarity_martix = build_similarity_matrix(sentences, stop_words)
    sentence_similarity_graph = nx.from_numpy_array(sentence_similarity_martix)
    scores = nx.pagerank(sentence_similarity_graph)

    ranked_sentence = sorted(((scores[i],s) for i,s in enumerate(sentences)), reverse=True)    

    for i in range(top_n):
        summarize_text.append(" ".join(ranked_sentence[i][1]))

    with open(file_name, 'w') as file:
        file.write('. '.join(summarize_text))

# 开始分析
try:
    generate_summary("/Users/jerryhu/Desktop/sentence.txt", 2)
except Exception as er:
    print('\nCannot summarize or cannot find file sentence.txt on Desktop, or file not readable.\n')