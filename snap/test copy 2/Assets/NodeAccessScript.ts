import { WebView } from "./Web View.lspkg/WebView"

@component
export class NodeAccessScript extends BaseScriptComponent {
    // Reference to WebView component in parent or other nodes
    private webViewComponent: WebView | null = null
    private webViewSceneObject: SceneObject | null = null
    
    onAwake() {
        this.findAndAccessWebViewNode()
        this.demonstrateNodeAccess()
    }
    
    /**
     * Find and access WebView node in the scene hierarchy
     * This demonstrates multiple ways to access other nodes
     */
    private findAndAccessWebViewNode() {
        // Method 1: Access parent node and find WebView component
        const parentObject = this.sceneObject.getParent()
        if (parentObject) {
            print("Found parent object: " + parentObject.name)
            
            // Try to get WebView component from parent
            this.webViewComponent = parentObject.getComponent(WebView.getTypeName()) as WebView
            if (this.webViewComponent) {
                print("Found WebView component in parent!")
                this.webViewSceneObject = parentObject
            }
        }
        
        // Method 2: Search through all children of parent for WebView
        if (!this.webViewComponent && parentObject) {
            this.searchChildrenForWebView(parentObject)
        }
        
        // Method 3: Search from scene root if not found in parent hierarchy
        if (!this.webViewComponent) {
            this.searchFromSceneRoot()
        }
        
        // Method 4: Find by name (if you know the WebView object name)
        if (!this.webViewComponent) {
            this.findWebViewByName("WebViewObject") // Replace with actual name
        }
    }
    
    /**
     * Search through children recursively for WebView component
     */
    private searchChildrenForWebView(parent: SceneObject) {
        const childCount = parent.getChildrenCount()
        
        for (let i = 0; i < childCount; i++) {
            const child = parent.getChild(i)
            
            // Check if this child has WebView component
            const webViewComp = child.getComponent(WebView.getTypeName()) as WebView
            if (webViewComp) {
                print("Found WebView in child: " + child.name)
                this.webViewComponent = webViewComp
                this.webViewSceneObject = child
                return
            }
            
            // Recursively search this child's children
            this.searchChildrenForWebView(child)
        }
    }
    
    /**
     * Search from scene root for WebView components
     */
    private searchFromSceneRoot() {
        const scene = this.sceneObject.getScene()
        const rootObjectsCount = scene.getRootObjectsCount()
        
        for (let i = 0; i < rootObjectsCount; i++) {
            const rootObject = scene.getRootObject(i)
            this.searchChildrenForWebView(rootObject)
            
            if (this.webViewComponent) {
                print("Found WebView from scene root search")
                break
            }
        }
    }
    
    /**
     * Find WebView by object name
     */
    private findWebViewByName(objectName: string) {
        const scene = this.sceneObject.getScene()
        const rootObjectsCount = scene.getRootObjectsCount()
        
        for (let i = 0; i < rootObjectsCount; i++) {
            const foundObject = this.findObjectByNameRecursive(scene.getRootObject(i), objectName)
            if (foundObject) {
                const webViewComp = foundObject.getComponent(WebView.getTypeName()) as WebView
                if (webViewComp) {
                    this.webViewComponent = webViewComp
                    this.webViewSceneObject = foundObject
                    print("Found WebView by name: " + objectName)
                    break
                }
            }
        }
    }
    
    /**
     * Recursively find object by name
     */
    private findObjectByNameRecursive(obj: SceneObject, targetName: string): SceneObject | null {
        if (obj.name === targetName) {
            return obj
        }
        
        const childCount = obj.getChildrenCount()
        for (let i = 0; i < childCount; i++) {
            const result = this.findObjectByNameRecursive(obj.getChild(i), targetName)
            if (result) {
                return result
            }
        }
        
        return null
    }
    
    /**
     * Demonstrate various node access methods and property modifications
     */
    private demonstrateNodeAccess() {
        if (!this.webViewComponent || !this.webViewSceneObject) {
            print("WebView component not found - cannot demonstrate property changes")
            return
        }
        
        print("=== Demonstrating WebView Property Access ===")
        
        // Access and modify WebView properties
        this.modifyWebViewProperties()
        
        // Access transform properties
        this.modifyTransformProperties()
        
        // Access other components on the WebView object
        this.accessOtherComponents()
        
        // Demonstrate parent-child relationships
        this.demonstrateHierarchyNavigation()
    }
    
