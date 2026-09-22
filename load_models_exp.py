# Load saved model and tokenizer
from tensorflow.keras.models import load_model
import numpy as np
import tensorflow as tf
import pickle

from sklearn.preprocessing import LabelEncoder
from tensorflow.keras.preprocessing.text import Tokenizer
from tensorflow.keras.preprocessing.sequence import pad_sequences
from lime.lime_text import LimeTextExplainer
# Load the model
final_model = load_model("cnn_gru_1.h5")

# Load the tokenizer
with open("cnn_gru_tokenizer_1.pkl", "rb") as f:
    tokenizer = pickle.load(f)

with open("train_data.pkl", "rb") as f:
    train_data = pickle.load(f)

patterns = []
labels = []
responses = {}
for item in train_data:
    intent = item['intent']
    responses[intent] = item['response']
    for pattern in item['text']:
        patterns.append(pattern)
        labels.append(intent)

word_index = tokenizer.word_index
sequences = tokenizer.texts_to_sequences(patterns)

# Pad sequences
max_len = 30
#max(len(seq) for seq in sequences)
padded_sequences = pad_sequences(sequences, maxlen=max_len, padding='post')

# Encode the labels
label_encoder = LabelEncoder()
encoded_labels = label_encoder.fit_transform(labels)

# Create an explainer
explainer = LimeTextExplainer(class_names=label_encoder.classes_)

# Define a prediction function
def predict_probabilities(texts):
    sequences = tokenizer.texts_to_sequences(texts)
    padded_sequences = pad_sequences(sequences, maxlen=max_len, padding='post')
    return final_model.predict(padded_sequences)
