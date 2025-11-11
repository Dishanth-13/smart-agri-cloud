"""
Simple simulator that posts fake sensor readings to the API /ingest endpoint.
"""
import os
import time
import random
import requests
import uuid
from datetime import datetime

API_URL = os.getenv('API_URL', 'http://localhost:8000/ingest')
INTERVAL = float(os.getenv('SIMULATOR_INTERVAL', '2'))
COUNT = int(os.getenv('SIMULATOR_COUNT', '0'))

def gen_reading(sensor_id):
    return {
        'sensor_id': sensor_id,
        'ts': datetime.utcnow().isoformat(),
        'temperature': round(random.uniform(10, 35), 2),
        'humidity': round(random.uniform(20, 90), 2),
        'ph': round(random.uniform(4.5, 8.5), 2),
        'rainfall': round(random.uniform(0, 200), 2),
        'n': random.randint(0,140),
        'p': random.randint(0,140),
        'k': random.randint(0,140),
        'farm_id': random.randint(1,5)
    }

def main():
    sensor_id = str(uuid.uuid4())[:8]
    i = 0
    while True:
        if COUNT and i>=COUNT:
            break
        payload = gen_reading(sensor_id)
        try:
            resp = requests.post(API_URL, json=payload, timeout=5)
            print('sent', payload, '->', resp.status_code, resp.text)
        except Exception as e:
            print('failed to send', e)
        time.sleep(INTERVAL)
        i += 1

if __name__ == '__main__':
    main()
