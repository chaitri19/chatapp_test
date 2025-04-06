import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import User
from .models import UserConnection
from channels.layers import get_channel_layer
import logging

logger = logging.getLogger(__name__)

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        # Store the channel name associated with this user
        self.user_group_name = f"user_{self.user.id}"
        
        # Join user-specific group
        await self.channel_layer.group_add(
            self.user_group_name,
            self.channel_name
        )
        
        await self.accept()
        logger.info(f"WebSocket connected for user: {self.user}, channel: {self.channel_name}")

    async def disconnect(self, close_code):
        # Leave user-specific group
        if hasattr(self, 'user_group_name'):
            await self.channel_layer.group_discard(
                self.user_group_name,
                self.channel_name
            )
        logger.info(f"WebSocket disconnected for user: {self.user}, code: {close_code}")

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            action = data.get("action", "")
            logger.info(f"Received action: {action} from user: {self.user}")

            if action == "init_connection":
                await self.handle_init_connection()
            elif action == "get_users":
                await self.get_users()
            elif action == "send_request":
                receiver = data.get("receiver")
                if receiver:
                    await self.send_connection_request(receiver)
            elif action == "approve_request":
                sender = data.get("sender")
                if sender:
                    await self.approve_connection_request(sender)
            elif action == "reject_request":
                sender = data.get("sender")
                if sender:
                    await self.reject_connection_request(sender)
            elif action == "ping":
                await self.send_json({"type": "pong"})
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            await self.send_json({"type": "error", "message": str(e)})

    async def handle_init_connection(self):
        logger.info(f"Initializing connection for user: {self.user}")
        await self.get_users()

    async def get_users(self):
        users = await self.get_all_users()
        sent_requests = await self.get_sent_requests()
        pending_requests = await self.get_pending_requests()
        mutual_connections = await self.get_mutual_connections()

        logger.info(f"Sending user lists to {self.user}. " +
                   f"Users: {len(users)}, " +
                   f"Sent: {len(sent_requests)}, " +
                   f"Pending: {len(pending_requests)}, " + 
                   f"Mutual: {len(mutual_connections)}")

        await self.send_json({
            "type": "update_users",
            "users": users,
            "sent_requests": sent_requests,
            "pending_requests": pending_requests,
            "mutual_connections": mutual_connections,
        })

    @database_sync_to_async
    def get_all_users(self):
        # Get all users except the current user
        return list(User.objects.exclude(username=self.user.username).values_list("username", flat=True))

    @database_sync_to_async
    def get_sent_requests(self):
        # Get all pending requests sent by the current user
        return list(UserConnection.objects.filter(
            sender=self.user, 
            status="pending"
        ).values_list("receiver__username", flat=True))

    @database_sync_to_async
    def get_pending_requests(self):
        # Get all pending requests received by the current user
        return list(UserConnection.objects.filter(
            receiver=self.user, 
            status="pending"
        ).values_list("sender__username", flat=True))

    @database_sync_to_async
    def get_mutual_connections(self):
        # Get all approved connections
        return list(UserConnection.objects.filter(
            status="approved"
        ).filter(
            sender=self.user
        ).values_list("receiver__username", flat=True)) + list(UserConnection.objects.filter(
            status="approved"
        ).filter(
            receiver=self.user
        ).values_list("sender__username", flat=True))

    async def send_connection_request(self, receiver_username):
        try:
            success, receiver_id = await self._create_connection_request(receiver_username)
            if success:
                # Update the sender's user lists
                await self.get_users()
                
                # Notify the receiver of the new request
                if receiver_id:
                    await self.channel_layer.group_send(
                        f"user_{receiver_id}",
                        {
                            "type": "connection_notification",
                            "message": f"New connection request from {self.user.username}"
                        }
                    )
            
        except Exception as e:
            logger.error(f"Error in send_connection_request: {e}")
            await self.send_json({"type": "error", "message": str(e)})

    @database_sync_to_async
    def _create_connection_request(self, receiver_username):
        try:
            receiver = User.objects.get(username=receiver_username)
            # Check if a connection request already exists
            existing = UserConnection.objects.filter(
                sender=self.user, 
                receiver=receiver
            ).exists()
            
            if existing:
                logger.warning(f"Request already exists from {self.user} to {receiver_username}")
                return False, None

            # Create a new connection request
            UserConnection.objects.create(
                sender=self.user,
                receiver=receiver,
                status="pending"
            )
            logger.info(f"Connection request created: {self.user} -> {receiver_username}")
            return True, receiver.id
            
        except User.DoesNotExist:
            logger.error(f"User not found: {receiver_username}")
            raise Exception(f"User {receiver_username} not found")
        except Exception as e:
            logger.error(f"Error creating connection request: {e}")
            raise

    async def approve_connection_request(self, sender_username):
        try:
            success, sender_id = await self._approve_connection(sender_username)
            if success:
                # Update the receiver's user lists
                await self.get_users()
                
                # Notify the original sender that their request was approved
                if sender_id:
                    await self.channel_layer.group_send(
                        f"user_{sender_id}",
                        {
                            "type": "connection_notification",
                            "message": f"{self.user.username} accepted your connection request"
                        }
                    )
        except Exception as e:
            logger.error(f"Error in approve_connection_request: {e}")
            await self.send_json({"type": "error", "message": str(e)})
    
    @database_sync_to_async
    def _approve_connection(self, sender_username):
        try:
            sender = User.objects.get(username=sender_username)
            connection = UserConnection.objects.get(
                sender=sender,
                receiver=self.user,
                status="pending"
            )
            connection.status = "approved"
            connection.save()
            logger.info(f"Connection request approved: {sender_username} -> {self.user}")
            return True, sender.id
        except User.DoesNotExist:
            logger.error(f"User not found: {sender_username}")
            raise Exception(f"User {sender_username} not found")
        except UserConnection.DoesNotExist:
            logger.error(f"Connection request not found from {sender_username} to {self.user}")
            raise Exception("Connection request not found")
        except Exception as e:
            logger.error(f"Error approving connection: {e}")
            raise

    async def reject_connection_request(self, sender_username):
        try:
            success, sender_id = await self._reject_connection(sender_username)
            if success:
                # Update the receiver's user lists
                await self.get_users()
                
                # Optionally notify the sender that their request was rejected
                if sender_id:
                    await self.channel_layer.group_send(
                        f"user_{sender_id}",
                        {
                            "type": "connection_notification",
                            "message": f"{self.user.username} rejected your connection request"
                        }
                    )
        except Exception as e:
            logger.error(f"Error in reject_connection_request: {e}")
            await self.send_json({"type": "error", "message": str(e)})
    
    @database_sync_to_async
    def _reject_connection(self, sender_username):
        try:
            sender = User.objects.get(username=sender_username)
            connection = UserConnection.objects.get(
                sender=sender,
                receiver=self.user,
                status="pending"
            )
            connection.delete()
            logger.info(f"Connection request rejected: {sender_username} -> {self.user}")
            return True, sender.id
        except User.DoesNotExist:
            logger.error(f"User not found: {sender_username}")
            raise Exception(f"User {sender_username} not found")
        except UserConnection.DoesNotExist:
            logger.error(f"Connection request not found from {sender_username} to {self.user}")
            raise Exception("Connection request not found")
        except Exception as e:
            logger.error(f"Error rejecting connection: {e}")
            raise

    # Handler for receiving connection notifications
    async def connection_notification(self, event):
        # Send the notification message to the WebSocket
        await self.send_json({
            "type": "notification",
            "message": event["message"],
            "action": "refresh_users"
        })

    async def send_json(self, content):
        await self.send(text_data=json.dumps(content))
