# Exact Code Changes - Before & After

## File: `services/dashboard/streamlit_app.py`

### TOTAL CHANGES
- **Lines Added**: ~200 (from ~100 to ~250)
- **New Tabs**: 4 (from 1)
- **New Functions**: 2 (`get_models()`, `get_active_model()`)
- **Commits**: adbdafa, bbda8be

---

## SECTION 1: Imports & Setup

### BEFORE
```python
import os
import streamlit as st
import pandas as pd
import requests
from sqlalchemy import create_engine
```

### AFTER
```python
import os
import streamlit as st
import pandas as pd
import requests
from sqlalchemy import create_engine, text  # ← Added text import
from datetime import datetime            # ← Added datetime import
```

---

## SECTION 2: Page Configuration

### BEFORE
```python
st.title('Smart Agri Dashboard')

st.sidebar.header('Controls')
num = st.sidebar.number_input('Recent readings', min_value=1, max_value=500, value=20)

if st.sidebar.button('Refresh'):
    st.experimental_rerun()
```

### AFTER
```python
# ← NEW: Page config for wide layout
st.set_page_config(page_title='Smart Agri Dashboard', layout='wide')

# ← NEW: Emoji in title
st.title('🌾 Smart Agri Dashboard')

# ← NEW: 4-Tab Navigation
tab1, tab2, tab3, tab4 = st.tabs([
    '📊 Readings', 
    '🔮 Predictions', 
    '🤖 Model Management',     # ← NEW TAB
    '📈 Analytics'             # ← NEW TAB
])

# ← UPDATED: Sidebar with emoji
st.sidebar.header('⚙️ Controls')
num = st.sidebar.number_input('Recent readings', min_value=1, max_value=500, value=20)

# ← UPDATED: Use st.rerun() instead of deprecated st.experimental_rerun()
if st.sidebar.button('🔄 Refresh All'):  # ← Added emoji
    st.rerun()                           # ← Changed API
```

**Key Changes:**
- ✅ Added page config with `layout='wide'`
- ✅ Added 4-tab structure
- ✅ Updated to modern Streamlit API (`st.rerun()`)
- ✅ Added emojis throughout

---

## SECTION 3: Helper Functions (NEW)

### NEW FUNCTIONS ADDED

```python
# ← COMPLETELY NEW FUNCTION
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

# ← COMPLETELY NEW FUNCTION
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
```

**What's New:**
- Calls new `GET /models/list` endpoint
- Calls existing `GET /models/latest` endpoint
- Caches results for 10 seconds
- Error handling with user messages

---

## SECTION 4: Data Fetching (UPDATED)

### BEFORE
```python
@st.cache_data(ttl=10)
def get_recent(n):
    with engine.connect() as conn:
        df = pd.read_sql('SELECT * FROM readings ORDER BY ts DESC LIMIT %s', conn, params=(n,))
    return df

df = get_recent(num)
```

### AFTER
```python
@st.cache_data(ttl=10)
def get_recent(n):
    with engine.connect() as conn:
        df = pd.read_sql('SELECT * FROM readings ORDER BY ts DESC LIMIT %s', conn, params=(n,))
    return df

# ← NEW: Fetch models
models_list = get_models()
active_model = get_active_model()

# ← Same as before
df = get_recent(num)
```

**Added:**
- Model fetching via new helper functions

---

## SECTION 5: TAB 1 - Readings (NEW CONTENT)

### BEFORE
```python
st.subheader('Recent readings')
st.dataframe(df)
```

### AFTER
```python
# ← COMPLETELY NEW TAB STRUCTURE
with tab1:
    st.subheader('📊 Recent Sensor Readings')
    # ← NEW: use_container_width for better layout
    st.dataframe(df, use_container_width=True)
    
    # ← NEW: Metrics section
    st.metric('Total Readings', len(df))
    col1, col2, col3 = st.columns(3)
    
    # ← NEW: Smart conditional rendering
    with col1:
        if 'temperature' in df.columns:
            st.metric('Avg Temperature (°C)', f"{df['temperature'].mean():.1f}")
    with col2:
        if 'humidity' in df.columns:
            st.metric('Avg Humidity (%)', f"{df['humidity'].mean():.1f}")
    with col3:
        if 'rainfall' in df.columns:
            st.metric('Total Rainfall (mm)', f"{df['rainfall'].sum():.1f}")
```

**Improvements:**
- ✅ Wrapped in tab context
- ✅ Added emoji to subheader
- ✅ Added 4 metrics
- ✅ Conditional column rendering
- ✅ Better formatting with units

---

## SECTION 6: TAB 2 - Predictions (REFACTORED)

### BEFORE
```python
st.subheader('Predict from latest reading for farm')
farm_id = st.number_input('Farm ID', min_value=1, value=1)
top_k = st.slider('Top K predictions', min_value=1, max_value=10, value=5)

if st.button('Predict'):
    with st.spinner('Requesting predictions...'):
        # ... prediction logic ...
```

### AFTER
```python
# ← NEW: Tab wrapper
with tab2:
    st.subheader('🔮 Predict from Latest Reading')
    
    # ← NEW: Side-by-side layout
    col1, col2 = st.columns(2)
    with col1:
        farm_id = st.number_input('Farm ID', min_value=1, value=1)
    with col2:
        top_k = st.slider('Top K predictions', min_value=1, max_value=10, value=5)

    # ← UPDATED: Better button with emoji and unique key
    if st.button('🚀 Get Predictions', key='predict_btn'):
        with st.spinner('Requesting predictions...'):
            # ... prediction logic (same as before) ...
            
            # ← UPDATED: Better success message with emoji
            st.success(f"🌱 **Recommended crop:** {best['crop']} — Confidence: {best['probability']:.2%}")
```

