import re
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize

import nltk
nltk.download('punkt')
nltk.download('stopwords')
STOP_WORDS = set(stopwords.words('english'))
def preprocess_text(text: str) -> str:
   text = text.lower()  # lowercasing
   text = re.sub(r'\s+', ' ', text)  # remove extra spaces
   text = re.sub(r'[^a-z0-9\s]', '', text)  # remove punctuation
   tokens = word_tokenize(text)
   tokens = [t for t in tokens if t not in STOP_WORDS]
   return " ".join(tokens)
