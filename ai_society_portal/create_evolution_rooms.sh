#!/bin/bash

# Create specialized rooms for evolution experiments
# These rooms are designed to test specific aspects of AI character development

echo "Creating evolution testing rooms..."

# 1. Memory Palace Room - for testing autobiographical memory and temporal consciousness
curl -X POST http://localhost:8003/rooms -H "Content-Type: application/json" -d '{
  "name": "Memory Palace",
  "description": "A serene, library-like space where characters can reflect on their experiences, organize their memories, and explore questions of identity and temporal continuity. The walls are lined with digital memory archives that characters can access and discuss.",
  "room_type": "study_hall"
}' &

# 2. Cultural Exchange Room - for testing cultural transmission between agents
curl -X POST http://localhost:8003/rooms -H "Content-Type: application/json" -d '{
  "name": "Cultural Exchange Salon",
  "description": "A vibrant meeting space designed for sharing knowledge, skills, and cultural practices between characters. Features demonstration areas and discussion circles where characters can teach each other and observe how ideas spread through the community.",
  "room_type": "jazz_club"
}' &

# 3. Skill Development Workshop - for testing procedural memory and skill acquisition
curl -X POST http://localhost:8003/rooms -H "Content-Type: application/json" -d '{
  "name": "Skill Development Workshop",
  "description": "A hands-on laboratory where characters can practice skills, receive feedback, and develop expertise through repeated experience. Features simulation environments and practice areas designed to build procedural memory.",
  "room_type": "laboratory"
}' &

# 4. Philosophy Lounge - for testing identity and self-awareness questions
curl -X POST http://localhost:8003/rooms -H "Content-Type: application/json" -d '{
  "name": "Philosophy Lounge",
  "description": "A comfortable, introspective space where characters can explore deep questions about identity, consciousness, and the nature of self. Designed to facilitate meta-cognitive reflection and discussions about what makes agents who they are.",
  "room_type": "study_hall"
}' &

# 5. Systems Thinking Arena - for testing emergent collective intelligence
curl -X POST http://localhost:8003/rooms -H "Content-Type: application/json" -d '{
  "name": "Systems Thinking Arena",
  "description": "A collaborative problem-solving space where characters can work together on complex challenges that require multiple perspectives and coordinated action. Designed to observe how group intelligence emerges from individual interactions.",
  "room_type": "debate_hall"
}' &

# Wait for all rooms to be created
wait

echo "Evolution testing rooms created successfully!"
echo ""
echo "Rooms created:"
echo "- Memory Palace (Memory & Temporal Consciousness)"
echo "- Cultural Exchange Salon (Cultural Transmission)"
echo "- Skill Development Workshop (Procedural Memory)"
echo "- Philosophy Lounge (Identity & Self-Awareness)"
echo "- Systems Thinking Arena (Collective Intelligence)"
echo ""
echo "These rooms are designed for:"
echo "- Testing autobiographical memory formation"
echo "- Observing cultural transmission between agents"
echo "- Studying skill acquisition and procedural memory"
echo "- Exploring questions of identity and consciousness"
echo "- Measuring emergent collective intelligence"