    /**
     * Modify WebView specific properties
     */
    private modifyWebViewProperties() {
        if (!this.webViewComponent) return
        
        print("--- WebView Properties ---")
        
        // Navigate to different URLs
        try {
            this.webViewComponent.goToUrl("https://example.com")
            print("Changed WebView URL to example.com")
        } catch (e) {
            print("Error changing URL: " + e.toString())
        }
        
        // Set custom user agent
        try {
            this.webViewComponent.setUserAgent("SnapSpectacles/1.0 CustomAgent")
            print("Set custom user agent")
        } catch (e) {
            print("Error setting user agent: " + e.toString())
        }
        
        // Control WebView navigation
        const delayedEvent = this.createEvent("DelayedCallbackEvent")
        delayedEvent.bind(() => {
            try {
                this.webViewComponent!.reload()
                print("Reloaded WebView")
            } catch (e) {
                print("Error reloading: " + e.toString())
            }
        })
        delayedEvent.reset(2.0) // Reload after 2 seconds
    }
    
    /**
     * Modify transform properties of the WebView object
     */
    private modifyTransformProperties() {
        if (!this.webViewSceneObject) return
        
        print("--- Transform Properties ---")
        
        const transform = this.webViewSceneObject.getTransform()
        
        // Get current properties
        const currentPos = transform.getLocalPosition()
        const currentRot = transform.getLocalRotation()
        const currentScale = transform.getLocalScale()
        
        print(`Current Position: ${currentPos.toString()}`)
        print(`Current Rotation: ${currentRot.toString()}`)
        print(`Current Scale: ${currentScale.toString()}`)
        
        // Modify properties
        transform.setLocalPosition(vec3.add(currentPos, new vec3(0.1, 0, 0)))
        transform.setLocalScale(vec3.uniformScale(1.2))
        
        print("Modified WebView position and scale")
    }
    
    /**
     * Access other components on the WebView scene object
     */
    private accessOtherComponents() {
        if (!this.webViewSceneObject) return
        
        print("--- Other Components ---")
        
        // Access Image component (used by WebView)
        const imageComponent = this.webViewSceneObject.getComponent("Component.Image") as Image
        if (imageComponent) {
            print("Found Image component")
            // Modify render order
            imageComponent.setRenderOrder(10)
            print("Changed Image render order to 10")
        }
        
        // Access Collider component
        const collider = this.webViewSceneObject.getComponent("Physics.ColliderComponent")
        if (collider) {
            print("Found Collider component")
        }
        
        // List all components
        const componentCount = this.webViewSceneObject.getComponentCount()
        print(`WebView object has ${componentCount} components:`)
        for (let i = 0; i < componentCount; i++) {
            const component = this.webViewSceneObject.getComponentByIndex(i)
            print(`  - ${component.getTypeName()}`)
        }
    }
    
    /**
     * Demonstrate hierarchy navigation
     */
    private demonstrateHierarchyNavigation() {
        if (!this.webViewSceneObject) return
        
        print("--- Hierarchy Navigation ---")
        
        // Navigate up the hierarchy
        let currentObject: SceneObject | null = this.webViewSceneObject
        let level = 0
        
        while (currentObject) {
            const indent = "  ".repeat(level)
            print(`${indent}Level ${level}: ${currentObject.name}`)
            
            // Show children at this level
            const childCount = currentObject.getChildrenCount()
            if (childCount > 0) {
                print(`${indent}  Has ${childCount} children:`)
                for (let i = 0; i < childCount; i++) {
                    const child = currentObject.getChild(i)
                    print(`${indent}    - ${child.name}`)
                }
            }
            
            currentObject = currentObject.getParent()
            level++
            
            if (level > 5) break // Prevent infinite loop
        }
    }
    
    /**
     * Public method to change WebView URL from external scripts
     */
    public changeWebViewUrl(newUrl: string) {
        if (this.webViewComponent) {
            try {
                this.webViewComponent.goToUrl(newUrl)
                print(`WebView URL changed to: ${newUrl}`)
            } catch (e) {
                print(`Error changing URL: ${e.toString()}`)
            }
        } else {
            print("WebView component not available")
        }
    }
    
    /**
     * Public method to get reference to WebView component
     */
    public getWebViewComponent(): WebView | null {
        return this.webViewComponent
    }
    
    /**
     * Public method to get reference to WebView scene object
     */
    public getWebViewSceneObject(): SceneObject | null {
        return this.webViewSceneObject
    }
}
