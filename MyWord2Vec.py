import re
import os
from gensim.models import Word2Vec

def FindSentences(path):
    for root, dirList, fileList in os.walk(path):
        for f in fileList:
            if f.endswith('.c') or f.endswith('.cpp') or f.endswith('.h') or f.endswith('.hpp'):
                location = os.path.join(root, f)
                yield [re.split(r'[\\\.]', location)[-2]]
                for line in open(location, 'r'):
                    yield re.split(r'[\s\(\:]+', line)

def MyWord2Vec(path, vectorSize):
    sentences = []
    for sen in FindSentences(path):
        sentences.append(sen)
    model = Word2Vec(sentences, vector_size=vectorSize, min_count=1)
    return model.wv
