import requests
import json

url = "http://localhost:5000/api/platforms/youtube/auth"
headers = {"Authorization": "Bearer YOUR_TOKEN", "Content-Type": "application/json"}
print("Testing payload")
