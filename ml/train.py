"""
Train a RandomForest on the Kaggle Crop Recommendation dataset.
Expected CSV columns: N,P,K,temperature,humidity,pH,rainfall,label
Saves model to ml/models/crop_rf.joblib
"""
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, classification_report
from sklearn.preprocessing import StandardScaler
import joblib
import os

# Get the directory where this script is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

DATA_CSV = os.getenv('DATA_CSV', os.path.join(SCRIPT_DIR, 'data', 'crop_recommendation.csv'))
MODEL_PATH = os.getenv('MODEL_PATH', os.path.join(SCRIPT_DIR, 'models', 'crop_rf.joblib'))

def load_data(path):
    """Load CSV data - handles case variations"""
    if os.path.exists(path):
        return pd.read_csv(path)
    
    # Try case-insensitive match for Windows
    dir_path = os.path.dirname(path) or '.'
    filename = os.path.basename(path)
    
    if os.path.exists(dir_path):
        for file in os.listdir(dir_path):
            if file.lower() == filename.lower():
                full_path = os.path.join(dir_path, file)
                print(f"📝 Found file: {full_path}")
                return pd.read_csv(full_path)
    
    raise FileNotFoundError(f"Dataset not found at {path}")

def train():
    """Train RandomForest model on crop recommendation data"""
    print("🌾 Starting ML Model Training...")
    print(f"📂 Loading dataset from: {DATA_CSV}")
    
    # Load data
    df = load_data(DATA_CSV)
    print(f"✅ Loaded {len(df)} samples")
    print(f"📊 Dataset columns: {df.columns.tolist()}")
    
    # Prepare features and target
    feature_columns = ['N', 'P', 'K', 'temperature', 'humidity', 'ph', 'rainfall']
    X = df[feature_columns]
    y = df['label']
    
    print(f"🎯 Target classes: {y.unique()}")
    print(f"📈 Features: {feature_columns}")
    
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    print(f"\n📊 Training set: {len(X_train)} samples")
    print(f"📊 Test set: {len(X_test)} samples")
    
    # Train model
    print("\n⏳ Training RandomForest Classifier...")
    clf = RandomForestClassifier(
        n_estimators=150,
        max_depth=20,
        min_samples_split=5,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=-1,
        verbose=1
    )
    clf.fit(X_train, y_train)
    
    # Evaluate model
    print("\n📊 Evaluating Model...")
    y_pred_train = clf.predict(X_train)
    y_pred_test = clf.predict(X_test)
    
    train_accuracy = accuracy_score(y_train, y_pred_train)
    test_accuracy = accuracy_score(y_test, y_pred_test)
    
    print(f"\n✅ Training Accuracy: {train_accuracy:.4f}")
    print(f"✅ Test Accuracy: {test_accuracy:.4f}")
    print(f"✅ Precision: {precision_score(y_test, y_pred_test, average='weighted'):.4f}")
    print(f"✅ Recall: {recall_score(y_test, y_pred_test, average='weighted'):.4f}")
    print(f"✅ F1-Score: {f1_score(y_test, y_pred_test, average='weighted'):.4f}")
    
    # Feature importance
    print("\n📊 Top 5 Important Features:")
    feature_importance = pd.DataFrame({
        'feature': feature_columns,
        'importance': clf.feature_importances_
    }).sort_values('importance', ascending=False)
    
    for idx, row in feature_importance.head().iterrows():
        print(f"   {row['feature']}: {row['importance']:.4f}")
    
    # Classification report
    print("\n📋 Classification Report:")
    print(classification_report(y_test, y_pred_test))
    
    # Save model
    os.makedirs(os.path.dirname(MODEL_PATH) or '.', exist_ok=True)
    joblib.dump(clf, MODEL_PATH)
    print(f"\n💾 Model saved to: {MODEL_PATH}")
    print(f"📦 Model file size: {os.path.getsize(MODEL_PATH) / 1024:.2f} KB")
    
    return clf, test_accuracy

if __name__ == '__main__':
    try:
        train()
        print("\n🎉 Training completed successfully!")
    except Exception as e:
        print(f"\n❌ Error during training: {e}")
        import traceback
        traceback.print_exc()
