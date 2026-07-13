import requests

url = "http://localhost:8200/api/easy_mode/generate"
data = {
    "api_key": "test",
    "config": {
        "genre": "test",
        "keywords": "test",
        "archetype_key": "test",
        "target_eps": 1,
        "initial_limit": 1,
        "word_count": 1000
    }
}

response = requests.post(url, json=data)
print(response.text)