**Changes:**
- ✅ Wrapped in tab context
- ✅ Side-by-side input layout
- ✅ Enhanced button with emoji and key
- ✅ Improved success message

---

## SECTION 7: TAB 3 - Model Management (COMPLETELY NEW - 70+ LINES)

### NEW TAB (DIDN'T EXIST BEFORE)

```python
# ← COMPLETELY NEW TAB
with tab3:
    st.subheader('🤖 Model Registry & Management')
    
    # Fetch models
    models_list = get_models()
    active_model = get_active_model()
    
    # ← NEW: Active Model Display
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
    
    # ← NEW: Model Version History
    st.subheader('📚 Model Version History')
    
    if models_list and len(models_list) > 0:
        df_models = pd.DataFrame(models_list)
        
        # Smart formatting
        if 'created_at' in df_models.columns:
            df_models['created_at'] = pd.to_datetime(df_models['created_at']).dt.strftime('%Y-%m-%d %H:%M:%S')
        if 'accuracy' in df_models.columns:
            df_models['accuracy'] = df_models['accuracy'].apply(lambda x: f"{x:.2%}" if pd.notna(x) else "N/A")
        if 'active' in df_models.columns:
            df_models['status'] = df_models['active'].apply(lambda x: '✅ Active' if x else '⏸️ Inactive')
        
        st.dataframe(df_models, use_container_width=True, hide_index=True)
        
        st.divider()
        
        # ← NEW: Model Activation Section
        st.subheader('🔄 Activate Model Version')
        
        if len(models_list) > 1:
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
                            st.cache_data.clear()
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
  -d '{...}'
        """, language='bash')
```

**New Features:**
- ✅ Shows active model with metrics
- ✅ Table of all model versions
- ✅ Model status indicators (✅/⏸️)
- ✅ One-click activation dropdown
- ✅ Auto-refresh after activation
- ✅ Helpful info messages
- ✅ API registration example

---

## SECTION 8: TAB 4 - Analytics (COMPLETELY NEW - 50+ LINES)

### NEW TAB (DIDN'T EXIST BEFORE)

```python
# ← COMPLETELY NEW TAB
with tab4:
    st.subheader('📈 System Analytics')
    
    # ← NEW: System Metrics
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
    
    # ← NEW: Sensor Trends
    st.subheader('📊 Sensor Data Trends')
    
    if not df.empty and 'ts' in df.columns:
        df_chart = df.copy()
        df_chart['ts'] = pd.to_datetime(df_chart['ts'])
        df_chart = df_chart.sort_values('ts')
        
        # Temperature Trend
        if 'temperature' in df_chart.columns:
            st.line_chart(df_chart.set_index('ts')[['temperature']], use_container_width=True)
            st.caption('Temperature Trend')
        
        # Humidity Trend
        if 'humidity' in df_chart.columns:
            st.line_chart(df_chart.set_index('ts')[['humidity']], use_container_width=True)
            st.caption('Humidity Trend')
        
        # Rainfall Trend
        if 'rainfall' in df_chart.columns:
            st.bar_chart(df_chart.set_index('ts')[['rainfall']], use_container_width=True)
            st.caption('Rainfall Trend')
    else:
        st.info('No data available to display trends.')
    
    st.divider()
    
    # ← NEW: System Info
    st.subheader('ℹ️ System Information')
    col1, col2, col3 = st.columns(3)
    with col1:
        st.write(f'**API URL:** {API_URL}')
    with col2:
        st.write(f'**Database:** smart_agri')
    with col3:
        st.write(f'**Dashboard Updated:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
```

**New Features:**
- ✅ 4 system metrics
- ✅ Temperature trend chart
- ✅ Humidity trend chart
- ✅ Rainfall trend chart
- ✅ System information footer
- ✅ Dynamic timestamp

---

## Summary of Changes

### Lines Changed
| Section | Before | After | Change |
|---------|--------|-------|--------|
| Imports | 5 | 7 | +2 lines |
| Setup | 8 | 12 | +4 lines |
| Tab 1 | 3 | 20 | +17 lines |
| Tab 2 | 60 | 65 | +5 lines (same logic, better layout) |
| Tab 3 | 0 | 70 | **+70 lines NEW** |
| Tab 4 | 0 | 50 | **+50 lines NEW** |
| **TOTAL** | **~100** | **~250** | **+150 lines** |

### Key Additions
- ✅ 4-tab navigation (was single page)
- ✅ 2 new helper functions
- ✅ 2 completely new tabs (Model Management, Analytics)
- ✅ 4 new metrics on Readings tab
- ✅ Model version history display
- ✅ One-click model activation/rollback
- ✅ 3 sensor trend charts
- ✅ System metrics and information
- ✅ Emojis throughout
- ✅ Better error handling

### API Calls Added
- ✅ `GET /models/list` (new endpoint in API)
- ✅ `GET /models/latest` (existing, now used here)
- ✅ `POST /models/register` (existing, now used for activation)

---

## Deployment Status

✅ Code updated in `services/dashboard/streamlit_app.py`  
✅ Docker image rebuilt  
✅ Container running with new features  
✅ All 4 tabs functional  
✅ API integration working  
✅ Changes committed (adbdafa, bbda8be)  
✅ Pushed to origin/main  

---

**Live URL**: http://localhost:8501  
**Git Commits**: adbdafa, bbda8be, 392c949, bbda8be  
**Status**: ✅ Complete & Deployed  
