/**
 * Model Viewer for Watch Try-On
 * Provides a 3D model viewer for watches when AR is not supported
 */

class ModelViewer {
    constructor(container, modelUrl) {
        if (!container) {
            throw new Error('Container element is required');
        }
        
        this.container = container;
        this.modelUrl = modelUrl;
        this.scene = null;
        this.camera = null;
        this.renderer = null;
        this.controls = null;
        this.model = null;
        this.animationMixer = null;
        this.clock = new THREE.Clock();
        this.isAnimating = false;
        
        // Bind methods
        this.animate = this.animate.bind(this);
        this.onWindowResize = this.onWindowResize.bind(this);
    }
    
    async initialize() {
        try {
            // Check if required libraries are available
            if (!window.THREE) {
                throw new Error('THREE.js not available');
            }
            
            // Setup scene
            await this.setupScene();
            
            // Load model if URL provided
            if (this.modelUrl) {
                await this.loadModel();
            } else {
                this.createFallbackModel();
            }
            
            // Start animation
            this.isAnimating = true;
            this.animate();
            
            return this;
        } catch (error) {
            console.error('Error initializing model viewer:', error);
            this.dispose();
            throw error;
        }
    }
    
    async setupScene() {
        // Create scene
        this.scene = new THREE.Scene();
        this.scene.background = new THREE.Color(0xf0f0f0);
        
        // Setup camera
        const width = this.container.clientWidth;
        const height = this.container.clientHeight;
        this.camera = new THREE.PerspectiveCamera(
            60,
            width / height,
            0.1,
            1000
        );
        this.camera.position.z = 5;
        this.camera.position.y = 1;
        this.camera.lookAt(0, 0, 0);
        
        // Check for existing canvas and remove it if found and if it's a child of the container
        const existingCanvas = this.container.querySelector('canvas');
        if (existingCanvas && existingCanvas.parentNode === this.container) {
            this.container.removeChild(existingCanvas);
        }
        
        // Create a new canvas element
        const canvas = document.createElement('canvas');
        canvas.style.width = '100%';
        canvas.style.height = '100%';
        this.container.appendChild(canvas);
        
        // Setup renderer
        try {
            this.renderer = new THREE.WebGLRenderer({
                antialias: true,
                canvas: canvas,
                preserveDrawingBuffer: true
            });
            this.renderer.setSize(width, height);
            this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
            this.renderer.shadowMap.enabled = true;
            this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
        } catch (error) {
            console.error('Error creating WebGL renderer:', error);
            throw new Error('Error creating WebGL context: ' + error.message);
        }
        
        // Setup lighting
        const ambientLight = new THREE.AmbientLight(0xffffff, 0.7);
        this.scene.add(ambientLight);
        
        const directionalLight = new THREE.DirectionalLight(0xffffff, 1.0);
        directionalLight.position.set(5, 5, 5);
        directionalLight.castShadow = true;
        directionalLight.shadow.mapSize.width = 1024;
        directionalLight.shadow.mapSize.height = 1024;
        this.scene.add(directionalLight);
        
        // Add fill light
        const fillLight = new THREE.DirectionalLight(0xffffff, 0.5);
        fillLight.position.set(-5, -5, 5);
        this.scene.add(fillLight);
        
        // Add orbit controls
        this.controls = new OrbitControls(this.camera, this.renderer.domElement);
        this.controls.enableDamping = true;
        this.controls.dampingFactor = 0.05;
        this.controls.screenSpacePanning = false;
        this.controls.minDistance = 2;
        this.controls.maxDistance = 10;
        this.controls.maxPolarAngle = Math.PI / 2;
        
        // Handle window resize
        window.addEventListener('resize', this.onWindowResize);
    }
    
