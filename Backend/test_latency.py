import requests
import time

url = 'https://agrotech-kc6o.onrender.com/api/ai_search/'
# Simuler une recherche rapide pour voir le temps de réponse
for i in range(3):
    start_time = time.time()
    try:
        # Pas de token donc ça va retourner 401/403 mais on mesure la latence réseau
        response = requests.post(url, json={"query": "test"}, timeout=15)
        print(f"Req {i+1}: {response.status_code} in {time.time() - start_time:.2f}s")
    except Exception as e:
        print(f"Req {i+1} Error: {e} in {time.time() - start_time:.2f}s")
