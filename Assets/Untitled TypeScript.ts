@component
export class DownloadGltfAutoSpawn extends BaseScriptComponent {
    private remoteServiceModule: RemoteServiceModule = require('LensStudio:RemoteServiceModule');
    private remoteMediaModule: RemoteMediaModule = require('LensStudio:RemoteMediaModule');

    // Small public GLB URL that works in Lens Studio
    private gltfUrl: string = 'https://rawcdn.githack.com/KhronosGroup/glTF-Sample-Models/master/2.0/Duck/glTF-Binary/Duck.glb';

    onAwake() {
        if (!this.remoteServiceModule || !this.remoteMediaModule) {
            print('Remote Service Module or Remote Media Module is missing.');
            return;
        }

        print('Fetching GLTF asset from: ' + this.gltfUrl);
        const resource: DynamicResource = this.remoteServiceModule.makeResourceFromUrl(this.gltfUrl);

        if (!resource) {
            print('Failed to create resource from URL.');
            return;
        }

        this.remoteMediaModule.loadResourceAsGltfAsset(
            resource,
            (gltfAsset) => {
                if (!gltfAsset) {
                    print('GLTF asset failed to load.');
                    return; // Prevent InternalError
                }

                const gltfSettings = GltfSettings.create();
                gltfSettings.convertMetersToCentimeters = true;

                gltfAsset.tryInstantiateAsync(
                    this.sceneObject,
                    undefined, // Use GLTF's own materials
                    (sceneObj) => {
                        // Move 100 cm in front of the script's sceneObject
                        const transform = sceneObj.getTransform();
                        const localPos = new vec3(0, 0, -100);
                        transform.setLocalPosition(localPos);

                        // Play animation if available
                        const animationPlayer = sceneObj.getChild(0)?.getChild(0)?.getComponent('AnimationPlayer');
                        if (animationPlayer) {
                            animationPlayer.playClipAt('Talk', 0);
                            print('Playing animation: Talk');
                        } else {
                            print('No Animation Player found.');
                        }
                    },
                    (error) => print('Instantiation error: ' + error),
                    (progress) => print('Progress: ' + progress),
                    gltfSettings
                );
            },
            (error) => print('GLTF load error: ' + error)
        );
    }
}
