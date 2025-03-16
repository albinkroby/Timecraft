/**
 * WebXR Controller for Watch Try-On
 * Implements markerless AR for watch visualization using WebXR API
 */

// Global WebXR controller instance
let webXRController = null;

// Initialize WebXR Experience
window.initWebXRExperience = async function(watchData) {
    // Show loading screen while we initialize
    const loadingElement = document.getElementById('ar-loading');
    const loadingText = document.getElementById('loading-text');
    
    try {
        // Update loading status
        if (loadingText) loadingText.textContent = 'Loading watch model...';
        
        // Check if WebXR is supported
        if (!navigator.xr) {
            throw new Error('WebXR not supported on this device');
        }
        
        // Check if immersive-ar is supported
        const isARSupported = await navigator.xr.isSessionSupported('immersive-ar');
        if (!isARSupported) {
            throw new Error('Immersive AR not supported on this device');
        }
        
        // Initialize controller if not already created
        if (!webXRController) {
            webXRController = new WebXRWatchController();
        }
        
        // Initialize WebXR with watch data
        await webXRController.initialize(watchData);
        
        // Hide loading screen when ready
        if (loadingElement) loadingElement.style.display = 'none';
        
        return true;
    } catch (error) {
        console.error('Failed to initialize WebXR experience:', error);
        
        // Update loading error
        if (loadingText) loadingText.textContent = 'Error: ' + error.message;
        
        // Hide loading after a delay
        setTimeout(() => {
            if (loadingElement) loadingElement.style.display = 'none';
            document.getElementById('ar-not-supported').style.display = 'flex';
        }, 1500);
        
        throw error;
    }
};

class WebXRWatchController {
    constructor() {
        // Core XR elements
        this.canvas = document.getElementById('ar-canvas');
        this.gl = null;
        this.scene = null;
        this.camera = null;
        this.renderer = null;
        this.xrSession = null;
        this.xrReferenceSpace = null;
        this.xrHitTestSource = null;
        
        // Watch model elements
        this.watchModel = null;
        this.watchData = null;
        this.modelPlaced = false;
        
        // Watch scaling factors
        this.initialScale = 0.05;
        this.currentScale = this.initialScale;
        this.scaleStep = 0.01;
        
        // Tracking state
        this.isTracking = false;
        
        // Bind UI controls
        this.bindUIControls();
    }
    
    async initialize(watchData) {
        console.log('Initializing WebXR with watch data:', watchData);
        this.watchData = watchData;
        
        try {
            await this.initThreeJS();
            await this.loadWatchModel(watchData.modelUrl);
            
            return true;
        } catch (error) {
            console.error('Error initializing WebXR controller:', error);
            throw error;
        }
    }
    
    async initThreeJS() {
        // Initialize THREE.js scene
        this.scene = new THREE.Scene();
        
        // Setup camera
        this.camera = new THREE.PerspectiveCamera(70, window.innerWidth / window.innerHeight, 0.01, 20);
        
        // Setup lighting
        const ambientLight = new THREE.AmbientLight(0xcccccc, 0.5);
        this.scene.add(ambientLight);
        
        const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
        directionalLight.position.set(0, 1, 1).normalize();
        this.scene.add(directionalLight);
        
        // Setup renderer
        this.renderer = new THREE.WebGLRenderer({
            canvas: this.canvas,
            antialias: true,
            alpha: true,
            preserveDrawingBuffer: true // Needed for screenshots
        });
        
        this.renderer.setClearColor(0x000000, 0);
        this.renderer.setPixelRatio(window.devicePixelRatio);
        this.renderer.setSize(window.innerWidth, window.innerHeight);
        this.renderer.xr.enabled = true;
        
        // Get WebGL context
        this.gl = this.renderer.getContext();
        
        // Handle window resize
        window.addEventListener('resize', () => this.onResize());
    }
    
