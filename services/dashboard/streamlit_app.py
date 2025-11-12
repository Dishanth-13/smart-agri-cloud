import os
import streamlit as st
import pandas as pd
import requests
from sqlalchemy import create_engine, text
from datetime import datetime

DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql+psycopg2://postgres:postgres@db:5432/smart_agri')
API_URL = os.getenv('API_URL', 'http://api:8000')

engine = create_engine(DATABASE_URL)

st.set_page_config(page_title='Smart Agri Dashboard', layout='wide')
st.title('🌾 Smart Agri Dashboard')

# Navigation tabs
tab1, tab2, tab3, tab4 = st.tabs(['📊 Readings', '🔮 Predictions', '🤖 Model Management', '📈 Analytics'])

st.sidebar.header('⚙️ Controls')
num = st.sidebar.number_input('Recent readings', min_value=1, max_value=500, value=20)

if st.sidebar.button('🔄 Refresh All'):
    st.rerun()

@st.cache_data(ttl=10)
def get_recent(n):
    with engine.connect() as conn:
        df = pd.read_sql('SELECT * FROM readings ORDER BY ts DESC LIMIT %s', conn, params=(n,))
    return df

@st.cache_data(ttl=10)
def get_models():
    """Fetch all registered models from API"""
    try:
        resp = requests.get(f'{API_URL}/models/list', timeout=5)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        st.warning(f'Failed to fetch models: {e}')
        return []

@st.cache_data(ttl=10)
def get_active_model():
    """Fetch active model from API"""
    try:
        resp = requests.get(f'{API_URL}/models/latest', timeout=5)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        st.warning(f'Failed to fetch active model: {e}')
        return None

df = get_recent(num)

# ============ TAB 1: READINGS ============
with tab1:
    st.subheader('📊 Recent Sensor Readings')
    st.dataframe(df, use_container_width=True)
    
    st.metric('Total Readings', len(df))
    col1, col2, col3 = st.columns(3)
    with col1:
        if 'temperature' in df.columns:
            st.metric('Avg Temperature (°C)', f"{df['temperature'].mean():.1f}")
    with col2:
        if 'humidity' in df.columns:
            st.metric('Avg Humidity (%)', f"{df['humidity'].mean():.1f}")
    with col3:
        if 'rainfall' in df.columns:
            st.metric('Total Rainfall (mm)', f"{df['rainfall'].sum():.1f}")

# ============ TAB 2: PREDICTIONS ============
with tab2:
    st.subheader('🔮 Predict from Latest Reading')
    
    col1, col2 = st.columns(2)
    with col1:
        farm_id = st.number_input('Farm ID', min_value=1, value=1)
    with col2:
        top_k = st.slider('Top K predictions', min_value=1, max_value=10, value=5)

    if st.button('🚀 Get Predictions', key='predict_btn'):
        with st.spinner('Requesting predictions...'):
            try:
                payload = {'farm_id': int(farm_id), 'top_k': int(top_k)}
                resp = requests.post(f'{API_URL}/predict', json=payload, timeout=10)
                resp.raise_for_status()
                data = resp.json()

                preds = data.get('predictions', [])
                if not preds:
                    st.info('No predictions returned from the API.')
                else:
                    # Normalize into DataFrame and ensure correct dtypes
                    df_preds = pd.DataFrame(preds)
                    if 'probability' in df_preds.columns:
                        df_preds['probability'] = df_preds['probability'].astype(float)
                    else:
                        df_preds['probability'] = 0.0

                    # Add 1-based ranking column and show table using rank as index (hides 0-based index)
                    df_preds.insert(0, 'rank', range(1, len(df_preds) + 1))
                    st.subheader(f'✅ Top {len(df_preds)} Predictions')
                    # use rank as the DataFrame index so Streamlit doesn't display the default 0-based index
                    st.table(df_preds.set_index('rank'))

                    # Graphical representation heading and bar chart of probabilities (crop -> probability)
                    st.subheader('📈 Graphical Representation')
                    try:
                        chart = df_preds.sort_values('probability', ascending=False).set_index('crop')['probability']
                        # remove non-positive probabilities (<= 0.0) from the graphical representation
                        chart = chart[chart > 0.0]
                        if chart.empty:
                            st.info('No positive probabilities to display in the chart.')
                        else:
                            st.bar_chart(chart)
                    except Exception:
                        # fallback if charting fails
                        pass

                    # Highlight best prediction
                    best = df_preds.sort_values('probability', ascending=False).iloc[0]
                    st.success(f"🌱 **Recommended crop:** {best['crop']} — Confidence: {best['probability']:.2%}")

            except requests.exceptions.RequestException as re:
                st.error(f'Network/API error: {re}')
            except Exception as e:
                st.error(f'Prediction error: {e}')

