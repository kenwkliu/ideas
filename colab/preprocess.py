import re

import nltk
nltk.download('stopwords')
nltk.download('wordnet')
nltk.download('omw-1.4')
from nltk.corpus import stopwords

wnl = nltk.WordNetLemmatizer()
stop_words = set(stopwords.words('english'))

def _removeSymbols(text):
    removeSymRx = re.compile('\W')
            
    return re.sub(removeSymRx, " ", text)    

    
def _stem(text):
    stemmed_words = []
    #  am, are, is -> be
    # car, cars, car's, cars' -> car
    for t in text.split():
        lemmatized = wnl.lemmatize(t)
        if (len(lemmatized) > 1 and lemmatized.isdigit() == False):
            stemmed_words.append(lemmatized)

    return ' '.join(stemmed_words)
    

def _subWholeText(subText, text):
    for k, v in subText.items():
        text = re.sub(r"\b%s\b" % k, v, text)
        # r"\b%s\b"% enables replacing by whole word matches only
    return text

    
def _subText(subText, text):
    for k in subText:
        text = text.replace(k, subText[k])
        
    return text
    
    
def _stop(text):
    stopped_words = []

    for t in text.split():
        if (t not in stop_words):
            stopped_words.append(t)

    return ' '.join(stopped_words)


def process(text):
    # remove symbols
    text = _removeSymbols(text)

    # To lower case
    text = text.lower()

    # Stem the words
    text = _stem(text)
    
    #remove stop words
    text = _stop(text)

    return text