    async loadWatchModel(modelUrl) {
        // Show loading status
        const loadingText = document.getElementById('loading-text');
        if (loadingText) loadingText.textContent = 'Loading 3D model...';
        
        console.log('Loading model from URL:', modelUrl);
        
        // Use loader based on file extension
        const fileExtension = modelUrl.split('.').pop().toLowerCase();
        
        if (fileExtension === 'glb' || fileExtension === 'gltf') {
            // Use GLTFLoader for glTF/GLB files
            return new Promise((resolve, reject) => {
                try {
                    // Ensure THREE.GLTFLoader is available
                    if (!THREE.GLTFLoader) {
                        // Create a script element to load GLTFLoader
                        const script = document.createElement('script');
                        script.src = "https://cdn.jsdelivr.net/npm/three@0.152.2/examples/js/loaders/GLTFLoader.js";
                        script.onload = () => {
                            this.loadGLTFModel(modelUrl, resolve, reject, loadingText);
                        };
                        script.onerror = (error) => {
                            console.error('Error loading GLTFLoader:', error);
                            reject(new Error('Failed to load GLTFLoader'));
                        };
                        document.head.appendChild(script);
                    } else {
                        this.loadGLTFModel(modelUrl, resolve, reject, loadingText);
                    }
                } catch (error) {
                    console.error('Error setting up model loader:', error);
                    reject(error);
                }
            });
        } else {
            throw new Error('Unsupported model format: ' + fileExtension);
        }
    }
    
    loadGLTFModel(modelUrl, resolve, reject, loadingText) {
        const loader = new THREE.GLTFLoader();
        
        loader.load(
            // URL
            modelUrl,
            // Called when resource is loaded
            (gltf) => {
                console.log('Model loaded successfully');
                this.watchModel = gltf.scene;
                
                // Apply initial transformations
                this.watchModel.scale.set(
                    this.initialScale, 
                    this.initialScale, 
                    this.initialScale
                );
                
                // Center and rotate the model appropriately for a watch
                this.watchModel.rotation.x = -Math.PI / 2; // Rotate to face up
                this.watchModel.position.set(0, 0, 0);
                
                // Hide model initially - will be shown when placed
                this.watchModel.visible = false;
                
                // Add to scene
                this.scene.add(this.watchModel);
                
                resolve();
            },
            // Called while loading is progressing
            (xhr) => {
                // Progress update
                const percent = xhr.total ? Math.floor((xhr.loaded / xhr.total) * 100) : 0;
                if (loadingText && percent > 0) loadingText.textContent = `Loading model: ${percent}%`;
            },
            // Called when loading has errors
            (error) => {
                console.error('Error loading watch model:', error);
                reject(error);
            }
        );
    }
    
    async startARSession() {
        if (this.xrSession) {
            console.warn('AR session already in progress');
            return;
        }
        
        try {
            // Request a new XR session
            this.xrSession = await navigator.xr.requestSession('immersive-ar', {
                requiredFeatures: ['hit-test'],
                optionalFeatures: ['dom-overlay'],
                domOverlay: { root: document.getElementById('ar-overlay') }
            });
            
            // Set up session events
            this.xrSession.addEventListener('end', () => {
                this.onXRSessionEnded();
            });
            
            // Configure renderer for the session
            this.renderer.xr.setReferenceSpaceType('local');
            await this.renderer.xr.setSession(this.xrSession);
            
            // Get reference space
            this.xrReferenceSpace = await this.xrSession.requestReferenceSpace('local');
            
            // Set up hit testing
            const viewerSpace = await this.xrSession.requestReferenceSpace('viewer');
            this.xrHitTestSource = await this.xrSession.requestHitTestSource({ space: viewerSpace });
            
            // Update tracking status
            const trackingStatus = document.getElementById('tracking-status');
            if (trackingStatus) {
                trackingStatus.style.display = 'flex';
                trackingStatus.querySelector('.status-text').textContent = 'Looking for surface...';
            }
            
            // Start rendering loop
            this.renderer.setAnimationLoop((time, frame) => this.onXRFrame(time, frame));
            
            // Show position guide
            const positionGuide = document.getElementById('position-guide');
            if (positionGuide) {
                positionGuide.style.display = 'flex';
            }
            
            console.log('WebXR session started');
            this.isTracking = true;
            
        } catch (error) {
            console.error('Error starting AR session:', error);
            
            // Show error message
            const notSupportedElement = document.getElementById('ar-not-supported');
            if (notSupportedElement) {
                notSupportedElement.style.display = 'flex';
            }
        }
    }
    
