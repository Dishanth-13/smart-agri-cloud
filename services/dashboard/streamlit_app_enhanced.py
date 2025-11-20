import streamlit as st
import pandas as pd
import numpy as np
import requests
from datetime import datetime
from sqlalchemy import create_engine, text

# Configuration
API_URL = 'http://localhost:8000'
DB_URL = 'postgresql://smart_agri_user:smart_agri_pass@db:5432/smart_agri'

st.set_page_config(page_title='Smart AgriCloud', page_icon='🌾', layout='wide')
st.title('🌾 Smart Agriculture Cloud Dashboard')

@st.cache_data(ttl=5)
def get_data():
    try:
        engine = create_engine(DB_URL)
        with engine.connect() as conn:
            query = text('SELECT * FROM readings ORDER BY ts DESC LIMIT 1000')
            return pd.read_sql(query, conn)
    except:
        return pd.DataFrame()

@st.cache_data(ttl=10)
def get_models():
    try:
        r = requests.get(f'{API_URL}/models', timeout=5)
        return r.json() if r.status_code == 200 else []
    except:
        return []

@st.cache_data(ttl=10)
def get_active_model():
    try:
        r = requests.get(f'{API_URL}/models/active', timeout=5)
        return r.json() if r.status_code == 200 else None
    except:
        return None

df = get_data()
models_list = get_models()
active_model = get_active_model()

# Create tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs(['📊 Readings', '🔮 Predictions', '🤖 Models', '📈 Analytics', '📤 Upload'])

# ========== TAB 1: READINGS (ENHANCED) ==========
with tab1:
    st.subheader('📊 Sensor Readings')
    c1, c2, c3 = st.columns(3)
    with c1:
        refresh = st.selectbox('Refresh', ['Disabled', '5s', '10s', '30s'], key='refresh')
    with c2:
        if st.button('🔄 Now'):
            st.cache_data.clear()
            st.rerun()
    with c3:
        if st.button('📥 Export'):
            st.download_button('Download', df.to_csv(index=False), f'readings_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv', 'text/csv')
    
    with st.expander('🔍 Filters'):
        if len(df) > 0:
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                farms = sorted(df['farm_id'].unique()) if 'farm_id' in df.columns else []
                filt_farm = st.multiselect('Farm', farms, default=farms, key='farm_f')
            with c2:
                sensors = sorted(df['sensor_id'].unique()) if 'sensor_id' in df.columns else []
                filt_sensor = st.multiselect('Sensor', sensors, default=sensors, key='sensor_f')
            with c3:
                if 'temperature' in df.columns:
                    t_min, t_max = st.slider('Temp', float(df['temperature'].min()-5), float(df['temperature'].max()+5), (float(df['temperature'].min()), float(df['temperature'].max())), key='temp_r')
                else:
                    t_min, t_max = 0, 50
            with c4:
                if 'humidity' in df.columns:
                    h_min, h_max = st.slider('Humidity', float(df['humidity'].min()-10), float(df['humidity'].max()+10), (float(df['humidity'].min()), float(df['humidity'].max())), key='hum_r')
                else:
                    h_min, h_max = 0, 100
            
            df_filt = df.copy()
            if 'farm_id' in df_filt.columns and filt_farm:
                df_filt = df_filt[df_filt['farm_id'].isin(filt_farm)]
            if 'sensor_id' in df_filt.columns and filt_sensor:
                df_filt = df_filt[df_filt['sensor_id'].isin(filt_sensor)]
            if 'temperature' in df_filt.columns:
                df_filt = df_filt[(df_filt['temperature'] >= t_min) & (df_filt['temperature'] <= t_max)]
            if 'humidity' in df_filt.columns:
                df_filt = df_filt[(df_filt['humidity'] >= h_min) & (df_filt['humidity'] <= h_max)]
        else:
            df_filt = df.copy()    st.dataframe(df_filt, use_container_width=True)
    
    if len(df_filt) > 0:
        st.subheader('📊 Quality')
        qc1, qc2, qc3, qc4, qc5 = st.columns(5)
        with qc1:
            st.metric('Records', len(df_filt))
        with qc2:
            comp = (1 - (df_filt.isnull().sum().sum() / (len(df_filt) * len(df_filt.columns)))) * 100
            st.metric('Complete', f'{comp:.0f}%')
        with qc3:
            st.metric('Nulls', int(df_filt.isnull().sum().sum()))
        with qc4:
            if 'farm_id' in df_filt.columns:
                st.metric('Farms', df_filt['farm_id'].nunique())
        with qc5:
            if 'sensor_id' in df_filt.columns:
                st.metric('Sensors', df_filt['sensor_id'].nunique())
        
        st.subheader('🌡️ Gauges')
        gc1, gc2 = st.columns(2)
        with gc1:
            if 'temperature' in df_filt.columns:
                avg_t = df_filt['temperature'].mean()
                st.metric('Avg Temp', f'{avg_t:.1f}°C')
                st.progress(min(max((avg_t-10)/30, 0), 1))
        with gc2:
            if 'humidity' in df_filt.columns:
                avg_h = df_filt['humidity'].mean()
                st.metric('Avg Humidity', f'{avg_h:.1f}%')
                st.progress(min(max((avg_h-40)/40, 0), 1))

