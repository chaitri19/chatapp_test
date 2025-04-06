let socket = null;
let messageHandler = null;
let reconnectAttempts = 0;
const maxReconnectAttempts = 5;

export const connectWebSocket = (token, username, onMessageReceived) => {
  if (socket && socket.readyState === WebSocket.OPEN) {
    console.log("WebSocket connection already exists. Closing existing connection.");
    disconnectWebSocket();
  }

  try {
    console.log("Attempting to connect WebSocket with token");
    // Include the token as a query parameter
    const wsUrl = `ws://127.0.0.1:8000/ws/chat/?token=${token}`;
    socket = new WebSocket(wsUrl);
    messageHandler = onMessageReceived;

    socket.onopen = () => {
      console.log("WebSocket connection established successfully");
      reconnectAttempts = 0;
      
      // Send an initial message to verify connection
      sendMessage({
        action: "init_connection",
        username: username
      });
    };

    socket.onmessage = (event) => {
      console.log("Raw WebSocket message received:", event.data);
      try {
        const data = JSON.parse(event.data);
        console.log("Parsed WebSocket message:", data);
        if (messageHandler) {
          messageHandler(data);
        } else {
          console.error("No message handler set");
        }
      } catch (error) {
        console.error("Error parsing WebSocket message:", error, event.data);
      }
    };

    socket.onclose = (event) => {
      console.log("WebSocket connection closed:", event);
      
      // Attempt to reconnect if not closed intentionally
      if (reconnectAttempts < maxReconnectAttempts) {
        console.log(`Attempting to reconnect (${reconnectAttempts + 1}/${maxReconnectAttempts})...`);
        reconnectAttempts++;
        
        setTimeout(() => {
          if (messageHandler) {
            connectWebSocket(token, username, messageHandler);
          }
        }, 3000); // Wait 3 seconds before reconnecting
      }
    };

    socket.onerror = (error) => {
      console.error("WebSocket error:", error);
      // The onclose handler will be called after this
    };
  } catch (error) {
    console.error("Error setting up WebSocket:", error);
    throw error;
  }
};

export const sendMessage = (message) => {
  if (!socket || socket.readyState !== WebSocket.OPEN) {
    console.error("WebSocket is not connected. Cannot send message:", message);
    return false;
  }

  try {
    console.log("Sending message:", message);
    socket.send(JSON.stringify(message));
    return true;
  } catch (error) {
    console.error("Error sending message:", error);
    return false;
  }
};

export const disconnectWebSocket = () => {
  if (socket) {
    console.log("Closing WebSocket connection");
    // Set this to prevent automatic reconnection attempts
    reconnectAttempts = maxReconnectAttempts;
    
    try {
      socket.close();
    } catch (error) {
      console.error("Error closing WebSocket:", error);
    } finally {
      socket = null;
      messageHandler = null;
    }
  }
};