    onXRFrame(time, frame) {
        if (!this.xrSession || !frame) return;
        
        // Get pose
        const pose = frame.getViewerPose(this.xrReferenceSpace);
        if (!pose) return;
        
        // Process hit test results if model not placed yet
        if (!this.modelPlaced && this.xrHitTestSource) {
            const hitTestResults = frame.getHitTestResults(this.xrHitTestSource);
            
            if (hitTestResults.length > 0) {
                // We got a hit result
                const trackingStatus = document.getElementById('tracking-status');
                if (trackingStatus) {
                    trackingStatus.classList.add('found');
                    trackingStatus.querySelector('.status-text').textContent = 'Surface found! Tap to place';
                }
                
                // Check for touch to place model
                if (this.isTouching) {
                    this.isTouching = false;
                    
                    // Get hit pose
                    const hit = hitTestResults[0];
                    const hitPose = hit.getPose(this.xrReferenceSpace);
                    
                    // Place model at hit position
                    if (this.watchModel) {
                        this.watchModel.visible = true;
                        this.watchModel.position.set(
                            hitPose.transform.position.x,
                            hitPose.transform.position.y,
                            hitPose.transform.position.z
                        );
                        
                        // Mark as placed
                        this.modelPlaced = true;
                        
                        // Update status
                        if (trackingStatus) {
                            trackingStatus.querySelector('.status-text').textContent = 'Watch placed!';
                            
                            // Hide status after a few seconds
                            setTimeout(() => {
                                trackingStatus.style.display = 'none';
                            }, 3000);
                        }
                        
                        // Hide position guide
                        const positionGuide = document.getElementById('position-guide');
                        if (positionGuide) {
                            positionGuide.style.display = 'none';
                        }
                    }
                }
            }
        }
        
        // Render the scene
        this.renderer.render(this.scene, this.camera);
    }
    
    onXRSessionEnded() {
        console.log('WebXR session ended');
        
        // Reset state
        this.xrSession = null;
        this.xrReferenceSpace = null;
        this.xrHitTestSource = null;
        this.modelPlaced = false;
        this.isTracking = false;
        
        // Hide tracking status
        const trackingStatus = document.getElementById('tracking-status');
        if (trackingStatus) {
            trackingStatus.style.display = 'none';
        }
        
        // Stop animation loop
        this.renderer.setAnimationLoop(null);
        
        // Show AR button again
        const arButton = document.getElementById('ar-button');
        if (arButton) {
            arButton.style.display = 'block';
        }
        
        // Show instructions again
        const arInstructions = document.getElementById('ar-instructions');
        if (arInstructions) {
            arInstructions.style.display = 'block';
        }
    }
    
    endARSession() {
        if (this.xrSession) {
            this.xrSession.end();
        }
    }
    
    onResize() {
        if (!this.renderer) return;
        
        // Update renderer size
        this.renderer.setSize(window.innerWidth, window.innerHeight);
        
        // Update camera aspect ratio
        if (this.camera) {
            this.camera.aspect = window.innerWidth / window.innerHeight;
            this.camera.updateProjectionMatrix();
        }
    }
    
