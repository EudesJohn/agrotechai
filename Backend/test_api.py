import requests

url = 'https://agrotech-kc6o.onrender.com/api/ai_search/'
try:
    response = requests.post(url, json={"query": "test"}, timeout=10)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text[:500]}")
    print(f"Headers: {response.headers}")
except Exception as e:
    print(f"Error: {e}")