    async loadModel() {
        if (!this.scene) {
            throw new Error('Scene not initialized');
        }
        
        return new Promise((resolve, reject) => {
            try {
                // Check if GLTFLoader is available
                if (!window.GLTFLoader) {
                    console.error('GLTFLoader not available');
                    this.createFallbackModel();
                    resolve();
                    return;
                }
                
                const loader = new window.GLTFLoader();
                
                // Add a timeout for model loading
                const timeoutId = setTimeout(() => {
                    console.warn('Model loading timed out, using fallback model');
                    this.createFallbackModel();
                    resolve();
                }, 10000); // 10 second timeout
                
                loader.load(
                    this.modelUrl,
                    (gltf) => {
                        // Clear the timeout
                        clearTimeout(timeoutId);
                        
                        // Remove any existing model
                        if (this.model) {
                            this.scene.remove(this.model);
                        }
                        
                        this.model = gltf.scene;
                        
                        // Center and scale model
                        const box = new THREE.Box3().setFromObject(this.model);
                        const size = box.getSize(new THREE.Vector3()).length();
                        const center = box.getCenter(new THREE.Vector3());
                        
                        this.model.position.x = -center.x;
                        this.model.position.y = -center.y;
                        this.model.position.z = -center.z;
                        
                        const scale = 2 / size;
                        this.model.scale.set(scale, scale, scale);
                        
                        // Enable shadows
                        this.model.traverse((node) => {
                            if (node.isMesh) {
                                node.castShadow = true;
                                node.receiveShadow = true;
                            }
                        });
                        
                        this.scene.add(this.model);
                        
                        // Setup animation if available
                        if (gltf.animations && gltf.animations.length) {
                            this.animationMixer = new THREE.AnimationMixer(this.model);
                            const animation = gltf.animations[0];
                            const action = this.animationMixer.clipAction(animation);
                            action.play();
                        }
                        
                        resolve();
                    },
                    (xhr) => {
                        const progress = (xhr.loaded / xhr.total) * 100;
                        console.log(`Loading model: ${progress.toFixed(2)}%`);
                    },
                    (error) => {
                        // Clear the timeout
                        clearTimeout(timeoutId);
                        
                        console.error('Error loading model:', error);
                        this.createFallbackModel();
                        resolve();
                    }
                );
            } catch (error) {
                console.error('Error setting up model loader:', error);
                this.createFallbackModel();
                resolve();
            }
        });
    }
    
    createFallbackModel() {
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
        
        // Watch face details (hour markers)
        for (let i = 0; i < 12; i++) {
            const angle = (i / 12) * Math.PI * 2;
            const markerGeometry = new THREE.BoxGeometry(0.05, 0.05, 0.01);
            const markerMaterial = new THREE.MeshBasicMaterial({ color: 0xffffff });
            const marker = new THREE.Mesh(markerGeometry, markerMaterial);
            
            marker.position.x = Math.sin(angle) * 0.4;
            marker.position.y = Math.cos(angle) * 0.4;
            marker.position.z = 0.06;
            
            watchGroup.add(marker);
        }
        
        // Watch hands
        const hourHandGeometry = new THREE.BoxGeometry(0.05, 0.25, 0.01);
        const handMaterial = new THREE.MeshBasicMaterial({ color: 0xffffff });
        const hourHand = new THREE.Mesh(hourHandGeometry, handMaterial);
        hourHand.position.z = 0.07;
        hourHand.position.y = 0.12;
        watchGroup.add(hourHand);
        
        const minuteHandGeometry = new THREE.BoxGeometry(0.03, 0.35, 0.01);
        const minuteHand = new THREE.Mesh(minuteHandGeometry, handMaterial);
        minuteHand.position.z = 0.08;
        minuteHand.position.y = 0.17;
        watchGroup.add(minuteHand);
        
        // Remove any existing model
        if (this.model) {
            this.scene.remove(this.model);
        }
        
        this.model = watchGroup;
        this.scene.add(this.model);
    }
    
    animate() {
        if (!this.isAnimating) return;
        
        requestAnimationFrame(this.animate);
        
        // Update controls if available
        if (this.controls) {
            this.controls.update();
        }
        
        // Update animation mixer
        if (this.animationMixer) {
            const delta = this.clock.getDelta();
            this.animationMixer.update(delta);
        }
        
        // Auto-rotate model
        if (this.model) {
            this.model.rotation.y += 0.002;
        }
        
        // Render scene
        if (this.renderer && this.scene && this.camera) {
            this.renderer.render(this.scene, this.camera);
        }
    }
    
    onWindowResize() {
        if (!this.camera || !this.renderer || !this.container) return;
        
        const width = this.container.clientWidth;
        const height = this.container.clientHeight;
        
        this.camera.aspect = width / height;
        this.camera.updateProjectionMatrix();
        this.renderer.setSize(width, height);
    }
    