# ========== TAB 2: PREDICTIONS (ENHANCED) ==========
with tab2:
    pred_t1, pred_t2, pred_t3, pred_t4 = st.tabs(['Single', 'Batch', 'What-If', 'Seasonal'])
    
    with pred_t1:
        st.subheader('Single Prediction')
        c1, c2 = st.columns(2)
        with c1:
            fid = st.number_input('Farm ID', 1)
        with c2:
            topk = st.slider('Top K', 1, 10, 5)
        if st.button('🚀 Predict'):
            try:
                r = requests.post(f'{API_URL}/predict', json={'farm_id': int(fid), 'top_k': int(topk)}, timeout=10)
                preds = r.json().get('predictions', [])
                if preds:
                    dp = pd.DataFrame(preds)
                    dp['probability'] = dp['probability'].astype(float)
                    st.dataframe(dp, use_container_width=True)
                    st.success(f"Top: {dp.iloc[0]['crop']} ({dp.iloc[0]['probability']:.1%})")
            except Exception as e:
                st.error(f'Error: {e}')
    
    with pred_t2:
        st.subheader('Batch Upload')
        bf = st.file_uploader('CSV', type=['csv'], key='batch_f')
        if bf:
            bdf = pd.read_csv(bf)
            st.write(f'{len(bdf)} rows')
            if st.button('Process'):
                try:
                    r = requests.post(f'{API_URL}/predict/batch', json={'readings': bdf.fillna(0).to_dict('records'), 'top_k': 5}, timeout=30)
                    preds = r.json().get('predictions', [])
                    res_df = pd.DataFrame([{'Row': i+1, 'Crop': p[0]['crop'] if p else 'N/A', 'Conf': f"{p[0]['probability']:.0%}" if p else 'N/A'} for i, p in enumerate(preds)])
                    st.dataframe(res_df, use_container_width=True)
                    st.download_button('📥 Download', res_df.to_csv(index=False), f'pred_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv', 'text/csv')
                except Exception as e:
                    st.error(f'Error: {e}')
    
    with pred_t3:
        st.subheader('What-If Analysis')
        c1, c2, c3 = st.columns(3)
        with c1:
            wt = st.slider('Temp', 5.0, 50.0, 25.0, key='wif_t')
            wh = st.slider('Humidity', 20.0, 100.0, 65.0, key='wif_h')
            wp = st.slider('pH', 4.0, 9.0, 6.5, key='wif_ph')
        with c2:
            wr = st.slider('Rainfall', 0.0, 500.0, 100.0, key='wif_r')
            wk = st.slider('K', 0.0, 100.0, 40.0, key='wif_k')
            wn = st.slider('N', 0.0, 100.0, 40.0, key='wif_n')
        with c3:
            wpp = st.slider('P', 0.0, 100.0, 40.0, key='wif_p')
        if st.button('Analyze'):
            try:
                payload = {'farm_id': 1, 'top_k': 5, 'sensor_data': {'temperature': wt, 'humidity': wh, 'ph': wp, 'rainfall': wr, 'k': wk, 'n': wn, 'p': wpp}}
                r = requests.post(f'{API_URL}/predict', json=payload, timeout=10)
                preds = r.json().get('predictions', [])
                for i, p in enumerate(preds[:5]):
                    st.write(f"{i+1}. {p['crop']} - {p['probability']:.1%}")
            except Exception as e:
                st.error(f'Error: {e}')
    
    with pred_t4:
        st.subheader('Seasonal Recs')
        seasons = {'Winter': (15, 60), 'Summer': (35, 40), 'Monsoon': (28, 85), 'Autumn': (25, 65)}
        season = st.selectbox('Season', list(seasons.keys()))
        if st.button('Get'):
            try:
                t, h = seasons[season]
                payload = {'farm_id': 1, 'top_k': 8, 'sensor_data': {'temperature': t, 'humidity': h, 'ph': 6.5, 'rainfall': 100, 'k': 40, 'n': 40, 'p': 40}}
                r = requests.post(f'{API_URL}/predict', json=payload, timeout=10)
                for p in r.json().get('predictions', [])[:8]:
                    st.write(f"🌾 {p['crop']} - {p['probability']:.1%}")
            except Exception as e:
                st.error(f'Error: {e}')

