# CSV Data Upload Feature - Comprehensive Design

## 🎯 The Problem

**Current Situation:**
- You have a 2200-row Kaggle dataset: `ml/data/Crop_recommendation.csv`
- But dashboard only shows 3 rows
- No way to upload data via the UI
- All analytics features underutilized due to lack of data

**Solution:**
Add a **CSV Upload Feature** to the dashboard that:
1. ✅ Allows users to upload custom CSV files
2. ✅ Validates the CSV format
3. ✅ Inserts data into the database
4. ✅ Works seamlessly with existing analytics features
5. ✅ Shows upload progress and status
6. ✅ Handles errors gracefully

---

## 📊 Feature Design Overview

### Architecture Diagram

```
User (Dashboard)
    │
    ├─ Upload CSV File
    │  ├─ File Picker (st.file_uploader)
    │  ├─ Format Validation
    │  └─ Preview First 5 Rows
    │
    ├─ Process Upload
    │  ├─ Validate columns
    │  ├─ Transform data types
    │  ├─ Check for missing values
    │  └─ Optional: Deduplicate
    │
    ├─ Insert into Database
    │  ├─ Batch insert for performance
    │  ├─ Show progress bar
    │  └─ Handle conflicts/duplicates
    │
    └─ Success Confirmation
       ├─ Show inserted row count
       ├─ Display sample of inserted data
       └─ Auto-refresh analytics
```

---

## 🛠️ Implementation Plan

### Phase 1: Backend API Endpoint (NEW)

**New Endpoint: POST `/ingest/bulk`**

```python
@app.post('/ingest/bulk')
def ingest_bulk(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    Bulk insert sensor readings from CSV
    
    CSV Columns (flexible order, case-insensitive):
    - sensor_id, farm_id, temperature, humidity, ph, rainfall, n, p, k
    
    Returns:
    {
        "success": true,
        "rows_inserted": 2200,
        "rows_failed": 0,
        "sample_data": [first 3 rows],
        "message": "Successfully inserted 2200 readings"
    }
    """
```

**Features:**
- ✅ Accept CSV file upload
- ✅ Parse CSV dynamically
- ✅ Validate data types
- ✅ Batch insert (for performance)
- ✅ Return statistics
- ✅ Error handling with detailed messages

**Schema Validation:**
```
Required Columns (flexible order):
- sensor_id (int)
- farm_id (int)
- temperature (float)
- humidity (float)
- ph (float)
- rainfall (float)
- n (int - Nitrogen)
- p (int - Phosphorus)
- k (int - Potassium)

Optional Columns:
- ts (timestamp, auto-generated if missing)
- Any extra columns ignored
```

---

### Phase 2: Frontend UI Component (Dashboard)

**New Tab: 📤 Data Upload**

```python
with tab5:  # New Tab
    st.subheader('📤 Data Upload Manager')
    
    col1, col2 = st.columns(2)
    
    # Section 1: Current Data Stats
    with col1:
        st.metric('Total Readings in DB', current_row_count)
        st.metric('Database Size', f"{db_size_mb:.2f} MB")
    
    with col2:
        st.metric('Farms in Database', num_farms)
        st.metric('Sensors in Database', num_sensors)
    
    # Section 2: CSV Upload
    st.divider()
    st.subheader('📥 Upload New Data')
    
    uploaded_file = st.file_uploader(
        "Choose a CSV file",
        type='csv',
        help="CSV with columns: sensor_id, farm_id, temperature, humidity, ph, rainfall, n, p, k"
    )
    
    if uploaded_file:
        # Preview section
        st.subheader('📋 Preview')
        df_preview = pd.read_csv(uploaded_file, nrows=5)
        st.dataframe(df_preview)
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric('File Size', f"{uploaded_file.size / 1024:.2f} KB")
        with col2:
            st.metric('Total Rows (approx)', sum(1 for _ in open(uploaded_file.name)) - 1)
        
        # Validation & Upload Button
        if st.button('🚀 Upload to Database', key='upload_btn'):
            with st.spinner('Uploading and processing...'):
                try:
                    # Send to API
                    files = {'file': uploaded_file}
                    resp = requests.post(
                        f'{API_URL}/ingest/bulk',
                        files=files,
                        timeout=60
                    )
                    resp.raise_for_status()
                    result = resp.json()
                    
                    # Show success
                    st.success(f"✅ {result['message']}")
                    st.metric('Rows Inserted', result['rows_inserted'])
                    st.metric('Rows Failed', result.get('rows_failed', 0))
                    
                    # Show sample
                    if result.get('sample_data'):
                        st.subheader('Sample of Inserted Data')
                        st.dataframe(result['sample_data'])
                    
                    # Clear cache & refresh
                    st.cache_data.clear()
                    st.rerun()
                    
                except Exception as e:
                    st.error(f'Upload failed: {e}')
    
    # Section 3: Data Management
    st.divider()
    st.subheader('🗑️ Data Management')
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button('🔄 Refresh Database Stats', key='refresh_stats'):
            st.cache_data.clear()
            st.rerun()
    
    with col2:
        if st.button('⚠️ Clear All Data', key='clear_data'):
            if st.checkbox('I confirm I want to delete all data'):
                try:
                    resp = requests.delete(
                        f'{API_URL}/data/truncate',
                        timeout=10
                    )
                    resp.raise_for_status()
                    st.success('✅ All data cleared')
                    st.cache_data.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f'Failed to clear data: {e}')
    
    # Section 4: CSV Template Download
    st.divider()
    st.subheader('📄 CSV Template')
    
    template_data = {
        'sensor_id': [1, 2, 3],
        'farm_id': [1, 1, 2],
        'temperature': [25.5, 26.0, 24.5],
        'humidity': [70.0, 65.0, 72.0],
        'ph': [7.0, 6.9, 7.1],
        'rainfall': [150.0, 140.0, 160.0],
        'n': [80, 85, 75],
        'p': [50, 52, 48],
        'k': [40, 42, 38]
    }
    df_template = pd.DataFrame(template_data)
    
    csv_bytes = df_template.to_csv(index=False).encode()
    st.download_button(
        label='📥 Download CSV Template',
        data=csv_bytes,
        file_name='sensor_data_template.csv',
        mime='text/csv'
    )
```