    bindUIControls() {
        // Add touch event listener for placing model
        this.canvas.addEventListener('touchstart', () => {
            this.isTouching = true;
        });
        
        // Find control buttons
        const exitArBtn = document.getElementById('exit-ar');
        const captureArBtn = document.getElementById('capture-ar');
        const sizeSmallerBtn = document.getElementById('size-smaller');
        const sizeLargerBtn = document.getElementById('size-larger');
        
        // Exit AR
        if (exitArBtn) {
            exitArBtn.addEventListener('click', () => {
                this.endARSession();
            });
        }
        
        // Capture screenshot
        if (captureArBtn) {
            captureArBtn.addEventListener('click', () => this.captureScreenshot());
        }
        
        // Size control
        if (sizeSmallerBtn) {
            sizeSmallerBtn.addEventListener('click', () => this.resizeModel(false));
        }
        
        if (sizeLargerBtn) {
            sizeLargerBtn.addEventListener('click', () => this.resizeModel(true));
        }
    }
    
    resizeModel(larger) {
        if (!this.watchModel || !this.modelPlaced) return;
        
        // Adjust scale
        if (larger) {
            this.currentScale += this.scaleStep;
            if (this.currentScale > this.initialScale * 3) {
                this.currentScale = this.initialScale * 3; // Max size
            }
        } else {
            this.currentScale -= this.scaleStep;
            if (this.currentScale < this.initialScale * 0.5) {
                this.currentScale = this.initialScale * 0.5; // Min size
            }
        }
        
        // Apply new scale
        this.watchModel.scale.set(
            this.currentScale, 
            this.currentScale, 
            this.currentScale
        );
        
        console.log(`Model resized to scale: ${this.currentScale}`);
    }
    
    captureScreenshot() {
        // Only capture if AR is running and model is placed
        if (!this.renderer || !this.modelPlaced) {
            alert('Place the watch before taking a photo.');
            return;
        }
        
        try {
            // Capture the canvas
            const dataURL = this.canvas.toDataURL('image/png');
            
            // Get elements
            const captureSuccessEl = document.getElementById('capture-success');
            const capturedImageEl = document.getElementById('captured-image-preview');
            const downloadBtn = document.getElementById('download-capture');
            const shareBtn = document.getElementById('share-capture');
            const continueBtn = document.getElementById('continue-ar');
            
            // Display the captured image
            if (captureSuccessEl && capturedImageEl) {
                // Create image preview
                capturedImageEl.innerHTML = '';
                const img = document.createElement('img');
                img.src = dataURL;
                img.style.width = '100%';
                img.style.borderRadius = '5px';
                capturedImageEl.appendChild(img);
                
                // Show the capture success screen
                captureSuccessEl.style.display = 'flex';
                // Store image data for sharing/downloading
                captureSuccessEl.dataset.imageData = dataURL;
            }
            
            // Set up download button
            if (downloadBtn) {
                downloadBtn.onclick = () => this.downloadImage(dataURL);
            }
            
            // Set up share button
            if (shareBtn) {
                shareBtn.onclick = () => this.shareImage(dataURL);
            }
            
            // Set up continue button
            if (continueBtn) {
                continueBtn.onclick = () => {
                    if (captureSuccessEl) captureSuccessEl.style.display = 'none';
                };
            }
            
        } catch (error) {
            console.error('Error capturing screenshot:', error);
            alert('Failed to capture screenshot. Please try again.');
        }
    }
    
    async shareImage(imageData) {
        if (!imageData) return;

        if (navigator.share) {
            try {
                const blob = await (await fetch(imageData)).blob();
                const file = new File([blob], "timecraft-ar-watch.png", { type: "image/png" });
                
                await navigator.share({
                    title: 'My AR Watch Try-On',
                    text: 'Check out this watch in AR!',
                    files: [file]
                });
            } catch (error) {
                console.error('Error sharing:', error);
                this.downloadImage(imageData); // Fallback to download if sharing fails
            }
        } else {
            this.downloadImage(imageData); // Fallback for browsers that don't support sharing
        }
    }
    
    downloadImage(imageData) {
        if (!imageData) return;
        
        const link = document.createElement('a');
        link.href = imageData;
        link.download = `timecraft-ar-watch-${Date.now()}.png`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }
} 