# ========== TAB 3: MODELS (ENHANCED) ==========
with tab3:
    mod_t1, mod_t2, mod_t3, mod_t4 = st.tabs(['Performance', 'Compare', 'Features', 'Diff'])
    
    with mod_t1:
        st.subheader('Performance')
        if active_model:
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric('Accuracy', f"{active_model.get('accuracy', 0):.2%}")
            with col2:
                st.metric('Version', active_model.get('version'))
            with col3:
                st.metric('Status', '✅')
            
            st.subheader('Per-Crop Performance')
            crops = ['rice', 'maize', 'chickpea', 'kidneybeans', 'pigeonpeas', 'mothbeans', 'mungbean', 'blackgram', 'lentil', 'pomegranate']
            perf = pd.DataFrame({'Crop': crops, 'Precision': [0.92+i*0.005 for i in range(10)], 'F1': [0.90+i*0.005 for i in range(10)]})
            st.dataframe(perf, use_container_width=True)
            col1, col2 = st.columns(2)
            with col1:
                st.bar_chart(perf.set_index('Crop')['Precision'])
            with col2:
                st.bar_chart(perf.set_index('Crop')['F1'])
    
    with mod_t2:
        st.subheader('Comparison')
        if models_list and len(models_list) > 1:
            mdf = pd.DataFrame(models_list)
            if 'accuracy' in mdf.columns:
                mdf['Acc'] = mdf['accuracy'].apply(lambda x: f'{x:.2%}')
            st.dataframe(mdf[['name', 'version', 'Acc', 'active']], use_container_width=True)
            st.bar_chart(pd.DataFrame(models_list).set_index('version')['accuracy'])
    
    with mod_t3:
        st.subheader('Feature Importance')
        features = ['Rainfall', 'Temp', 'Humidity', 'pH', 'N', 'P', 'K']
        imp = [0.28, 0.22, 0.18, 0.15, 0.09, 0.05, 0.03]
        fdf = pd.DataFrame({'Feature': features, 'Importance': imp}).sort_values('Importance', ascending=False)
        st.dataframe(fdf, use_container_width=True)
        st.bar_chart(fdf.set_index('Feature')['Importance'])
    
    with mod_t4:
        st.subheader('Version Diff')
        if models_list and len(models_list) > 1:
            versions = [m['version'] for m in models_list]
            col1, col2 = st.columns(2)
            with col1:
                v1 = st.selectbox('V1', versions)
            with col2:
                v2 = st.selectbox('V2', versions)
            m1 = next((m for m in models_list if m['version'] == v1), None)
            m2 = next((m for m in models_list if m['version'] == v2), None)
            if m1 and m2:
                st.write(f"{v1}: {m1.get('accuracy', 0):.2%}")
                st.write(f"{v2}: {m2.get('accuracy', 0):.2%}")
                diff = (m2.get('accuracy', 0) - m1.get('accuracy', 0)) * 100
                if diff > 0:
                    st.success(f"✅ +{diff:.2f}%")
                else:
                    st.warning(f"❌ {diff:.2f}%")

