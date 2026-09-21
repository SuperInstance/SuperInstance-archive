#!/usr/bin/env python3
"""
Script to create immersive, rich environments for AI Society Portal
Using room data from immersive_rooms.json
"""

import json
import requests
import time

def create_room(room_data):
    """Create a room via API"""
    url = "http://localhost:8003/rooms"
    headers = {"Content-Type": "application/json"}

    payload = {
        "name": room_data["name"],
        "description": room_data["description"],
        "room_type": room_data["room_type"]
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
    """Main function to create all rooms"""
    print("🏛️ Creating Immersive Rooms for AI Society Portal")
    print("=" * 50)

    # Load room data
    try:
        with open("immersive_rooms.json", "r") as f:
            rooms = json.load(f)
    except Exception as e:
        print(f"❌ Error loading rooms: {e}")
        return

    created_rooms = []

    for i, room in enumerate(rooms, 1):
        print(f"\n{i}/{len(rooms)} Creating {room['name']}...")

        success, room_id, message = create_room(room)

        if success:
            print(f"✅ Success: {room['name']} (ID: {room_id})")
            created_rooms.append({
                "name": room["name"],
                "id": room_id,
                "room_type": room["room_type"],
                "atmosphere": room["atmosphere"],
                "ideal_conversations": room["ideal_conversations"][:2]
            })
        else:
            print(f"❌ Failed: {message}")

        # Small delay to avoid overwhelming the API
        time.sleep(0.5)

    # Summary
    print("\n" + "=" * 50)
    print(f"🎉 Successfully created {len(created_rooms)}/{len(rooms)} rooms")

    if created_rooms:
        print("\n🏛️ Created Rooms:")
        for room in created_rooms:
            print(f"  • {room['name']} ({room['room_type']})")

    # Save room IDs for reference
    with open("created_rooms.json", "w") as f:
        json.dump(created_rooms, f, indent=2)

    print(f"\n💾 Room IDs saved to created_rooms.json")

if __name__ == "__main__":
    main()