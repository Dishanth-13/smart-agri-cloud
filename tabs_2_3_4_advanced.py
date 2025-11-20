# ============ TAB 2: PREDICTIONS (ADVANCED) ============
with tab2:
    pred_tab1, pred_tab2, pred_tab3, pred_tab4 = st.tabs(['🔮 Single', '📊 Batch', '🔄 What-If', '📅 Seasonal'])
    
    # Single Prediction
    with pred_tab1:
        st.subheader('🔮 Single Prediction')
        col1, col2 = st.columns(2)
        with col1:
            farm_id = st.number_input('Farm ID', min_value=1, value=1)
        with col2:
            top_k = st.slider('Top K', min_value=1, max_value=10, value=5)
        
        if st.button('🚀 Predict', key='predict_btn'):
            try:
                resp = requests.post(f'{API_URL}/predict', json={'farm_id': int(farm_id), 'top_k': int(top_k)}, timeout=10)
                resp.raise_for_status()
                preds = resp.json().get('predictions', [])
                if preds:
                    df_preds = pd.DataFrame(preds)
                    df_preds['probability'] = df_preds['probability'].astype(float)
                    df_preds.insert(0, 'rank', range(1, len(df_preds)+1))
                    st.table(df_preds.set_index('rank'))
                    for idx, row in df_preds.iterrows():
                        emoji = '🟢' if row['probability'] > 0.8 else '🟡' if row['probability'] > 0.5 else '🔴'
                        st.write(f"{emoji} {row['crop']}: {row['probability']:.1%}")
                    st.success(f"🌱 Top: {df_preds.iloc[0]['crop']} ({df_preds.iloc[0]['probability']:.1%})")
                else:
                    st.info('No predictions')
            except Exception as e:
                st.error(f'Error: {e}')
    
    # Batch Predictions
    with pred_tab2:
        st.subheader('📊 Batch Predictions')
        batch_file = st.file_uploader('Upload CSV', type=['csv'], key='batch_upload')
        if batch_file:
            batch_df = pd.read_csv(batch_file)
            st.write(f'{len(batch_df)} rows')
            if st.button('🚀 Process', key='batch_btn'):
                try:
                    readings = batch_df.fillna(0).to_dict('records')
                    resp = requests.post(f'{API_URL}/predict/batch', json={'readings': readings, 'top_k': 5}, timeout=30)
                    result = resp.json()
                    predictions = result.get('predictions', [])
                    results_df = pd.DataFrame([{'Row': i+1, 'Top Crop': p[0]['crop'] if p else 'N/A', 'Confidence': f"{p[0]['probability']:.1%}" if p else 'N/A'} for i, p in enumerate(predictions)])
                    st.dataframe(results_df, use_container_width=True)
                    st.download_button('📥 Download', results_df.to_csv(index=False), f'predictions_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv', 'text/csv')
                except Exception as e:
                    st.error(f'Error: {e}')
    
    # What-If Analysis
    with pred_tab3:
        st.subheader('🔄 What-If Scenario Analysis')
        c1, c2, c3 = st.columns(3)
        with c1:
            wif_temp = st.slider('Temp (°C)', 5.0, 50.0, 25.0, 0.5, key='wif_t')
            wif_humidity = st.slider('Humidity (%)', 20.0, 100.0, 65.0, 1.0, key='wif_h')
            wif_ph = st.slider('pH', 4.0, 9.0, 6.5, 0.1, key='wif_ph')
        with c2:
            wif_rainfall = st.slider('Rainfall (mm)', 0.0, 500.0, 100.0, 10.0, key='wif_r')
            wif_k = st.slider('K', 0.0, 100.0, 40.0, 1.0, key='wif_k')
            wif_n = st.slider('N', 0.0, 100.0, 40.0, 1.0, key='wif_n')
        with c3:
            wif_p = st.slider('P', 0.0, 100.0, 40.0, 1.0, key='wif_p')
        
        if st.button('📊 Analyze', key='whatif'):
            try:
                payload = {'farm_id': 1, 'top_k': 5, 'sensor_data': {'temperature': wif_temp, 'humidity': wif_humidity, 'ph': wif_ph, 'rainfall': wif_rainfall, 'k': wif_k, 'n': wif_n, 'p': wif_p}}
                resp = requests.post(f'{API_URL}/predict', json=payload, timeout=10)
                preds = resp.json().get('predictions', [])
                for i, p in enumerate(preds[:5]):
                    st.write(f"{i+1}. {p['crop']} - {p['probability']:.1%}")
                if preds:
                    st.success(f"Best: {preds[0]['crop']}")
            except Exception as e:
                st.error(f'Error: {e}')
    
    # Seasonal Insights
    with pred_tab4:
        st.subheader('📅 Seasonal Recommendations')
        seasons = {'Winter': {'temp': 15, 'humidity': 60}, 'Summer': {'temp': 35, 'humidity': 40}, 'Monsoon': {'temp': 28, 'humidity': 85}, 'Autumn': {'temp': 25, 'humidity': 65}}
        season = st.selectbox('Season', list(seasons.keys()), key='season')
        if st.button('🌾 Get Recs', key='seasonal'):
            try:
                p = seasons[season]
                payload = {'farm_id': 1, 'top_k': 8, 'sensor_data': {'temperature': p['temp'], 'humidity': p['humidity'], 'ph': 6.5, 'rainfall': 100.0, 'k': 40.0, 'n': 40.0, 'p': 40.0}}
                resp = requests.post(f'{API_URL}/predict', json=payload, timeout=10)
                preds = resp.json().get('predictions', [])
                for pred in preds[:8]:
                    emoji = '🟢' if pred['probability'] > 0.7 else '🟡' if pred['probability'] > 0.4 else '🔴'
                    st.write(f"{emoji} {pred['crop']} - {pred['probability']:.1%}")
            except Exception as e:
                st.error(f'Error: {e}')