    dispose() {
        try {
            // Stop animation loop
            if (this._animationFrameId) {
                try {
                    cancelAnimationFrame(this._animationFrameId);
                } catch (error) {
                    console.warn('Error canceling animation frame:', error);
                }
            }
            
            // Clean up THREE.js resources
            if (this.scene) {
                try {
                    // Dispose of all geometries and materials
                    this.scene.traverse((object) => {
                        if (object.geometry) {
                            object.geometry.dispose();
                        }
                        
                        if (object.material) {
                            if (Array.isArray(object.material)) {
                                object.material.forEach(material => material.dispose());
                            } else {
                                object.material.dispose();
                            }
                        }
                    });
                    
                    // Clear the scene
                    while(this.scene.children.length > 0) { 
                        this.scene.remove(this.scene.children[0]); 
                    }
                } catch (error) {
                    console.warn('Error cleaning up scene:', error);
                }
                
                this.scene = null;
            }
            
            // Clean up renderer
            if (this.renderer) {
                try {
                    this.renderer.dispose();
                    
                    // Force context loss to ensure clean WebGL context
                    const gl = this.renderer.getContext();
                    if (gl && gl.getExtension('WEBGL_lose_context')) {
                        gl.getExtension('WEBGL_lose_context').loseContext();
                    }
                    
                    // Remove canvas element
                    if (this.renderer.domElement && this.renderer.domElement.parentNode) {
                        this.renderer.domElement.parentNode.removeChild(this.renderer.domElement);
                    }
                } catch (error) {
                    console.warn('Error disposing renderer:', error);
                }
                
                this.renderer = null;
            }
            
            // Clean up controls
            if (this.controls) {
                try {
                    this.controls.dispose();
                } catch (error) {
                    console.warn('Error disposing controls:', error);
                }
                this.controls = null;
            }
            
            // Clear references
            this.camera = null;
            this.model = null;
            this.animationMixer = null;
            
            try {
                window.removeEventListener('resize', this.onWindowResize);
            } catch (error) {
                console.warn('Error removing event listener:', error);
            }
            
            console.log('ModelViewer resources disposed');
        } catch (error) {
            console.error('Error in ModelViewer.dispose():', error);
        }
    }
}

