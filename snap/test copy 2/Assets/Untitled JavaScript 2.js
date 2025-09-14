//@input Asset.InternetModule internetModule
var internetModule = script.internetModule;

// Create WebSocket connection.
let socket; 
try {
    socket = script.internetModule.createWebSocket("ws://10.37.100.45:5069");
    socket.binaryType = "blob";
} catch (error) {''
    print("Error creating socket: " + error);
}

print("Script running");

// Listen for the open event
socket.onopen = (event) => {
    print("Socket opened");
    // Socket has opened, send a message back to the server
    socket.send("Message 1");

    // Try sending a binary message
    // (the bytes below spell 'Message 2')
    const message = [77, 101, 115, 115, 97, 103, 101, 32, 50];
    const bytes = new Uint8Array(message);
    socket.send(bytes);
};

// Listen for messages
socket.onmessage = async (event) => {
    print("Socket message received");
    if (event.data instanceof Blob) {
        // Binary frame, can be retrieved as either Uint8Array or string
        let bytes = await event.data.bytes();
        let text = await event.data.text();

        print("Received binary message, printing as text: " + text);
    } else {
        // Text frame
        let text = event.data;
        print("Received text message: " + text);
    }
};

socket.onclose = (event) => {
    if (event.wasClean) {
        print("Socket closed cleanly");
    } else {
        print("Socket closed with error, code: " + event.code);
    }
};

socket.onerror = (event) => {
    print("Socket error");
    print("Error: " + JSON.stringify(event));
};