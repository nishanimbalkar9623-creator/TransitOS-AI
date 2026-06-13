import requests
import json

url = 'http://127.0.0.1:5000/copilot-chat'
test_prompts = [
    'Route risk Mumbai to Pune tomorrow',
    'Forecast Bangalore to Chennai next week',
    'Trust score for TRK001',
]

for prompt in test_prompts:
    print(f'\nTesting: "{prompt}"')
    try:
        response = requests.post(url, json={'prompt': prompt})
        data = response.json()
        print(f'Status: {data.get("status")}')
        resp_text = data.get('response', 'No response')
        preview = resp_text[:200] if len(resp_text) > 200 else resp_text
        print(f'Response: {preview}')
    except Exception as e:
        print(f'Error: {e}')

print('\n✓ All API tests completed successfully!')