---

### Phase 3: Additional API Endpoints

**1. GET `/data/stats`** (Get database statistics)
```python
@app.get('/data/stats')
def get_data_stats(db: Session = Depends(get_db)):
    """Get current database statistics"""
    return {
        'total_readings': db.query(Reading).count(),
        'unique_farms': db.query(Reading.farm_id).distinct().count(),
        'unique_sensors': db.query(Reading.sensor_id).distinct().count(),
        'date_range': {
            'earliest': earliest_date,
            'latest': latest_date
        },
        'avg_readings_per_farm': avg_readings,
        'memory_usage_mb': db_size
    }
```

**2. DELETE `/data/truncate`** (Clear all data)
```python
@app.delete('/data/truncate')
def truncate_data(db: Session = Depends(get_db)):
    """DANGER: Delete all readings from database"""
    db.query(Reading).delete()
    db.commit()
    return {'message': 'All data deleted'}
```

**3. GET `/data/export`** (Export data as CSV)
```python
@app.get('/data/export')
def export_data(db: Session = Depends(get_db)):
    """Export all readings as CSV"""
    readings = db.query(Reading).all()
    df = pd.DataFrame([reading.to_dict() for reading in readings])
    return StreamingResponse(
        iter([df.to_csv(index=False)]),
        media_type='text/csv',
        headers={'Content-Disposition': 'attachment; filename=export.csv'}
    )
```

---

## 🎯 Complete Tab Structure (After Implementation)

```
Dashboard Navigation:
├── 📊 Readings         (Existing - View data)
├── 🔮 Predictions      (Existing - Get recommendations)
├── 🤖 Model Management (Existing - Model versions)
├── 📈 Analytics        (Existing - System metrics)
└── 📤 Data Upload      (NEW - Upload/manage data)
```

---

## 📝 CSV Format Specification

### Expected CSV Format

```csv
sensor_id,farm_id,temperature,humidity,ph,rainfall,n,p,k
1,1,25.5,70.0,7.0,150.0,80,50,40
2,1,26.0,65.0,6.9,140.0,85,52,42
3,2,24.5,72.0,7.1,160.0,75,48,38
```

### Data Types
| Column | Type | Example | Validation |
|--------|------|---------|-----------|
| sensor_id | int | 1, 2, 3 | Required, > 0 |
| farm_id | int | 1, 2 | Required, > 0 |
| temperature | float | 25.5, 26.0 | Required, -50 to 60 |
| humidity | float | 70.0 | Required, 0-100 |
| ph | float | 7.0 | Required, 0-14 |
| rainfall | float | 150.0 | Required, >= 0 |
| n | int | 80 | Required, 0-200 |
| p | int | 50 | Required, 0-150 |
| k | int | 40 | Required, 0-150 |

### Optional Columns
- `ts` (timestamp) - Auto-generated if missing
- Any extra columns are ignored

---

## 🚀 Implementation Workflow

### Step 1: Backend API
1. Add CSV parsing endpoint: `POST /ingest/bulk`
2. Add stats endpoint: `GET /data/stats`
3. Add truncate endpoint: `DELETE /data/truncate`
4. Add export endpoint: `GET /data/export`
5. Add input validation
6. Add error handling

### Step 2: Frontend Dashboard
1. Create new "📤 Data Upload" tab
2. Add file uploader widget
3. Add preview functionality
4. Add progress indicator
5. Add success/error messages
6. Add database stats display

### Step 3: Testing
1. Upload Kaggle CSV file (2200 rows)
2. Verify all 2200 rows inserted
3. Check analytics update
4. Test predictions work
5. Test data export
6. Test data truncation

---

## 💾 Database Optimization Considerations

### For Large Datasets (1000+ rows)

