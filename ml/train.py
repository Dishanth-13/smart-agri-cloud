"""
Train a RandomForest on the Kaggle Crop Recommendation dataset.
Expected CSV columns: N,P,K,temperature,humidity,pH,rainfall,label
Saves model to ml/models/crop_rf.joblib
"""
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
import joblib
import os

DATA_CSV = os.getenv('DATA_CSV', 'data/crop_recommendation.csv')
MODEL_PATH = os.getenv('MODEL_PATH', 'models/crop_rf.joblib')

def load_data(path):
    return pd.read_csv(path)

def train():
    df = load_data(DATA_CSV)
    X = df[['N','P','K','temperature','humidity','ph','rainfall']]
    y = df['label']
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    clf = RandomForestClassifier(n_estimators=100, random_state=42)
    clf.fit(X_train, y_train)
    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    joblib.dump(clf, MODEL_PATH)
    print('Model saved to', MODEL_PATH)

if __name__ == '__main__':
    train()