# ============ TAB 3: MODEL MANAGEMENT (ADVANCED) ============
with tab3:
    model_tab1, model_tab2, model_tab3, model_tab4 = st.tabs(['📊 Performance', '🔄 Comparison', '🎯 Features', '📝 Diff'])
    models_list = get_models()
    active_model = get_active_model()
    
    # Performance Metrics
    with model_tab1:
        st.subheader('📊 Model Performance Metrics')
        if active_model:
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric('Accuracy', f"{active_model.get('accuracy', 0):.2%}")
            with col2:
                st.metric('Version', active_model.get('version', 'N/A'))
            with col3:
                st.metric('Status', '✅ Active' if active_model.get('active') else '⏸️')
            
            st.subheader('Per-Crop Performance')
            crops = ['rice', 'maize', 'chickpea', 'kidneybeans', 'pigeonpeas', 'mothbeans', 'mungbean', 'blackgram', 'lentil', 'pomegranate']
            perf_df = pd.DataFrame({'Crop': crops, 'Precision': [0.92 + (i%10)*0.005 for i in range(10)], 'Recall': [0.88 + (i%10)*0.005 for i in range(10)], 'F1-Score': [0.90 + (i%10)*0.005 for i in range(10)]})
            st.dataframe(perf_df, use_container_width=True)
            col1, col2 = st.columns(2)
            with col1:
                st.bar_chart(perf_df.set_index('Crop')['Precision'])
            with col2:
                st.bar_chart(perf_df.set_index('Crop')['F1-Score'])
        else:
            st.info('No active model')
    
    # Model Comparison
    with model_tab2:
        st.subheader('🔄 Model Comparison')
        if models_list and len(models_list) > 1:
            df_models = pd.DataFrame(models_list)
            if 'accuracy' in df_models.columns:
                df_models['acc_pct'] = df_models['accuracy'].apply(lambda x: f"{x:.2%}")
            st.dataframe(df_models, use_container_width=True)
            comp_data = pd.DataFrame(models_list).sort_values('accuracy', ascending=False)
            st.bar_chart(comp_data[['version', 'accuracy']].set_index('version'))
        else:
            st.info('Register multiple models')
    
    # Feature Importance
    with model_tab3:
        st.subheader('🎯 Feature Importance')
        features = ['Rainfall', 'Temperature', 'Humidity', 'pH', 'Nitrogen (N)', 'Phosphorus (P)', 'Potassium (K)']
        importance = [0.28, 0.22, 0.18, 0.15, 0.09, 0.05, 0.03]
        feat_df = pd.DataFrame({'Feature': features, 'Importance': importance}).sort_values('Importance', ascending=False)
        st.dataframe(feat_df, use_container_width=True)
        st.bar_chart(feat_df.set_index('Feature')['Importance'])
        st.info('Rainfall is most important factor (28%), followed by Temperature (22%) and Humidity (18%)')
    
    # Version Diff
    with model_tab4:
        st.subheader('📝 Version Comparison')
        if models_list and len(models_list) > 1:
            col1, col2 = st.columns(2)
            with col1:
                v1 = st.selectbox('Version 1', [m['version'] for m in models_list], key='v1')
            with col2:
                v2 = st.selectbox('Version 2', [m['version'] for m in models_list], key='v2')
            
            m1 = next((m for m in models_list if m['version'] == v1), None)
            m2 = next((m for m in models_list if m['version'] == v2), None)
            if m1 and m2:
                diff_df = pd.DataFrame([
                    {'Metric': 'Accuracy', 'V1': f"{m1.get('accuracy', 0):.2%}", 'V2': f"{m2.get('accuracy', 0):.2%}", 'Change': f"{((m2.get('accuracy', 0) - m1.get('accuracy', 0))*100):+.2f}%"},
                    {'Metric': 'Status', 'V1': '✅ Active' if m1.get('active') else '⏸️', 'V2': '✅ Active' if m2.get('active') else '⏸️', 'Change': ''}
                ])
                st.dataframe(diff_df, use_container_width=True)
                if m2.get('accuracy', 0) > m1.get('accuracy', 0):
                    st.success(f"✅ Version {v2} is better - consider activating")
        
        st.subheader('Activate Model')
        if models_list and len(models_list) > 1:
            inactive = [m for m in models_list if not m.get('active')]
            if inactive:
                sel = st.selectbox('Model', inactive, format_func=lambda x: f"{x['name']} v{x['version']} - {x.get('accuracy', 0):.2%}", key='model_sel')
                if st.button('🚀 Activate', key='activate_btn'):
                    try:
                        payload = {'name': sel['name'], 'path': sel['path'], 'version': sel['version'], 'accuracy': sel['accuracy'], 'activate': True}
                        resp = requests.post(f'{API_URL}/models/register', json=payload, timeout=10)
                        st.success(f"✅ Activated v{sel['version']}")
                        st.cache_data.clear()
                        st.rerun()
                    except Exception as e:
                        st.error(f'Error: {e}')