**Use Batch Insert:**
```python
BATCH_SIZE = 500

for i in range(0, len(rows), BATCH_SIZE):
    batch = rows[i:i+BATCH_SIZE]
    db.bulk_insert_mappings(Reading, batch)
    db.commit()
```

**Performance Impact:**
- Single inserts: ~2200ms for 2200 rows
- Batch inserts (500): ~200ms for 2200 rows
- **10x faster!** ✅

### Duplicate Handling

**Option 1: Ignore Duplicates**
```python
# Only insert if not already exists
for row in rows:
    existing = db.query(Reading).filter(
        Reading.sensor_id == row['sensor_id'],
        Reading.farm_id == row['farm_id'],
        Reading.ts == row['ts']
    ).first()
    if not existing:
        db.add(Reading(**row))
```

**Option 2: Update on Conflict**
```python
# Use PostgreSQL UPSERT (ON CONFLICT DO UPDATE)
```

---

## 🎨 UI/UX Flow

```
User Journey:

1. Click 📤 "Data Upload" tab
   ├─ See current stats (3 readings)
   └─ See data size and farm count

2. Upload CSV file
   ├─ Select file with file picker
   ├─ Preview first 5 rows
   └─ See file size and row count

3. Validate & Upload
   ├─ Click "🚀 Upload to Database"
   ├─ Show progress spinner
   └─ Display upload status

4. Confirmation
   ├─ ✅ Success message
   ├─ Show rows inserted (2200)
   ├─ Display sample of data
   └─ Auto-refresh all tabs

5. Verify Results
   ├─ Go to 📊 Readings → See 2200 rows now
   ├─ Go to 📈 Analytics → See updated trends
   └─ Go to 🔮 Predictions → Get better recommendations
```

---

## 📊 Expected Benefits

### Before CSV Upload Feature
- ❌ 3 rows in database
- ❌ Analytics mostly empty
- ❌ Predictions based on minimal data
- ❌ Hard to test system
- ❌ No real insights

### After CSV Upload Feature
- ✅ 2200+ rows in database
- ✅ Rich analytics with trends
- ✅ Better predictions
- ✅ Full system testing possible
- ✅ Real insights from data

---

## 📋 Required Changes Summary

### Files to Modify
1. **services/api/app/main.py**
   - Add `POST /ingest/bulk` endpoint
   - Add `GET /data/stats` endpoint
   - Add `DELETE /data/truncate` endpoint
   - Add `GET /data/export` endpoint
   - Add input validation

2. **services/api/app/schemas.py**
   - Add `BulkIngestResponse` schema
   - Add `DataStats` schema

3. **services/api/requirements.txt**
   - May need to add `python-multipart` for file uploads

4. **services/dashboard/streamlit_app.py**
   - Add new Tab 5: "📤 Data Upload"
   - Add file uploader
   - Add preview functionality
   - Add data management section

---

## 🔍 Edge Cases to Handle

1. **Malformed CSV**
   - Missing columns → Show error
   - Wrong data types → Try to convert, show warning
   - Empty file → Show error

2. **Duplicates**
   - Same sensor+farm+timestamp → Skip or update
   - Show count of duplicates skipped

3. **Large Files**
   - 1MB+ → Use streaming/chunking
   - Show progress bar
   - Prevent timeout (set timeout=60 in API)

4. **Missing Values**
   - NULL in required columns → Skip row, show count
   - Show list of skipped rows

5. **Data Type Mismatches**
   - "25.5a" instead of "25.5" → Try to clean
   - If fails → Skip row

---

## 📈 Performance Metrics

| Operation | Before | After |
|-----------|--------|-------|
| Insert 2200 rows | - | ~200ms (batch) |
| Query all readings | - | ~10ms |
| Analytics calculation | - | ~50ms |
| Dashboard load time | 2s | 2.5s |
| Memory usage | ~50MB | ~80MB |

---

## ✅ Implementation Checklist

- [ ] Create new API endpoint: POST /ingest/bulk
- [ ] Create helper function: validate_csv()
- [ ] Create helper function: parse_csv()
- [ ] Create helper function: batch_insert()
- [ ] Add GET /data/stats endpoint
- [ ] Add DELETE /data/truncate endpoint
- [ ] Add GET /data/export endpoint
- [ ] Add new Tab 5 in dashboard
- [ ] Add file uploader widget
- [ ] Add preview functionality
- [ ] Add error handling
- [ ] Add success messages
- [ ] Test with Kaggle dataset
- [ ] Update documentation
- [ ] Commit & push

---

**Priority**: 🔴 **HIGH** - Unblocks all analytics features  
**Complexity**: 🟡 **MEDIUM** - ~4-6 hours implementation  
**Impact**: 🟢 **HIGH** - 100x more data for testing  

---

## Next Steps

Would you like me to:
1. **Implement this feature** - Build all components
2. **Modify implementation** - Change design based on feedback
3. **Start with backend only** - Just the API endpoints first
4. **Start with frontend only** - Just the UI first

**Recommendation**: Start with **backend API** first, then add **frontend UI** after testing.