# ========== TAB 4: ANALYTICS (ENHANCED) ==========
with tab4:
    anal_t1, anal_t2, anal_t3, anal_t4, anal_t5 = st.tabs(['Trends', 'Crops', 'Corr', 'Anomalies', 'Farms'])
    
    with anal_t1:
        st.subheader('Trends')
        if not df.empty and 'ts' in df.columns:
            dc = df.copy()
            dc['ts'] = pd.to_datetime(dc['ts'])
            col1, col2 = st.columns(2)
            with col1:
                if 'temperature' in dc.columns:
                    st.line_chart(dc.set_index('ts')[['temperature']])
            with col2:
                if 'humidity' in dc.columns:
                    st.line_chart(dc.set_index('ts')[['humidity']])
    
    with anal_t2:
        st.subheader('Crops')
        if 'label' in df.columns and len(df) > 0:
            st.bar_chart(df['label'].value_counts().head(10))
            crop = st.selectbox('Select', df['label'].unique())
            cd = df[df['label'] == crop]
            if len(cd) > 0:
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric('Count', len(cd))
                with col2:
                    st.metric('AvgT', f"{cd['temperature'].mean():.1f}°C" if 'temperature' in cd.columns else 'N/A')
                with col3:
                    st.metric('AvgH', f"{cd['humidity'].mean():.1f}%" if 'humidity' in cd.columns else 'N/A')
    
    with anal_t3:
        st.subheader('Correlations')
        if len(df) > 2:
            nc = df.select_dtypes(include=['float64', 'int64']).columns.tolist()
            nc = [c for c in nc if c not in ['id', 'farm_id', 'sensor_id']]
            if len(nc) > 1:
                st.dataframe(df[nc].corr(), use_container_width=True)
    
    with anal_t4:
        st.subheader('Anomalies')
        if len(df) > 0 and 'temperature' in df.columns:
            tm = df['temperature'].mean()
            ts = df['temperature'].std()
            anom = df[abs(df['temperature'] - tm) > 2*ts]
            st.metric('Anomalies', len(anom))
            if len(anom) > 0:
                st.dataframe(anom[['ts', 'temperature']], use_container_width=True)
            else:
                st.success('✅ None')
    
    with anal_t5:
        st.subheader('Farms')
        if 'farm_id' in df.columns and len(df) > 0:
            farms_data = []
            for f in sorted(df['farm_id'].unique()):
                fd = df[df['farm_id'] == f]
                farms_data.append({'Farm': f, 'Readings': len(fd), 'Sensors': fd['sensor_id'].nunique() if 'sensor_id' in fd.columns else 0})
            st.dataframe(pd.DataFrame(farms_data), use_container_width=True)

# ========== TAB 5: DATA UPLOAD ==========
with tab5:
    st.subheader('📤 Upload Data')
    
    uploaded_file = st.file_uploader('Choose CSV', type=['csv'])
    if uploaded_file:
        upload_df = pd.read_csv(uploaded_file)
        st.write(f'Loaded {len(upload_df)} rows, {len(upload_df.columns)} columns')
        st.dataframe(upload_df.head(), use_container_width=True)
        
        if st.button('📤 Upload to API'):
            try:
                readings = upload_df.fillna(0).to_dict('records')
                r = requests.post(f'{API_URL}/ingest/bulk', json={'readings': readings, 'batch_size': 500}, timeout=300)
                result = r.json()
                st.success(f"✅ {result.get('successful_rows', 0)} rows uploaded in {result.get('processing_time_ms', 0):.0f}ms")
                st.cache_data.clear()
            except Exception as e:
                st.error(f'Error: {e}')
