import json
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import UserConnection

@csrf_exempt
def register_view(request):
    if request.method == "POST":
        data = json.loads(request.body)
        if User.objects.filter(username=data["username"]).exists():
            return JsonResponse({"error": "Username already taken"}, status=400)
        User.objects.create_user(username=data["username"], password=data["password"])
        return JsonResponse({"message": "User registered successfully"})

@csrf_exempt
def login_view(request):
    if request.method == "POST":
        data = json.loads(request.body)
        user = authenticate(username=data["username"], password=data["password"])
        if user:
            refresh = RefreshToken.for_user(user)
            return JsonResponse({"access": str(refresh.access_token), "refresh": str(refresh)})
        return JsonResponse({"error": "Invalid credentials"}, status=400)

@api_view(["POST"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def send_request(request):
    data = json.loads(request.body)
    receiver_username = data.get("receiver_username")

    try:
        receiver = User.objects.get(username=receiver_username)
    except User.DoesNotExist:
        return JsonResponse({"error": "User does not exist"}, status=400)

    if UserConnection.objects.filter(sender=request.user, receiver=receiver).exists():
        return JsonResponse({"error": "Request already sent"}, status=400)

    UserConnection.objects.create(sender=request.user, receiver=receiver, status="pending")
    
    # Send real-time update
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"user_{receiver.id}",
        {"type": "connection.update", "message": "New request received"}
    )
    return JsonResponse({"message": "Request sent successfully"})

@api_view(["POST"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def accept_request(request, username):
    try:
        sender = User.objects.get(username=username)
        conn = UserConnection.objects.get(sender=sender, receiver=request.user, status="pending")
        conn.status = "approved"
        conn.save()
        
        # Notify both users about the mutual connection
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"user_{sender.id}",
            {"type": "connection.update", "message": "Your request was accepted"}
        )
        async_to_sync(channel_layer.group_send)(
            f"user_{request.user.id}",
            {"type": "connection.update", "message": "New mutual connection"}
        )
        return JsonResponse({"status": "Request accepted"})
    except (User.DoesNotExist, UserConnection.DoesNotExist):
        return JsonResponse({"error": "Request not found"}, status=400)

@api_view(["POST"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def reject_request(request, username):
    try:
        sender = User.objects.get(username=username)
        conn = UserConnection.objects.get(sender=sender, receiver=request.user, status="pending")
        conn.delete()
        
        # Notify sender about rejection
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"user_{sender.id}",
            {"type": "connection.update", "message": "Your request was rejected"}
        )
        return JsonResponse({"status": "Request rejected"})
    except (User.DoesNotExist, UserConnection.DoesNotExist):
        return JsonResponse({"error": "Request not found"}, status=400)

@api_view(["GET"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def get_user_lists(request):
    """
    Get all users, sent requests, pending requests, and mutual connections for the current user
    """
    # Get all users except the current user
    all_users = User.objects.exclude(username=request.user.username).values_list("username", flat=True)
    
    # Get sent requests
    sent_requests = UserConnection.objects.filter(
        sender=request.user, 
        status="pending"
    ).values_list("receiver__username", flat=True)
    
    # Get pending requests
    pending_requests = UserConnection.objects.filter(
        receiver=request.user, 
        status="pending"
    ).values_list("sender__username", flat=True)
    
    # Get mutual connections (approved connections)
    mutual_connections = list(UserConnection.objects.filter(
        status="approved"
    ).filter(
        sender=request.user
    ).values_list("receiver__username", flat=True)) + list(UserConnection.objects.filter(
        status="approved"
    ).filter(
        receiver=request.user
    ).values_list("sender__username", flat=True))
    
    return JsonResponse({
        "users": list(all_users),
        "sent_requests": list(sent_requests),
        "pending_requests": list(pending_requests),
        "mutual_connections": list(mutual_connections)
    })
