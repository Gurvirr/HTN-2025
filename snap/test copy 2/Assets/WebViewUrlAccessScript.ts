import { WebView } from "./Web View.lspkg/WebView"

@component
export class WebViewUrlAccessScript extends BaseScriptComponent {
    // Reference to the WebView component on the same SceneObject
    private webViewComponent: WebView | null = null
    
    onAwake() {
        // Get the WebView component attached to the same SceneObject
        this.webViewComponent = this.sceneObject.getComponent(WebView.getTypeName()) as WebView
        
        if (this.webViewComponent) {
            print("WebView component found on the same SceneObject!")
            this.accessWebViewUrl()
        } else {
            print("No WebView component found on this SceneObject")
        }
    }
    
    /**
     * Access and display the current URL from the WebView component
     */
    private accessWebViewUrl() {
        if (!this.webViewComponent) {
            print("WebView component not available")
            return
        }
        
        // Access the URL property directly from the WebView component
        // Note: The url property is public in the WebView class
        const currentUrl = this.webViewComponent.url
        print(`Current WebView URL: ${currentUrl}`)
        
        // You can also access other WebView properties:
        print(`WebView Resolution: ${this.webViewComponent.resolution.toString()}`)
        print(`User Agent: ${this.webViewComponent.userAgent || "Default"}`)
        print(`Poke Enabled: ${this.webViewComponent.poke}`)
    }
    
    /**
     * Change the WebView URL programmatically
     */
    public changeUrl(newUrl: string) {
        if (this.webViewComponent) {
            try {
                this.webViewComponent.goToUrl(newUrl)
                print(`Changed WebView URL to: ${newUrl}`)
            } catch (e) {
                print(`Error changing URL: ${e.toString()}`)
            }
        }
    }
    
    /**
     * Get the current URL (useful for other scripts)
     */
    public getCurrentUrl(): string {
        if (this.webViewComponent) {
            return this.webViewComponent.url
        }
        return ""
    }
    
    /**
     * Monitor URL changes (if you need to react to URL changes)
     */
    onStart() {
        if (this.webViewComponent) {
            // Set up a periodic check for URL changes
            const urlCheckEvent = this.createEvent("UpdateEvent")
            urlCheckEvent.bind(() => {
                this.checkForUrlChanges()
            })
        }
    }
    
    private lastKnownUrl: string = ""
    
    private checkForUrlChanges() {
        if (this.webViewComponent) {
            const currentUrl = this.webViewComponent.url
            if (currentUrl !== this.lastKnownUrl) {
                print(`URL changed from '${this.lastKnownUrl}' to '${currentUrl}'`)
                this.lastKnownUrl = currentUrl
                this.onUrlChanged(currentUrl)
            }
        }
    }
    
    /**
     * Override this method to handle URL changes
     */
    protected onUrlChanged(newUrl: string) {
        // Custom logic when URL changes
        print(`Handling URL change: ${newUrl}`)
    }
    
    /**
     * Access WebView control methods
     */
    public navigateBack() {
        if (this.webViewComponent) {
            try {
                this.webViewComponent.back()
                print("Navigated back in WebView")
            } catch (e) {
                print(`Error navigating back: ${e.toString()}`)
            }
        }
    }
    
    public navigateForward() {
        if (this.webViewComponent) {
            try {
                this.webViewComponent.forward()
                print("Navigated forward in WebView")
            } catch (e) {
                print(`Error navigating forward: ${e.toString()}`)
            }
        }
    }
    
    public reloadPage() {
        if (this.webViewComponent) {
            try {
                this.webViewComponent.reload()
                print("Reloaded WebView page")
            } catch (e) {
                print(`Error reloading: ${e.toString()}`)
            }
        }
    }
}
