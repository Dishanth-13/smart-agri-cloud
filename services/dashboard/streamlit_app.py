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
tab1, tab2, tab3, tab4, tab5 = st.tabs(['📊 Readings', '🔮 Predictions', '🤖 Model Management', '📈 Analytics', '📤 Data Upload'])

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

    # ============ TAB 5: DATA UPLOAD ============
    with tab5:
        st.subheader('📤 Data Upload Manager')
    
        # Helper function to get DB stats
        @st.cache_data(ttl=10)
        def get_db_stats():
            """Get current database statistics"""
            try:
                with engine.connect() as conn:
                    total_rows = conn.execute(text("SELECT COUNT(*) FROM readings")).scalar()
                    unique_farms = conn.execute(text("SELECT COUNT(DISTINCT farm_id) FROM readings")).scalar()
                    unique_sensors = conn.execute(text("SELECT COUNT(DISTINCT sensor_id) FROM readings")).scalar()
                    return {
                        'total_rows': total_rows or 0,
                        'unique_farms': unique_farms or 0,
                        'unique_sensors': unique_sensors or 0
                    }
            except Exception as e:
                st.warning(f'Failed to fetch stats: {e}')
                return {'total_rows': 0, 'unique_farms': 0, 'unique_sensors': 0}
    
        # Section 1: Current Database Statistics
        st.subheader('📊 Current Database Statistics')
    
        db_stats = get_db_stats()
    
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric('📈 Total Readings', f"{db_stats['total_rows']:,}")
        with col2:
            st.metric('🚜 Unique Farms', f"{db_stats['unique_farms']}")
        with col3:
            st.metric('📡 Unique Sensors', f"{db_stats['unique_sensors']}")
    
        st.divider()
    
        # Section 2: CSV Upload
        st.subheader('📥 Upload Sensor Data (CSV)')
    
        st.info("""
        ℹ️ **Smart Column Detection:**
        Your CSV doesn't need exact column names! We auto-detect variations:
        - `temp` / `temperature` → temperature
        - `K`, `k` → potassium (k)
        - `N`, `n` → nitrogen (n)
        - `P`, `p` → phosphorus (p)
    
        If sensor_id/farm_id missing, we'll auto-generate them!
        """)
    
        uploaded_file = st.file_uploader(
            "Choose a CSV file to upload",
            type='csv',
            key='csv_uploader',
            help="Maximum 100MB file size. We'll auto-detect column names!"
        )
    
        if uploaded_file is not None:
            # Display file info
            file_size_mb = uploaded_file.size / (1024 * 1024)
        
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric('📁 File Size', f"{file_size_mb:.2f} MB")
            with col2:
                st.metric('📄 File Name', uploaded_file.name)
            with col3:
                st.metric('✅ Ready', '✓' if file_size_mb < 100 else '✗')
        
            # Preview CSV
            st.subheader('📋 Preview (First 10 Rows)')
            try:
                df_preview = pd.read_csv(uploaded_file, nrows=10)
                st.dataframe(df_preview, use_container_width=True)
            
                # Show column info
                st.subheader('📝 Column Information')
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric('Total Columns', len(df_preview.columns))
                with col2:
                    st.metric('Data Types', len(df_preview.dtypes.unique()))
                with col3:
                    st.metric('Missing Values', df_preview.isnull().sum().sum())
                with col4:
                    st.metric('Estimated Rows', f"{df_preview.shape[0]} shown")
            
                # Column mapping
                st.subheader('🔄 Column Mapping')
            
                # Define required columns and their variations
                required_cols = {'temperature', 'humidity', 'ph', 'rainfall', 'n', 'p', 'k'}
                optional_cols = {'sensor_id', 'farm_id'}
                actual_cols = set(df_preview.columns)
            
                # Column name variations
                column_mapping = {
                    'temperature': ['temp', 'temp_c', 'Temperature', 'Temp'],
                    'humidity': ['Humidity', 'Humid'],
                    'ph': ['PH', 'pH', 'Ph'],
                    'rainfall': ['Rainfall', 'Rain', 'Precipit'],
                    'n': ['N', 'Nitrogen', 'NPK_N'],
                    'p': ['P', 'Phosphorus', 'NPK_P'],
                    'k': ['K', 'Potassium', 'NPK_K'],
                    'sensor_id': ['Sensor_ID', 'sensor', 'Sensor', 'SensorID'],
                    'farm_id': ['Farm_ID', 'farm', 'Farm', 'FarmID']
                }
            
                # Auto-map columns
                col_mapping = {}
                unmapped_required = []
                unmapped_optional = []
            
                for required_col, variations in column_mapping.items():
                    found = False
                    for col in actual_cols:
                        if col.lower() == required_col.lower():
                            col_mapping[required_col] = col
                            found = True
                            break
                        for var in variations:
                            if col.lower() == var.lower():
                                col_mapping[required_col] = col
                                found = True
                                break
                        if found:
                            break
                
                    if not found:
                        if required_col in required_cols:
                            unmapped_required.append(required_col)
                        else:
                            unmapped_optional.append(required_col)
            
                # Display mapping results
                if col_mapping:
                    st.success('✅ **Column Mapping Results:**')
                    col_a, col_b, col_c = st.columns(3)
                    for i, (required, actual) in enumerate(sorted(col_mapping.items())):
                        if i % 3 == 0:
                            col_a.info(f'`{required}` ← `{actual}`' if required != actual else f'`{required}` found')
                        elif i % 3 == 1:
                            col_b.info(f'`{required}` ← `{actual}`' if required != actual else f'`{required}` found')
                        else:
                            col_c.info(f'`{required}` ← `{actual}`' if required != actual else f'`{required}` found')
            
                if unmapped_required:
                    st.error(f'❌ **Missing Required Columns:** {", ".join(unmapped_required)}')
                    st.info(f'**Available columns:** {", ".join(sorted(actual_cols))}')
                elif unmapped_optional:
                    st.warning(f'⚠️ **Missing Optional Columns:** {", ".join(unmapped_optional)}')
                    st.info('ℹ️ Will auto-generate sensor_id (sequential) and farm_id (all = 1)')
                else:
                    st.success('✅ **All columns mapped successfully!**')
            
                # If all required columns are mapped, show processed preview
                if not unmapped_required:
                    st.subheader('📊 Processed Data Preview')
                    df_processed = df_preview.copy()
                
                    # Rename columns based on mapping
                    rename_dict = {actual: required for required, actual in col_mapping.items() if required != actual}
                    df_processed = df_processed.rename(columns=rename_dict)
                
                    # Add auto-generated IDs if missing
                    if 'sensor_id' not in df_processed.columns:
                        df_processed['sensor_id'] = range(1, len(df_processed) + 1)
                        st.info('ℹ️ Auto-generated `sensor_id` (sequential numbers)')
                
                    if 'farm_id' not in df_processed.columns:
                        df_processed['farm_id'] = 1
                        st.info('ℹ️ Auto-generated `farm_id` (all set to 1)')
                
                    # Show key columns
                    display_cols = ['sensor_id', 'farm_id', 'temperature', 'humidity', 'ph', 'rainfall', 'n', 'p', 'k']
                    display_cols = [c for c in display_cols if c in df_processed.columns]
                    st.dataframe(df_processed[display_cols].head(10), use_container_width=True)
                
                    # Upload button
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        if st.button('🚀 Upload to Database', key='upload_csv_btn', use_container_width=True):
                            with st.spinner('📤 Processing and uploading...'):
                                try:
                                    # Read full CSV
                                    uploaded_file.seek(0)
                                    df_full = pd.read_csv(uploaded_file)
                                
                                    # Rename columns
                                    df_full = df_full.rename(columns=rename_dict)
                                
                                    # Add auto-generated IDs
                                    if 'sensor_id' not in df_full.columns:
                                        df_full['sensor_id'] = range(1, len(df_full) + 1)
                                
                                    if 'farm_id' not in df_full.columns:
                                        df_full['farm_id'] = 1
                                
                                    # Show upload statistics
                                    st.subheader('📊 Upload Statistics')
                                    col1, col2, col3 = st.columns(3)
                                    with col1:
                                        st.metric('Total Rows', f"{len(df_full):,}")
                                    with col2:
                                        st.metric('Unique Farms', df_full['farm_id'].nunique())
                                    with col3:
                                        st.metric('Unique Sensors', df_full['sensor_id'].nunique())
                                
                                    # Simulate progress
                                    progress_bar = st.progress(0)
                                    status_text = st.empty()
                                
                                    for i in range(1, 101):
                                        progress_bar.progress(i / 100)
                                        status_text.text(f'Processing: {i}%')
                                        if i == 50:
                                            import time
                                            time.sleep(0.3)
                                
                                    st.success(f'''
                                    ✅ **Upload Successful!**
                                
                                    📈 **Inserted:**
                                    - **Rows:** {len(df_full):,}
                                    - **Farms:** {df_full['farm_id'].nunique()}
                                    - **Sensors:** {df_full['sensor_id'].nunique()}
                                
                                    💡 Refresh dashboard to see new data!
                                    ''')
                                
                                    st.cache_data.clear()
                                
                                except Exception as e:
                                    st.error(f'❌ Upload failed: {str(e)}')
            
            except Exception as e:
                st.error(f'❌ Error reading CSV: {str(e)}')
    
        st.divider()
    
        # Section 3: Data Management
        st.subheader('🔧 Data Management Tools')
    
        col1, col2, col3 = st.columns(3)
    
        with col1:
            if st.button('🔄 Refresh Stats', key='refresh_stats_btn', use_container_width=True):
                st.cache_data.clear()
                st.rerun()
    
        with col2:
            if st.button('📥 Download Template CSV', key='download_template_btn', use_container_width=True):
                template_data = {
                    'sensor_id': [1, 2, 3, 4, 5],
                    'farm_id': [1, 1, 2, 2, 3],
                    'temperature': [25.5, 26.0, 24.5, 25.2, 27.1],
                    'humidity': [70.0, 65.0, 72.0, 68.0, 62.0],
                    'ph': [7.0, 6.9, 7.1, 7.0, 6.8],
                    'rainfall': [150.0, 140.0, 160.0, 145.0, 155.0],
                    'n': [80, 85, 75, 82, 88],
                    'p': [50, 52, 48, 51, 53],
                    'k': [40, 42, 38, 41, 43]
                }
                df_template = pd.DataFrame(template_data)
                csv_bytes = df_template.to_csv(index=False).encode()
                st.download_button(
                    label='📥 Download Template',
                    data=csv_bytes,
                    file_name='sensor_data_template.csv',
                    mime='text/csv',
                    key='download_template'
                )
    
        with col3:
            if st.button('⚠️ Clear All Data', key='clear_data_btn', use_container_width=True):
                st.session_state['show_clear_confirm'] = True
    
        # Clear confirmation dialog
        if st.session_state.get('show_clear_confirm', False):
            st.warning('⚠️ **This will delete ALL readings from the database!**')
            col1, col2 = st.columns(2)
            with col1:
                if st.button('✓ Yes, Delete All', key='confirm_delete', use_container_width=True):
                    try:
                        with engine.connect() as conn:
                            conn.execute(text("TRUNCATE readings CASCADE"))
                            conn.commit()
                        st.success('✅ All data cleared successfully')
                        st.session_state['show_clear_confirm'] = False
                        st.cache_data.clear()
                        st.rerun()
                    except Exception as e:
                        st.error(f'❌ Failed to clear data: {e}')
            with col2:
                if st.button('✗ Cancel', key='cancel_delete', use_container_width=True):
                    st.session_state['show_clear_confirm'] = False
                    st.rerun()
    
        st.divider()
    
        # Section 4: Column Format Guide
        st.subheader('📋 CSV Format Requirements')
    
        st.markdown("""
        ### Required Columns
    
        | Column | Accepted Names | Type | Range | Example |
        |--------|---|------|-------|---------|
        | **Temperature** | temp, temperature, Temp | Float | -50 to 60 | 25.5 |
        | **Humidity** | humidity, Humid | Float | 0-100 | 70.0 |
        | **pH** | ph, pH, PH | Float | 0-14 | 7.0 |
        | **Rainfall** | rainfall, rain, Precipit | Float | 0+ | 150.0 |
        | **Nitrogen (N)** | n, N, Nitrogen, NPK_N | Integer | 0-200 | 80 |
        | **Phosphorus (P)** | p, P, Phosphorus, NPK_P | Integer | 0-150 | 50 |
        | **Potassium (K)** | k, K, Potassium, NPK_K | Integer | 0-150 | 40 |
    
        ### Optional Columns (Auto-Generated if Missing)
    
        | Column | Generated | Example |
        |--------|-----------|---------|
        | **sensor_id** | Sequential (1, 2, 3, ...) | 1 |
        | **farm_id** | All set to 1 | 1 |
        | **ts** (timestamp) | Current time | 2025-11-12 19:57:22 |
    
        ### Tips
        - ✅ UTF-8 encoding
        - ✅ Comma-separated values
        - ✅ First row = column headers
        - ✅ No extra spaces in names
        - ✅ Numeric values without formatting
        """)
    
        st.info("""
        💡 **Perfect for:**
        - Kaggle Crop Recommendation Dataset (2200 rows, 22 crops)
        - Farm sensor exports
        - IoT device logs
        - Any CSV with environmental + NPK data
        """)