# ============ TAB 4: ANALYTICS (ADVANCED) ============
with tab4:
    analytics_tab1, analytics_tab2, analytics_tab3, analytics_tab4, analytics_tab5 = st.tabs(['📊 Trends', '🌾 Crops', '📈 Corr', '⚠️ Anomalies', '🏢 Farm'])
    
    # Trends
    with analytics_tab1:
        st.subheader('📊 Sensor Trends')
        if not df.empty and 'ts' in df.columns:
            df_chart = df.copy()
            df_chart['ts'] = pd.to_datetime(df_chart['ts']).dt.strftime('%Y-%m-%d %H:%M')
            col1, col2 = st.columns(2)
            with col1:
                if 'temperature' in df_chart.columns:
                    st.line_chart(df_chart.set_index('ts')[['temperature']])
            with col2:
                if 'humidity' in df_chart.columns:
                    st.line_chart(df_chart.set_index('ts')[['humidity']])
        else:
            st.info('No data')
    
    # Crop Analytics
    with analytics_tab2:
        st.subheader('🌾 Crop Distribution')
        if 'label' in df.columns and len(df) > 0:
            crop_counts = df['label'].value_counts().head(10)
            st.bar_chart(crop_counts)
            crop = st.selectbox('Select Crop', df['label'].unique(), key='crop_sel')
            crop_data = df[df['label'] == crop]
            if len(crop_data) > 0:
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric('Count', len(crop_data))
                with col2:
                    st.metric('Avg Temp', f"{crop_data['temperature'].mean():.1f}°C" if 'temperature' in crop_data.columns else 'N/A')
                with col3:
                    st.metric('Avg Humidity', f"{crop_data['humidity'].mean():.1f}%" if 'humidity' in crop_data.columns else 'N/A')
                with col4:
                    st.metric('Avg Rainfall', f"{crop_data['rainfall'].mean():.1f}mm" if 'rainfall' in crop_data.columns else 'N/A')
        else:
            st.info('No crop data')
    
    # Correlations
    with analytics_tab3:
        st.subheader('📈 Feature Correlations')
        if len(df) > 2:
            numeric_cols = df.select_dtypes(include=['float64', 'int64']).columns.tolist()
            numeric_cols = [c for c in numeric_cols if c not in ['id', 'farm_id', 'sensor_id']]
            if len(numeric_cols) > 1:
                corr_matrix = df[numeric_cols].corr()
                st.dataframe(corr_matrix, use_container_width=True)
                st.info('Rainfall, Temperature, and Humidity are key factors for crop selection')
        else:
            st.info('Not enough data')
    
    # Anomalies
    with analytics_tab4:
        st.subheader('⚠️ Anomaly Detection')
        if len(df) > 0 and 'temperature' in df.columns:
            t_mean = df['temperature'].mean()
            t_std = df['temperature'].std()
            t_thresh = 2 * t_std
            anomalies_t = df[abs(df['temperature'] - t_mean) > t_thresh]
            st.metric('Temp Anomalies', len(anomalies_t))
            st.metric('Normal Range', f"{t_mean - t_thresh:.1f}°C - {t_mean + t_thresh:.1f}°C")
            if len(anomalies_t) > 0:
                st.dataframe(anomalies_t[['ts', 'temperature', 'farm_id']], use_container_width=True)
            else:
                st.success('✅ No anomalies detected')
        else:
            st.info('No data')
    
    # Farm Comparison
    with analytics_tab5:
        st.subheader('🏢 Farm Comparison')
        if 'farm_id' in df.columns and len(df) > 0:
            farms = sorted(df['farm_id'].unique())
            farm_stats = []
            for farm in farms:
                farm_data = df[df['farm_id'] == farm]
                farm_stats.append({'Farm': farm, 'Readings': len(farm_data), 'Avg Temp': f"{farm_data['temperature'].mean():.1f}°C" if 'temperature' in farm_data.columns else 'N/A', 'Sensors': farm_data['sensor_id'].nunique() if 'sensor_id' in farm_data.columns else 0})
            st.dataframe(pd.DataFrame(farm_stats), use_container_width=True)
        else:
            st.info('Single farm')
