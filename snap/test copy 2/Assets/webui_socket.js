//@input Asset.InternetModule internetModule

var internetModule = script.internetModule;

// print
// print("Scene Object: " + this.getSceneObject());
// print("WebView: " + this.getSceneObject().getComponent("Component.WebView"));
// print("WebView URL: " + this.getSceneObject().getComponent("Component.WebView").WebView);
// print("WebView URL: " + this.getSceneObject().getComponent("Component.WebView").WebView.url);
// Create the options

var resolution = new vec2(512, 512);
var options = InternetModule.createWebViewOptions(resolution);
var texture_web; 

//@input Component.Image image
//@input Asset.Texture texture

var webview = script.internetModule.createWebView(
	options,
	(texture) => {
		script.image.mainPass.baseTex = texture;
		webViewControl = texture.control;
		webViewControl.onReady.add(() => {
			print("onReady");
			webViewControl.loadUrl("https://snap.com");
		});
        texture_web = texture.control; 
	},
	(msg) => {
		print("Error:" + msg);
	}
);



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
    print("WebUI Socket opened");
};

// Listen for messages
socket.onmessage = async (event) => {
    print("WebUI Socket message received");
    if (event.data instanceof Blob) {
        // Binary frame, can be retrieved as either Uint8Array or string
        let text = await event.data.text();

        print("Received binary message, printing as text: " + text);
    } else {
        // Text frame
        let text = event.data;
        let data = JSON.parse(text);
        print("Received text frame message: " + text);
        if(data.action === "play_song") {
            print("Playing song: " + data.data.song_title);
        }else if(data.action === "play_video") {
            print("Playing video: " + data.data.video_url);
        }else{
            print("WebUI socket has no need to handle this action: " + data.action);
        }
    }
};

socket.onclose = (event) => {
    if (event.wasClean) {
        print("WebUI Socket closed cleanly");
    } else {
        print("WebUI Socket closed with error, code: " + event.code);
    }
};

socket.onerror = (event) => {
    print("WebUI Socket error");
    print("Error: " + JSON.stringify(event));
};