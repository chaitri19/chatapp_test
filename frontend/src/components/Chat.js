import React, { useState, useEffect, useCallback } from "react";
import { connectWebSocket, sendMessage, disconnectWebSocket } from "../utils/websocket";

const ChatApp = () => {
  const [loggedInUser, setLoggedInUser] = useState(null);
  const [token, setToken] = useState(null);
  const [users, setUsers] = useState([]);
  const [sentRequests, setSentRequests] = useState([]);
  const [pendingRequests, setPendingRequests] = useState([]);
  const [mutualConnections, setMutualConnections] = useState([]);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [notifications, setNotifications] = useState([]);

  // Create a memoized refresh function
  const refreshUserLists = useCallback(() => {
    if (loggedInUser && token) {
      console.log("Refreshing user lists");
      sendMessage({
        action: "get_users"
      });
    }
  }, [loggedInUser, token]);

  useEffect(() => {
    if (token && loggedInUser) {
      console.log("Setting up WebSocket with token and username:", loggedInUser);
      try {
        connectWebSocket(token, loggedInUser, (message) => {
          console.log("Received message from WebSocket:", message);
          
          if (message.type === "update_users") {
            console.log("Updating user lists:", {
              users: message.users,
              sentRequests: message.sent_requests,
              pendingRequests: message.pending_requests,
              mutualConnections: message.mutual_connections
            });
            
            // Check if data exists and is properly formatted
            if (!message.users && !Array.isArray(message.users)) {
              console.error("Invalid users data received:", message.users);
              setError("Invalid user data received");
            } else {
              setUsers(message.users || []);
              setSentRequests(message.sent_requests || []);
              setPendingRequests(message.pending_requests || []);
              setMutualConnections(message.mutual_connections || []);
              setError(""); // Clear any previous errors
            }
          } else if (message.type === "notification") {
            // Handle incoming notification
            console.log("Received notification:", message);
            
            // Add to notifications list
            setNotifications(prev => [
              { id: Date.now(), message: message.message },
              ...prev.slice(0, 4) // Keep only the 5 most recent notifications
            ]);
            
            // If the notification includes an action to refresh users, do it
            if (message.action === "refresh_users") {
              refreshUserLists();
            }
          } else if (message.type === "error") {
            console.error("Error message from server:", message);
            setError(message.message || "Unknown error occurred");
          }
        });

        // Send initial connection message after a small delay to ensure socket is open
        setTimeout(() => {
          console.log("Sending init_connection message");
          sendMessage({ 
            action: "init_connection",
            username: loggedInUser
          });
          
          // Request user list explicitly
          sendMessage({
            action: "get_users"
          });
        }, 1000); // Increased timeout
        
        return () => {
          sendMessage({ action: "disconnect" });
          disconnectWebSocket();
        };
      } catch (error) {
        console.error("WebSocket connection error:", error);
        setError("WebSocket connection error: " + error.message);
      }
    }
  }, [token, loggedInUser, refreshUserLists]);

  // Log current state for debugging
  useEffect(() => {
    console.log("Current state:", {
      users,
      sentRequests,
      pendingRequests, 
      mutualConnections,
      loggedInUser
    });
  }, [users, sentRequests, pendingRequests, mutualConnections, loggedInUser]);

  const sendRequest = (receiver) => {
    sendMessage({ 
      action: "send_request", 
      receiver,
      sender: loggedInUser
    });
  };

  const acceptRequest = (sender) => {
    sendMessage({ 
      action: "approve_request", 
      sender,
      receiver: loggedInUser 
    });
  };

  const rejectRequest = (sender) => {
    sendMessage({ 
      action: "reject_request", 
      sender,
      receiver: loggedInUser
    });
  };

  const handleLogout = () => {
    sendMessage({ action: "disconnect" });
    disconnectWebSocket();
    setToken(null);
    setLoggedInUser(null);
    setUsers([]);
    setSentRequests([]);
    setPendingRequests([]);
    setMutualConnections([]);
    setError(""); // Clear error on logout
  };

  return (
    !token ? (
      <div>
        <h2>Login</h2>
        <form onSubmit={(e) => {
          e.preventDefault();
          fetch("http://127.0.0.1:8000/chat/api/login/", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username, password }),
          })
            .then((res) => res.json())
            .then((data) => { setToken(data.access); setLoggedInUser(username); })
            .catch((error) => console.error("Error logging in:", error));
        }}>
          <label>Username: <input type="text" value={username} onChange={(e) => setUsername(e.target.value)} /></label><br />
          <label>Password: <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} /></label><br />
          <button type="submit">Login</button>
        </form>
      </div>
    ) : (
      <div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h1>Welcome, {loggedInUser}!</h1>
          <button onClick={handleLogout}>Logout</button>
        </div>
        
        {error && <div style={{ color: 'red', padding: '10px', marginBottom: '10px', background: '#ffe6e6' }}>{error}</div>}
        
        {/* Notifications area */}
        {notifications.length > 0 && (
          <div style={{ marginBottom: '20px', padding: '10px', background: '#e6f7ff', borderRadius: '5px' }}>
            <h3>Recent Notifications</h3>
            <ul style={{ listStyle: 'none', padding: 0 }}>
              {notifications.map(notif => (
                <li key={notif.id} style={{ marginBottom: '5px', padding: '5px', borderBottom: '1px solid #ccc' }}>
                  {notif.message}
                </li>
              ))}
            </ul>
          </div>
        )}
        
        <div style={{ marginBottom: '20px' }}>
          <button onClick={refreshUserLists}>Refresh User Lists</button>
        </div>

        <h2>Available Users {users.length > 0 ? `(${users.length})` : '(No users)'}</h2>
        <ul>
          {users.length > 0 ? 
            users.map((user) => (
              !sentRequests.includes(user) && !mutualConnections.includes(user) && user !== loggedInUser && (
                <li key={user}>{user} <button onClick={() => sendRequest(user)}>Send Request</button></li>
              )
            )) : 
            <li>No available users found</li>
          }
        </ul>
        <h2>Requests Sent {sentRequests.length > 0 ? `(${sentRequests.length})` : '(None)'}</h2>
        <ul>{sentRequests.length > 0 ? sentRequests.map((user) => <li key={user}>{user}</li>) : <li>No requests sent</li>}</ul>
        <h2>Pending Requests {pendingRequests.length > 0 ? `(${pendingRequests.length})` : '(None)'}</h2>
        <ul>
          {pendingRequests.length > 0 ? 
            pendingRequests.map((user) => (
              <li key={user}>
                {user}
                <button onClick={() => acceptRequest(user)}>Accept</button>
                <button onClick={() => rejectRequest(user)}>Reject</button>
              </li>
            )) : 
            <li>No pending requests</li>
          }
        </ul>
        <h2>Mutual Connections {mutualConnections.length > 0 ? `(${mutualConnections.length})` : '(None)'}</h2>
        <ul>
          {mutualConnections.length > 0 ? 
            mutualConnections.map((user) => (
              <li key={user}>{user}</li>
            )) : 
            <li>No mutual connections</li>
          }
        </ul>
      </div>
    )
  );
};

export default ChatApp;
