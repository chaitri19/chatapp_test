# Chat Application

A real-time chat application with connection management features built with Django, Django Channels, and React.

## Features

- User authentication with JWT tokens
- WebSocket-based real-time communication
- Connection request system (send, accept, reject requests)
- Real-time notifications
- User connection management

## Project Structure

```
Chatapp/
├── backend/             # Django project settings
├── chat/                # Django app with core functionality
│   ├── consumers.py     # WebSocket consumers
│   ├── middleware.py    # Token authentication for WebSockets
│   ├── models.py        # Data models
│   ├── routing.py       # WebSocket routing
│   ├── views.py         # API endpoints
│   └── admin.py         # Admin interface configuration
├── frontend/            # React frontend
│   ├── src/
│   │   ├── components/  # React components
│   │   └── utils/       # Utility functions
└── manage.py            # Django management script
```

## Prerequisites

- Python 3.8+
- Node.js 14+
- npm 6+

## Initial Setup

### Backend Setup

1. Create a virtual environment and activate it:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install Python dependencies:
```bash
pip install django djangorestframework djangorestframework-simplejwt django-cors-headers channels channels-redis
```

3. Apply database migrations:
```bash
python manage.py makemigrations
python manage.py migrate
```

4. Create a superuser for admin access:
```bash
python manage.py createsuperuser
```

5. Start the Django development server:
```bash
python manage.py runserver
```

### Frontend Setup

1. Navigate to the frontend directory:
```bash
cd frontend
```

2. Install Node dependencies:
```bash
npm install
```

3. Start the React development server:
```bash
npm start
```

## Authentication

The application uses JWT token authentication:

1. Register a user account
2. Login to receive a JWT token
3. This token is used for API requests and WebSocket connections

## WebSocket Connection

The WebSocket connection is established on successful login and handles:
- Connection requests between users
- Real-time updates of user lists
- Notifications for connection events

## User Connection Flow

1. Available users are shown in the user list
2. Send a connection request to a user
3. The recipient receives a notification about the request
4. The recipient can accept or reject the request
5. On acceptance, both users become mutual connections

## Admin Interface

Access the Django admin interface at http://127.0.0.1:8000/admin/ to:
- Manage users
- View and modify user connections
- Monitor the system

## Main Models

### UserConnection

Tracks connection relationships between users with the following fields:
- sender: The user who initiated the connection request
- receiver: The user who received the connection request
- status: Current status of the connection (pending, approved, rejected)
- created_at: When the request was created
- updated_at: When the request was last updated

## API Endpoints

- `/chat/api/login/` - User login
- `/chat/api/register/` - User registration
- `/chat/api/users/` - Get user lists
- `/ws/chat/` - WebSocket endpoint for real-time communication