# api/consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .appium_service import AppiumService

# class AppiumConsumer(AsyncWebsocketConsumer):
#     async def connect(self):
#         await self.accept()
#         await self.channel_layer.group_add("appium", self.channel_name)

#     async def disconnect(self, close_code):
#         await self.channel_layer.group_discard("appium", self.channel_name)

#     async def receive(self, text_data):
#         try:
#             data = json.loads(text_data)
#             # Handle incoming messages if needed
#         except json.JSONDecodeError:
#             pass

#     async def log_message(self, event):
#         await self.send(text_data=json.dumps({
#             'event': 'log',
#             'message': event['message']
#         }))


# api/consumers.py
class AppiumConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # The group name we will send messages to.
        self.room_group_name = "appium"
        
        # Join the room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        # Leave the room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    # This method is not used for backend-to-frontend logs, but is good to have.
    async def receive(self, text_data):
        pass # We are not expecting messages from the client.

    async def log_message(self, event):
        message_data = event['message']

        await self.send(text_data=json.dumps({
            'event': 'log', 
            'message': message_data
        }))