/**
 * AR.js Controller for Watch Try-On
 * Implements marker-based AR for watch visualization
 */

// Use an immediately invoked function expression (IIFE) to avoid global variable conflicts
(function() {
    // Only define if not already defined
    if (window.ARWatchController) {
        console.log('ARWatchController already defined, skipping initialization');
        return;
    }
    
    // Global AR controller instance (scoped to this IIFE)
    let arController = null;
    
    // Initialize AR Experience
    window.initARExperience = async function(watchData) {
        // Show loading screen while we initialize
        const loadingElement = document.getElementById('ar-loading');
        const loadingText = document.getElementById('loading-text');
        
        try {
            // Update loading status
            if (loadingText) loadingText.textContent = 'Loading watch model...';
            
            // Initialize controller if not already created
            if (!arController) {
                arController = new window.ARWatchController();
            }
            
            // Initialize AR with watch data
            await arController.initialize(watchData);
            
            // Hide loading screen when ready
            if (loadingElement) loadingElement.style.display = 'none';
            
            return true;
        } catch (error) {
            console.error('Failed to initialize AR experience:', error);
            
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
    
    // Helper function to load AR.js if not already loaded
    async function ensureARJSLoaded() {
        if (typeof THREEx !== 'undefined') {
            console.log('THREEx is already defined, AR.js is loaded');
            return true;
        }
        
        console.log('THREEx is not defined, loading AR.js...');
        
        try {
            // Load AR.js components
            await new Promise((resolve, reject) => {
                const script = document.createElement('script');
                script.src = 'https://raw.githack.com/AR-js-org/AR.js/master/three.js/build/ar.js';
                script.onload = () => {
                    if (typeof THREEx !== 'undefined') {
                        console.log('AR.js loaded successfully');
                        resolve();
                    } else {
                        reject(new Error('Failed to load THREEx after loading AR.js'));
                    }
                };
                script.onerror = () => reject(new Error('Failed to load AR.js script'));
                document.head.appendChild(script);
                
                // Add timeout
                setTimeout(() => {
                    if (typeof THREEx === 'undefined') {
                        reject(new Error('AR.js loading timeout'));
                    }
                }, 5000);
            });
            
            return true;
        } catch (error) {
            console.error('Error loading AR.js:', error);
            throw error;
        }
    }
    
    // Helper function to create a fallback model when GLTFLoader fails
    function createFallbackModel() {
        console.log('Creating fallback model');
        
        // Create a simple watch-like model
        const group = new THREE.Group();
        
        // Watch face (cylinder)
        const faceGeometry = new THREE.CylinderGeometry(0.5, 0.5, 0.1, 32);
        const faceMaterial = new THREE.MeshPhongMaterial({ 
            color: 0x333333, 
            shininess: 100 
        });
        const face = new THREE.Mesh(faceGeometry, faceMaterial);
        face.rotation.x = Math.PI / 2;
        group.add(face);
        
        // Watch band (top)
        const bandTopGeometry = new THREE.BoxGeometry(0.3, 0.7, 0.05);
        const bandMaterial = new THREE.MeshPhongMaterial({ 
            color: 0x111111 
        });
        const bandTop = new THREE.Mesh(bandTopGeometry, bandMaterial);
        bandTop.position.y = 0.6;
        bandTop.position.z = 0.05;
        group.add(bandTop);
        
        // Watch band (bottom)
        const bandBottomGeometry = new THREE.BoxGeometry(0.3, 0.7, 0.05);
        const bandBottom = new THREE.Mesh(bandBottomGeometry, bandMaterial);
        bandBottom.position.y = -0.6;
        bandBottom.position.z = 0.05;
        group.add(bandBottom);
        
        // Watch face details (hour markers)
        for (let i = 0; i < 12; i++) {
            const angle = (i / 12) * Math.PI * 2;
            const markerGeometry = new THREE.BoxGeometry(0.05, 0.05, 0.01);
            const markerMaterial = new THREE.MeshBasicMaterial({ color: 0xffffff });
            const marker = new THREE.Mesh(markerGeometry, markerMaterial);
            
            marker.position.x = Math.sin(angle) * 0.4;
            marker.position.y = Math.cos(angle) * 0.4;
            marker.position.z = 0.06;
            
            group.add(marker);
        }
        
        // Watch hands
        const hourHandGeometry = new THREE.BoxGeometry(0.05, 0.25, 0.01);
        const handMaterial = new THREE.MeshBasicMaterial({ color: 0xffffff });
        const hourHand = new THREE.Mesh(hourHandGeometry, handMaterial);
        hourHand.position.z = 0.07;
        hourHand.position.y = 0.12;
        group.add(hourHand);
        
        const minuteHandGeometry = new THREE.BoxGeometry(0.03, 0.35, 0.01);
        const minuteHand = new THREE.Mesh(minuteHandGeometry, handMaterial);
        minuteHand.position.z = 0.08;
        minuteHand.position.y = 0.17;
        group.add(minuteHand);
        
        return group;
    }
    
    // Expose ARWatchController to global scope
    window.ARWatchController = class ARWatchController {
        constructor() {
            console.log('Creating new ARWatchController instance');
            
            // Core AR elements
            this.scene = null;
            this.camera = null;
            this.renderer = null;
            this.arToolkitContext = null;
            this.arToolkitSource = null;
            
            // Watch model elements
            this.watchModel = null;
            this.watchData = null;
            this.markerRoot = null;
            
            // Watch scaling factors
            this.initialScale = 0.05;
            this.currentScale = this.initialScale;
            this.scaleStep = 0.01;
            
            // Tracking state
            this.isMarkerVisible = false;
            
            // Bind UI controls
            this.bindUIControls();
        }
        
        async initialize(watchData) {
            console.log('Initializing AR with watch data:', watchData);
            this.watchData = watchData;
            
            try {
                await this.initThreeJS();
                
                // Ensure AR.js is loaded before initializing AR toolkit
                await ensureARJSLoaded();
                
                await this.initARToolkit();
                await this.loadWatchModel(watchData.modelUrl);
                this.setupARScene();
                
                // Start animation loop
                this.animate();
                
                return true;
            } catch (error) {
                console.error('Error initializing AR controller:', error);
                throw error;
            }
        }
        
        async initThreeJS() {
            // Initialize THREE.js scene
            this.scene = new THREE.Scene();
            
            // Setup camera
            this.camera = new THREE.Camera();
            this.scene.add(this.camera);
            
            // Setup lighting
            const ambientLight = new THREE.AmbientLight(0xcccccc, 0.5);
            this.scene.add(ambientLight);
            
            const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
            directionalLight.position.set(0, 1, 1).normalize();
            this.scene.add(directionalLight);
            
            // Setup renderer
            const canvas = document.getElementById('ar-canvas');
            this.renderer = new THREE.WebGLRenderer({
                canvas: canvas,
                antialias: true,
                alpha: true
            });
            
            this.renderer.setClearColor(new THREE.Color('lightgrey'), 0);
            
            // Set renderer size based on window size
            this.renderer.setSize(window.innerWidth, window.innerHeight);
            this.renderer.setPixelRatio(window.devicePixelRatio);
            
            // Handle window resize
            window.addEventListener('resize', () => this.onResize());
        }
        
        async initARToolkit() {
            try {
                // Check if THREEx is defined
                if (typeof THREEx === 'undefined') {
                    console.error('THREEx is not defined. AR.js may not be loaded properly.');
                    throw new Error('AR.js not loaded properly');
                }
                
                // Create AR source (for camera stream)
                this.arToolkitSource = new THREEx.ArToolkitSource({
                    sourceType: 'webcam',
                });
                
                // Initialize AR source and handle resize
                await new Promise((resolve, reject) => {
                    this.arToolkitSource.init(() => {
                        this.onResize();
                        resolve();
                    });
                    
                    // Add timeout for initialization
                    setTimeout(() => {
                        if (!this.arToolkitSource.ready) {
                            reject(new Error('AR source initialization timeout'));
                        }
                    }, 3000);
                });
                
                // Create AR context
                this.arToolkitContext = new THREEx.ArToolkitContext({
                    // Use pattern marker file from static folder
                    detectionMode: 'mono',
                    patternRatio: 0.75,
                    cameraParametersUrl: 'https://cdn.jsdelivr.net/gh/AR-js-org/AR.js@3.4.5/data/data/camera_para.dat',
                    maxDetectionRate: 30,
                });
                
                // Initialize context
                await new Promise((resolve, reject) => {
                    this.arToolkitContext.init(() => {
                        this.camera.projectionMatrix.copy(this.arToolkitContext.getProjectionMatrix());
                        resolve();
                    });
                    
                    // Add timeout for initialization
                    setTimeout(() => {
                        if (!this.arToolkitContext.arController) {
                            reject(new Error('AR context initialization timeout'));
                        }
                    }, 3000);
                });
                
                // Create marker root and add to scene
                this.markerRoot = new THREE.Group();
                this.scene.add(this.markerRoot);
                
                // Setup marker tracking
                this.arMarkerControls = new THREEx.ArMarkerControls(this.arToolkitContext, this.markerRoot, {
                    type: 'pattern',
                    patternUrl: 'https://cdn.jsdelivr.net/gh/AR-js-org/AR.js@3.4.5/data/data/patt.hiro',
                    changeMatrixMode: 'modelViewMatrix'
                });
                
                console.log('AR.js initialized successfully');
            } catch (error) {
                console.error('Error initializing AR toolkit:', error);
                throw new Error('Failed to initialize AR toolkit: ' + error.message);
            }
            
            // Track marker visibility for UI feedback
            this.trackingStatusElement = document.getElementById('tracking-status');
        }
        
        async loadWatchModel(modelUrl) {
            // Show loading status
            const loadingText = document.getElementById('loading-text');
            if (loadingText) loadingText.textContent = 'Loading 3D model...';
            
            console.log('Loading model from URL:', modelUrl);
            
            // Use loader based on file extension
            const fileExtension = modelUrl.split('.').pop().toLowerCase();
            
            if (fileExtension === 'glb' || fileExtension === 'gltf') {
                try {
                    // Check if GLTFLoader is available through the global loadGLTFLoader function
                    if (window.loadGLTFLoader) {
                        await window.loadGLTFLoader();
                    }
                    
                    // Check if GLTFLoader is available
                    if (!THREE.GLTFLoader) {
                        console.warn('GLTFLoader not available, using fallback model');
                        this.watchModel = createFallbackModel();
                        return;
                    }
                    
                    // Load the model using GLTFLoader
                    await new Promise((resolve, reject) => {
                        try {
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
                                    // Use fallback model on error
                                    console.warn('Using fallback model due to loading error');
                                    this.watchModel = createFallbackModel();
                                    resolve();
                                }
                            );
                        } catch (error) {
                            console.error('Error setting up model loader:', error);
                            // Use fallback model on error
                            console.warn('Using fallback model due to setup error');
                            this.watchModel = createFallbackModel();
                            resolve();
                        }
                    });
                } catch (error) {
                    console.error('Error in model loading process:', error);
                    // Use fallback model on any error
                    this.watchModel = createFallbackModel();
                }
            } else {
                console.warn('Unsupported model format: ' + fileExtension + ', using fallback model');
                this.watchModel = createFallbackModel();
            }
        }
        
        setupARScene() {
            // Add watch model to marker root
            if (this.watchModel && this.markerRoot) {
                this.markerRoot.add(this.watchModel);
                console.log('Watch model added to marker root');
            } else {
                console.error('Watch model or marker root not available');
            }
            
            // Show the position guide
            const positionGuide = document.getElementById('position-guide');
            if (positionGuide) {
                positionGuide.style.display = 'flex';
            }
        }
        
        animate() {
            // Request next animation frame
            requestAnimationFrame(() => this.animate());
            
            if (this.arToolkitSource && this.arToolkitSource.ready) {
                this.arToolkitContext.update(this.arToolkitSource.domElement);
                
                // Check marker visibility for status updates
                this.updateMarkerVisibility();
            }
            
            this.renderer.render(this.scene, this.camera);
        }
        
        updateMarkerVisibility() {
            // Check if marker is visible
            const isVisible = this.markerRoot.visible;
            
            // Only update UI when visibility changes
            if (isVisible !== this.isMarkerVisible) {
                this.isMarkerVisible = isVisible;
                
                if (this.trackingStatusElement) {
                    if (isVisible) {
                        this.trackingStatusElement.style.display = 'flex';
                        this.trackingStatusElement.classList.add('found');
                        this.trackingStatusElement.querySelector('.status-text').textContent = 'Marker found!';
                        
                        // Hide marker info when marker is found
                        const markerInfo = document.getElementById('marker-info');
                        if (markerInfo) markerInfo.style.display = 'none';
                        
                        // Hide guide when marker is found
                        const positionGuide = document.getElementById('position-guide');
                        if (positionGuide) positionGuide.style.display = 'none';
                        
                        console.log('Marker is now visible');
                    } else {
                        this.trackingStatusElement.style.display = 'flex';
                        this.trackingStatusElement.classList.remove('found');
                        this.trackingStatusElement.querySelector('.status-text').textContent = 'Looking for marker...';
                        
                        console.log('Marker is now hidden');
                    }
                }
            }
        }
        
        onResize() {
            if (!this.arToolkitSource) return;
            
            // Update AR source
            this.arToolkitSource.onResizeElement();
            this.arToolkitSource.copyElementSizeTo(this.renderer.domElement);
            
            if (this.arToolkitContext && this.arToolkitContext.arController !== null) {
                this.arToolkitSource.copyElementSizeTo(this.arToolkitContext.arController.canvas);
            }
        }
        
        bindUIControls() {
            // Find control buttons
            const exitArBtn = document.getElementById('exit-ar');
            const captureArBtn = document.getElementById('capture-ar');
            const sizeSmallerBtn = document.getElementById('size-smaller');
            const sizeLargerBtn = document.getElementById('size-larger');
            
            // Exit AR
            if (exitArBtn) {
                exitArBtn.addEventListener('click', () => {
                    // Stop camera stream before navigating away
                    if (this.arToolkitSource && this.arToolkitSource.domElement && this.arToolkitSource.domElement.srcObject) {
                        this.arToolkitSource.domElement.srcObject.getTracks().forEach(track => track.stop());
                    }
                    window.history.back();
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
            
            // Handle marker info dismissal
            const hideMarkerInfoBtn = document.getElementById('hide-marker-info');
            if (hideMarkerInfoBtn) {
                hideMarkerInfoBtn.addEventListener('click', () => {
                    const markerInfo = document.getElementById('marker-info');
                    if (markerInfo) markerInfo.style.display = 'none';
                });
            }
        }
        
        resizeModel(larger) {
            if (!this.watchModel) return;
            
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
            // Only capture if AR is running
            if (!this.renderer || !this.isMarkerVisible) {
                alert('Position the marker properly before taking a photo.');
                return;
            }
            
            try {
                // Capture the canvas
                const dataURL = this.renderer.domElement.toDataURL('image/png');
                
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
    };
    
    console.log('AR controller module loaded successfully');
})();