#!/usr/bin/env python3
"""
Script to create rich, diverse characters for AI Society Portal
Using character data from rich_characters.json
"""

import json
import requests
import time

def create_character(character_data):
    """Create a character via API"""
    url = "http://localhost:8003/characters"
    headers = {"Content-Type": "application/json"}

    # Extract required fields
    payload = {
        "name": character_data["name"],
        "specialization": character_data["specialization"],
        "backstory": character_data["backstory"]
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code == 200:
            result = response.json()
            return True, result.get("id", "unknown"), result.get("message", "success")
        else:
            return False, None, f"Error: {response.status_code} - {response.text}"
    except Exception as e:
        return False, None, f"Exception: {str(e)}"

def main():
    """Main function to create all characters"""
    print("🎭 Creating Rich Characters for AI Society Portal")
    print("=" * 50)

    # Load character data
    try:
        with open("rich_characters.json", "r") as f:
            characters = json.load(f)
    except Exception as e:
        print(f"❌ Error loading characters: {e}")
        return

    created_characters = []

    for i, char in enumerate(characters, 1):
        print(f"\n{i}/{len(characters)} Creating {char['name']}...")

        success, char_id, message = create_character(char)

        if success:
            print(f"✅ Success: {char['name']} (ID: {char_id})")
            created_characters.append({
                "name": char["name"],
                "id": char_id,
                "specialization": char["specialization"],
                "personality": char["personality"][:100] + "...",
                "motivation": char["motivation"]
            })
        else:
            print(f"❌ Failed: {message}")

        # Small delay to avoid overwhelming the API
        time.sleep(0.5)

    # Summary
    print("\n" + "=" * 50)
    print(f"🎉 Successfully created {len(created_characters)}/{len(characters)} characters")

    if created_characters:
        print("\n📋 Created Characters:")
        for char in created_characters:
            print(f"  • {char['name']} - {char['specialization']}")

    # Save character IDs for reference
    with open("created_characters.json", "w") as f:
        json.dump(created_characters, f, indent=2)

    print(f"\n💾 Character IDs saved to created_characters.json")

if __name__ == "__main__":
    main()