from fastapi import WebSocket
from typing import Dict, List
import json
import asyncio


class WebSocketManager:
    """
    WebSocket Connection Manager for real-time updates
    """
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.subscriptions: Dict[str, List[str]] = {}  # client_id -> [topics]
    
    async def connect(self, client_id: str, websocket: WebSocket):
        """
        Accept and store websocket connection
        """
        await websocket.accept()
        self.active_connections[client_id] = websocket
        self.subscriptions[client_id] = []
        print(f"[OK] WebSocket connected: {client_id}")
        
        # Send welcome message
        await self.send_to_client(client_id, {
            "type": "connection_established",
            "client_id": client_id,
            "message": "Connected to CodeForge AI"
        })
    
    def disconnect(self, client_id: str):
        """
        Remove websocket connection
        """
        if client_id in self.active_connections:
            del self.active_connections[client_id]
        if client_id in self.subscriptions:
            del self.subscriptions[client_id]
        print(f"[DISCONNECT] WebSocket disconnected: {client_id}")
    
    async def send_to_client(self, client_id: str, message: dict):
        """
        Send message to specific client
        """
        if client_id in self.active_connections:
            try:
                await self.active_connections[client_id].send_text(
                    json.dumps(message)
                )
            except Exception as e:
                print(f"Error sending to client {client_id}: {e}")
                self.disconnect(client_id)
    
    async def broadcast(self, message: dict):
        """
        Broadcast message to all connected clients
        """
        disconnected = []
        for client_id, websocket in self.active_connections.items():
            try:
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                print(f"Error broadcasting to {client_id}: {e}")
                disconnected.append(client_id)
        
        # Clean up disconnected clients
        for client_id in disconnected:
            self.disconnect(client_id)
    
    async def broadcast_to_client(self, client_id: str, message: dict):
        """
        Alias for send_to_client
        """
        await self.send_to_client(client_id, message)
    
    def subscribe(self, client_id: str, topic: str):
        """
        Subscribe client to a topic
        """
        if client_id in self.subscriptions:
            if topic not in self.subscriptions[client_id]:
                self.subscriptions[client_id].append(topic)
    
    def unsubscribe(self, client_id: str, topic: str):
        """
        Unsubscribe client from a topic
        """
        if client_id in self.subscriptions:
            if topic in self.subscriptions[client_id]:
                self.subscriptions[client_id].remove(topic)
    
    async def publish_to_topic(self, topic: str, message: dict):
        """
        Publish message to all clients subscribed to a topic
        """
        for client_id, topics in self.subscriptions.items():
            if topic in topics:
                await self.send_to_client(client_id, message)
    
    def get_connected_clients(self) -> List[str]:
        """
        Get list of connected client IDs
        """
        return list(self.active_connections.keys())
    
    def get_client_count(self) -> int:
        """
        Get number of connected clients
        """
        return len(self.active_connections)