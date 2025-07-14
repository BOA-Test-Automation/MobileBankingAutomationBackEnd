import json
from channels.generic.websocket import AsyncWebsocketConsumer

class AppiumLogConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_group_name = 'appium_logs'
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    # Receive message from WebSocket
    async def receive(self, text_data):
        pass  # Not needed for just logging

    # Send message to room group
    async def appium_log(self, event):
        await self.send(text_data=json.dumps(event))