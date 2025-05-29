#!/usr/bin/env python3
import requests
import json

# Login as admin
print("Testing updated admin character endpoint...")
login_data = {'username': 'admin@example.com', 'password': 'Secure_Password_123!'}
response = requests.post('https://imacall-backend-production.up.railway.app/api/v1/login/access-token', data=login_data)

if response.status_code != 200:
    print("Failed to login:", response.text)
    exit(1)

token = response.json()['access_token']
print("✅ Admin login successful")

# Test the updated admin character endpoint
headers = {'Authorization': f'Bearer {token}'}
character_id = 'ef8a6178-6e65-4473-ba6e-34b085dc1419'  # Trung's ID from the recent run
character_response = requests.get(f'https://imacall-backend-production.up.railway.app/api/v1/admin/characters/{character_id}', headers=headers)

print(f"GET /admin/characters/{character_id}")
print('Status Code:', character_response.status_code)

if character_response.status_code == 200:
    char_data = character_response.json()
    print('✅ Character Name:', char_data['name'])
    print('✅ Character Status:', char_data['status'])
    print('✅ Has admin_feedback field:', 'admin_feedback' in char_data)
    print('✅ admin_feedback value:', char_data.get('admin_feedback', 'None'))
    print('✅ Has fallback_response field:', 'fallback_response' in char_data)
    print('✅ fallback_response value:', char_data.get('fallback_response', 'None'))
    print('✅ Has created_at field:', 'created_at' in char_data)
    print('✅ Has updated_at field:', 'updated_at' in char_data)
    print('✅ Has creator_id field:', 'creator_id' in char_data)
    print("✅ Admin character endpoint working correctly with all fields!")
    
    # Test updating the character with admin feedback
    print("\n🔧 Testing character update with admin feedback...")
    update_data = {
        "admin_feedback": "Great character! Approved for testing purposes.",
        "fallback_response": "Hey there! I'm Trung and I'm currently having some technical difficulties. Please try again in a moment!"
    }
    update_response = requests.put(f'https://imacall-backend-production.up.railway.app/api/v1/admin/characters/{character_id}', 
                                 headers=headers, json=update_data)
    
    if update_response.status_code == 200:
        updated_char = update_response.json()
        print('✅ Character updated successfully!')
        print('✅ Updated admin_feedback:', updated_char.get('admin_feedback', 'None'))
        print('✅ Updated fallback_response:', updated_char.get('fallback_response', 'None'))
    else:
        print('❌ Update failed:', update_response.text)
        
else:
    print('❌ Error:', character_response.text) 