// Initialize model viewer
window.initModelViewer = async function(options) {
    const { container, modelUrl } = options;
    
    // Create a class to handle the model viewer
    class ModelViewer {
        constructor(container, modelUrl) {
            this.container = container;
            this.modelUrl = modelUrl;
            this.scene = null;
            this.camera = null;
            this.renderer = null;
            this.model = null;
            this.controls = null;
            this.animationMixer = null;
            this.clock = new THREE.Clock();
            
            // Bind methods
            this.onWindowResize = this.onWindowResize.bind(this);
            this.animate = this.animate.bind(this);
        }
        
        async initialize() {
            try {
                await this.setupScene();
                await this.loadModel();
                this.startAnimation();
                return this;
            } catch (error) {
                console.error('Error initializing model viewer:', error);
                this.dispose();
                throw error;
            }
        }
        
        async setupScene() {
            // Create scene
            this.scene = new THREE.Scene();
            this.scene.background = new THREE.Color(0xf0f0f0);
            
            // Setup camera
            const width = this.container.clientWidth;
            const height = this.container.clientHeight;
            this.camera = new THREE.PerspectiveCamera(
                60,
                width / height,
                0.1,
                1000
            );
            this.camera.position.z = 5;
            this.camera.position.y = 1;
            this.camera.lookAt(0, 0, 0);
            
            // Check for existing canvas and remove it if found and if it's a child of the container
            const existingCanvas = this.container.querySelector('canvas');
            if (existingCanvas && existingCanvas.parentNode === this.container) {
                this.container.removeChild(existingCanvas);
            }
            
            // Create a new canvas element
            const canvas = document.createElement('canvas');
            canvas.style.width = '100%';
            canvas.style.height = '100%';
            this.container.appendChild(canvas);
            
            // Setup renderer
            try {
                this.renderer = new THREE.WebGLRenderer({
                    antialias: true,
                    canvas: canvas,
                    preserveDrawingBuffer: true
                });
                this.renderer.setSize(width, height);
                this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
                this.renderer.shadowMap.enabled = true;
                this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
            } catch (error) {
                console.error('Error creating WebGL renderer:', error);
                throw new Error('Error creating WebGL context: ' + error.message);
            }
            
            // Setup lighting
            const ambientLight = new THREE.AmbientLight(0xffffff, 0.7);
            this.scene.add(ambientLight);
            
            const directionalLight = new THREE.DirectionalLight(0xffffff, 1.0);
            directionalLight.position.set(5, 5, 5);
            directionalLight.castShadow = true;
            directionalLight.shadow.mapSize.width = 1024;
            directionalLight.shadow.mapSize.height = 1024;
            this.scene.add(directionalLight);
            
            // Add fill light
            const fillLight = new THREE.DirectionalLight(0xffffff, 0.5);
            fillLight.position.set(-5, -5, 5);
            this.scene.add(fillLight);
            
            // Add orbit controls
            this.controls = new OrbitControls(this.camera, this.renderer.domElement);
            this.controls.enableDamping = true;
            this.controls.dampingFactor = 0.05;
            this.controls.screenSpacePanning = false;
            this.controls.minDistance = 2;
            this.controls.maxDistance = 10;
            this.controls.maxPolarAngle = Math.PI / 2;
            
            // Handle window resize
            window.addEventListener('resize', this.onWindowResize);
        }
        
        async loadModel() {
            return new Promise((resolve, reject) => {
                const loader = new GLTFLoader();
                
                loader.load(
                    this.modelUrl,
                    (gltf) => {
                        this.model = gltf.scene;
                        
                        // Center model
                        const box = new THREE.Box3().setFromObject(this.model);
                        const center = box.getCenter(new THREE.Vector3());
                        this.model.position.x = -center.x;
                        this.model.position.y = -center.y;
                        this.model.position.z = -center.z;
                        
                        // Scale model
                        const size = box.getSize(new THREE.Vector3());
                        const maxDim = Math.max(size.x, size.y, size.z);
                        const scale = 2 / maxDim;
                        this.model.scale.set(scale, scale, scale);
                        
                        // Enable shadows
                        this.model.traverse((node) => {
                            if (node.isMesh) {
                                node.castShadow = true;
                                node.receiveShadow = true;
                            }
                        });
                        
                        // Add model to scene
                        this.scene.add(this.model);
                        
                        // Setup animation if available
                        if (gltf.animations && gltf.animations.length) {
                            this.animationMixer = new THREE.AnimationMixer(this.model);
                            const animation = gltf.animations[0];
                            const action = this.animationMixer.clipAction(animation);
                            action.play();
                        }
                        
                        resolve();
                    },
                    (xhr) => {
                        const progress = (xhr.loaded / xhr.total) * 100;
                        console.log(`Loading model: ${progress.toFixed(2)}%`);
                    },
                    (error) => {
                        console.error('Error loading model:', error);
                        reject(error);
                    }
                );
            });
        }
        
        startAnimation() {
            this.animate();
        }
        
        animate() {
            requestAnimationFrame(this.animate);
            
            // Update controls
            if (this.controls) {
                this.controls.update();
            }
            
            // Update animation mixer
            if (this.animationMixer) {
                const delta = this.clock.getDelta();
                this.animationMixer.update(delta);
            }
            
            // Auto-rotate model
            if (this.model) {
                this.model.rotation.y += 0.002;
            }
            
            // Render scene
            if (this.renderer && this.scene && this.camera) {
                this.renderer.render(this.scene, this.camera);
            }
        }
        
        onWindowResize() {
            if (!this.camera || !this.renderer) return;
            
            const width = this.container.clientWidth;
            const height = this.container.clientHeight;
            
            this.camera.aspect = width / height;
            this.camera.updateProjectionMatrix();
            this.renderer.setSize(width, height);
        }
        
        dispose() {
            // Stop animation loop
            if (this._animationFrameId) {
                try {
                    cancelAnimationFrame(this._animationFrameId);
                } catch (error) {
                    console.warn('Error canceling animation frame:', error);
                }
            }
            
            // Clean up THREE.js resources
            if (this.scene) {
                try {
                    // Dispose of all geometries and materials
                    this.scene.traverse((object) => {
                        if (object.geometry) {
                            object.geometry.dispose();
                        }
                        
                        if (object.material) {
                            if (Array.isArray(object.material)) {
                                object.material.forEach(material => material.dispose());
                            } else {
                                object.material.dispose();
                            }
                        }
                    });
                    
                    // Clear the scene
                    while(this.scene.children.length > 0) { 
                        this.scene.remove(this.scene.children[0]); 
                    }
                } catch (error) {
                    console.warn('Error cleaning up scene:', error);
                }
                
                this.scene = null;
            }
            
            // Clean up renderer
            if (this.renderer) {
                try {
                    this.renderer.dispose();
                    
                    // Force context loss to ensure clean WebGL context
                    const gl = this.renderer.getContext();
                    if (gl && gl.getExtension('WEBGL_lose_context')) {
                        gl.getExtension('WEBGL_lose_context').loseContext();
                    }
                    
                    // Remove canvas element
                    if (this.renderer.domElement && this.renderer.domElement.parentNode) {
                        this.renderer.domElement.parentNode.removeChild(this.renderer.domElement);
                    }
                } catch (error) {
                    console.warn('Error disposing renderer:', error);
                }
                
                this.renderer = null;
            }
            
            // Clean up controls
            if (this.controls) {
                try {
                    this.controls.dispose();
                } catch (error) {
                    console.warn('Error disposing controls:', error);
                }
                this.controls = null;
            }
            
            // Clear references
            this.camera = null;
            this.model = null;
            this.animationMixer = null;
            
            try {
                window.removeEventListener('resize', this.onWindowResize);
            } catch (error) {
                console.warn('Error removing event listener:', error);
            }
            
            console.log('ModelViewer resources disposed');
        }
    }
    
    try {
        const viewer = new ModelViewer(container, modelUrl);
        return await viewer.initialize();
    } catch (error) {
        console.error('Failed to initialize model viewer:', error);
        return null;
    }
}; 