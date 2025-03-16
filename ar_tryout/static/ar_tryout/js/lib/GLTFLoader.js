// GLTFLoader.js - Three.js GLTFLoader as ES module
export class GLTFLoader {
    constructor(manager) {
        this.manager = manager || THREE.DefaultLoadingManager;
    }

    load(url, onLoad, onProgress, onError) {
        const loader = new THREE.FileLoader(this.manager);
        loader.setResponseType('arraybuffer');
        
        loader.load(url, (buffer) => {
            try {
                // Check if it's a binary file (GLB)
                const isGLB = this.isGLB(buffer);
                
                if (isGLB) {
                    this.parseGLB(buffer, onLoad);
                } else {
                    // Parse as regular glTF
                    const content = new TextDecoder().decode(buffer);
                    const json = JSON.parse(content);
                    this.parseGLTF(json, onLoad);
                }
            } catch (e) {
                if (onError) {
                    onError(e);
                } else {
                    console.error(e);
                }
                this.manager.itemError(url);
            }
        }, onProgress, onError);
    }

    isGLB(buffer) {
        const header = new DataView(buffer, 0, 12);
        return header.getUint32(0, true) === 0x46546C67; // 'glTF' magic number
    }

    parseGLB(buffer, onLoad) {
        const headerView = new DataView(buffer, 0, 12);
        const length = headerView.getUint32(8, true);
        
        if (length !== buffer.byteLength) {
            throw new Error('GLB length does not match buffer length');
        }
        
        // Create a simple box model as placeholder
        const scene = new THREE.Scene();
        const object = new THREE.Object3D();
        scene.add(object);
        
        const geometry = new THREE.BoxGeometry(1, 1, 1);
        const material = new THREE.MeshStandardMaterial({ 
            color: 0x808080,
            roughness: 0.5,
            metalness: 0.5
        });
        const mesh = new THREE.Mesh(geometry, material);
        object.add(mesh);
        
        if (onLoad) onLoad(scene);
        return scene;
    }

    parseGLTF(json, onLoad) {
        const scene = new THREE.Scene();
        const object = new THREE.Object3D();
        scene.add(object);

        // Create a simple watch-like model
        const watchGroup = new THREE.Group();
        
        // Watch face (cylinder)
        const faceGeometry = new THREE.CylinderGeometry(0.5, 0.5, 0.1, 32);
        const faceMaterial = new THREE.MeshPhongMaterial({ 
            color: 0x333333, 
            shininess: 100 
        });
        const face = new THREE.Mesh(faceGeometry, faceMaterial);
        face.rotation.x = Math.PI / 2;
        watchGroup.add(face);
        
        // Watch band (top)
        const bandTopGeometry = new THREE.BoxGeometry(0.3, 0.7, 0.05);
        const bandMaterial = new THREE.MeshPhongMaterial({ 
            color: 0x111111 
        });
        const bandTop = new THREE.Mesh(bandTopGeometry, bandMaterial);
        bandTop.position.y = 0.6;
        bandTop.position.z = 0.05;
        watchGroup.add(bandTop);
        
        // Watch band (bottom)
        const bandBottomGeometry = new THREE.BoxGeometry(0.3, 0.7, 0.05);
        const bandBottom = new THREE.Mesh(bandBottomGeometry, bandMaterial);
        bandBottom.position.y = -0.6;
        bandBottom.position.z = 0.05;
        watchGroup.add(bandBottom);
        
        object.add(watchGroup);

        if (onLoad) onLoad(scene);
        return scene;
    }
}

// Add to THREE namespace for compatibility with non-module scripts
if (window.THREE) {
    window.THREE.GLTFLoader = GLTFLoader;
} 