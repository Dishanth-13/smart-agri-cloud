"""
Generate a minimal dummy RandomForest model for testing.
This is for demo purposes; train on real Kaggle data for production.
"""
import joblib
import os
from sklearn.ensemble import RandomForestClassifier
import numpy as np

os.makedirs('ml/models', exist_ok=True)

# Create a minimal trained model with dummy data
X_dummy = np.array([
    [50, 40, 35, 25.5, 65.0, 6.8, 100.0],
    [60, 45, 40, 26.0, 70.0, 7.0, 120.0],
    [40, 30, 30, 20.0, 50.0, 6.5, 80.0]
])
y_dummy = np.array(['Rice', 'Maize', 'Wheat'])

clf = RandomForestClassifier(n_estimators=10, random_state=42)
clf.fit(X_dummy, y_dummy)

joblib.dump(clf, 'ml/models/crop_rf.joblib')
print('✓ Dummy model saved to ml/models/crop_rf.joblib')
