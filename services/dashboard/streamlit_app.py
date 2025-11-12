import os
import streamlit as st
import pandas as pd
import requests
from sqlalchemy import create_engine

DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql+psycopg2://postgres:postgres@db:5432/smart_agri')
API_URL = os.getenv('API_URL', 'http://api:8000')

engine = create_engine(DATABASE_URL)

st.title('Smart Agri Dashboard')

st.sidebar.header('Controls')
num = st.sidebar.number_input('Recent readings', min_value=1, max_value=500, value=20)

if st.sidebar.button('Refresh'):
    st.experimental_rerun()

@st.cache_data(ttl=10)
def get_recent(n):
    with engine.connect() as conn:
        df = pd.read_sql('SELECT * FROM readings ORDER BY ts DESC LIMIT %s', conn, params=(n,))
    return df

df = get_recent(num)
st.subheader('Recent readings')
st.dataframe(df)

st.subheader('Predict from latest reading for farm')
farm_id = st.number_input('Farm ID', min_value=1, value=1)
top_k = st.slider('Top K predictions', min_value=1, max_value=10, value=5)

if st.button('Predict'):
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
                st.subheader(f'Top {len(df_preds)} Predictions')
                # use rank as the DataFrame index so Streamlit doesn't display the default 0-based index
                st.table(df_preds.set_index('rank'))

                # Graphical representation heading and bar chart of probabilities (crop -> probability)
                st.subheader('Graphical Representation')
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
                st.markdown(f"**Recommended crop:** {best['crop']} — Confidence: {best['probability']:.2%}")

        except requests.exceptions.RequestException as re:
            st.error(f'Network/API error: {re}')
        except Exception as e:
            st.error(f'Prediction error: {e}')