# ============ TAB 3: MODEL MANAGEMENT ============
with tab3:
    st.subheader('🤖 Model Registry & Management')
    
    # Fetch models
    models_list = get_models()
    active_model = get_active_model()
    
    # Active Model Section
    if active_model:
        st.success(f"✅ **Active Model:** {active_model.get('name')} (v{active_model.get('version', 'N/A')})")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric('Accuracy', f"{active_model.get('accuracy', 0):.2%}")
        with col2:
            st.metric('Version', active_model.get('version', 'N/A'))
        with col3:
            st.metric('ID', active_model.get('id', 'N/A'))
        with col4:
            created_at = active_model.get('created_at', 'N/A')
            st.metric('Created', created_at[:10] if isinstance(created_at, str) else 'N/A')
    else:
        st.warning('⚠️ No active model registered. Register a model to enable predictions.')
    
    st.divider()
    
    # Model History Section
    st.subheader('📚 Model Version History')
    
    if models_list and len(models_list) > 0:
        # Create DataFrame from models
        df_models = pd.DataFrame(models_list)
        
        # Format columns for display
        if 'created_at' in df_models.columns:
            df_models['created_at'] = pd.to_datetime(df_models['created_at']).dt.strftime('%Y-%m-%d %H:%M:%S')
        if 'accuracy' in df_models.columns:
            df_models['accuracy'] = df_models['accuracy'].apply(lambda x: f"{x:.2%}" if pd.notna(x) else "N/A")
        if 'active' in df_models.columns:
            df_models['status'] = df_models['active'].apply(lambda x: '✅ Active' if x else '⏸️ Inactive')
        
        # Display models table
        st.dataframe(df_models, use_container_width=True, hide_index=True)
        
        st.divider()
        
        # Model Rollback Section
        st.subheader('🔄 Activate Model Version')
        
        if len(models_list) > 1:
            # Allow selection from inactive models
            inactive_models = [m for m in models_list if not m.get('active')]
            
            if inactive_models:
                selected_model = st.selectbox(
                    'Select a model to activate:',
                    options=inactive_models,
                    format_func=lambda x: f"{x['name']} v{x.get('version', 'N/A')} (ID: {x['id']}) - Accuracy: {x.get('accuracy', 0):.2%}"
                )
                
                if st.button('🚀 Activate Selected Model', key='activate_model_btn'):
                    with st.spinner('Activating model...'):
                        try:
                            # Call API to activate (via re-registration with activate=true)
                            payload = {
                                'name': selected_model['name'],
                                'path': selected_model['path'],
                                'version': selected_model.get('version'),
                                'accuracy': selected_model.get('accuracy'),
                                'activate': True
                            }
                            resp = requests.post(f'{API_URL}/models/register', json=payload, timeout=10)
                            resp.raise_for_status()
                            st.success(f"✅ Model {selected_model['name']} v{selected_model.get('version')} activated!")
                            st.cache_data.clear()  # Clear cache to refresh models
                            st.rerun()
                        except Exception as e:
                            st.error(f'Failed to activate model: {e}')
            else:
                st.info('ℹ️ All models are currently active or only one model exists.')
        else:
            st.info('ℹ️ Only one model registered. Register more models to enable rollback.')
    else:
        st.info('ℹ️ No models registered yet. Register a model via the API to get started.')
        st.code("""
# Example: Register a model via API
curl -X POST http://localhost:8000/models/register \\
  -H "Content-Type: application/json" \\
  -d '{
    "name": "crop_rf",
    "path": "/app/models/crop_rf.joblib",
    "version": "v1",
    "accuracy": 0.9932,
    "activate": true
  }'
        """, language='bash')

# ============ TAB 4: ANALYTICS ============
with tab4:
    st.subheader('📈 System Analytics')
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric('Total Models Registered', len(models_list) if models_list else 0)
        st.metric('Active Model', f"{active_model.get('name', 'None')} v{active_model.get('version', 'N/A')}" if active_model else 'None')
    
    with col2:
        if active_model:
            st.metric('Active Model Accuracy', f"{active_model.get('accuracy', 0):.2%}")
        if models_list and len(models_list) > 0:
            best_accuracy = max([m.get('accuracy', 0) for m in models_list])
            st.metric('Best Model Accuracy', f"{best_accuracy:.2%}")
    
    st.divider()
    
    st.subheader('📊 Sensor Data Trends')
    
    if not df.empty and 'ts' in df.columns:
        # Convert ts to datetime if needed
        df_chart = df.copy()
        df_chart['ts'] = pd.to_datetime(df_chart['ts'])
        df_chart = df_chart.sort_values('ts')
        
        # Plot temperature trend
        if 'temperature' in df_chart.columns:
            st.line_chart(df_chart.set_index('ts')[['temperature']], use_container_width=True)
            st.caption('Temperature Trend')
        
        # Plot humidity trend
        if 'humidity' in df_chart.columns:
            st.line_chart(df_chart.set_index('ts')[['humidity']], use_container_width=True)
            st.caption('Humidity Trend')
        
        # Plot rainfall trend
        if 'rainfall' in df_chart.columns:
            st.bar_chart(df_chart.set_index('ts')[['rainfall']], use_container_width=True)
            st.caption('Rainfall Trend')
    else:
        st.info('No data available to display trends.')
    
    st.divider()
    
    st.subheader('ℹ️ System Information')
    col1, col2, col3 = st.columns(3)
    with col1:
        st.write(f'**API URL:** {API_URL}')
    with col2:
        st.write(f'**Database:** smart_agri')
    with col3:
        st.write(f'**Dashboard Updated:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')

