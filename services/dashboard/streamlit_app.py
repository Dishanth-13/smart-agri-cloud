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
if st.button('Predict'):
    resp = requests.post(f'{API_URL}/predict', json={'farm_id': int(farm_id)})
    if resp.status_code==200:
        st.json(resp.json())
    else:
        st.error(f'Error: {resp.text}')
