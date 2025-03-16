/**
 * Wrist Detection Module for AR Watch Try-On
 * Uses TensorFlow.js and Handpose model to detect wrist position
 */

class WristTracker {
    constructor(container) {
        if (!container) {
            throw new Error('Container element is required');
        }
        
        this.container = container;
        this.handposeModel = null;
        this.video = null;
        this.scene = null;
        this.camera = null;
        this.renderer = null;
        this.watchModel = null;
        this.isTracking = false;
        this.lastWristPosition = null;
        this.onWristDetected = null;
        this.onWristLost = null;
        this.onVideoReady = null;
        this.onHandDetected = null;
        
        // Error tracking
        this.consecutiveErrors = 0;
        this.maxConsecutiveErrors = 60; // Increased tolerance for errors
        this.handDetected = false;
        this.wristDetectionAttempts = 0;
        this.maxWristDetectionAttempts = 120; // Allow more attempts before giving up
        
        // Debug mode
        this.debugMode = false;
        this.debugCanvas = null;
        this.debugCtx = null;
        
        // Bind methods
        this.animate = this.animate.bind(this);
        this.detectHands = this.detectHands.bind(this);
        this.onWindowResize = this.onWindowResize.bind(this);
        this.toggleDebugMode = this.toggleDebugMode.bind(this);
    }
    
    async initialize(options = {}) {
        const {
            modelUrl,
            onWristDetected,
            onWristLost,
            onVideoReady,
            onHandDetected,
            debug = false
        } = options || {};
        
        this.onWristDetected = onWristDetected;
        this.onWristLost = onWristLost;
        this.onVideoReady = onVideoReady;
        this.onHandDetected = onHandDetected;
        this.debugMode = debug;
        
        try {
            // Check if required libraries are available
            if (!window.handpose) {
                throw new Error('Handpose library not available');
            }
            
            if (!window.THREE) {
                throw new Error('THREE.js not available');
            }
            
            // Setup video first
            await this.setupVideo();
            
            // Setup debug overlay if in debug mode
            if (this.debugMode) {
                this.setupDebugOverlay();
            }
            
            // Load handpose model
            console.log('Loading handpose model...');
            this.handposeModel = await handpose.load();
            console.log('Handpose model loaded');
            
            // Setup THREE.js scene
            this.setupScene();
            
            // Load watch model if URL provided
            if (modelUrl) {
                await this.loadWatchModel(modelUrl);
            }
            
            // Start tracking
            this.isTracking = true;
            this.animate();
            
            return true;
        } catch (error) {
            console.error('Error initializing wrist tracker:', error);
            throw error;
        }
    }
    
    setupDebugOverlay() {
        // Create debug canvas
        this.debugCanvas = document.createElement('canvas');
        this.debugCanvas.style.position = 'absolute';
        this.debugCanvas.style.top = '10px';
        this.debugCanvas.style.right = '10px';
        this.debugCanvas.style.width = '160px';
        this.debugCanvas.style.height = '120px';
        this.debugCanvas.style.border = '2px solid white';
        this.debugCanvas.style.borderRadius = '5px';
        this.debugCanvas.style.zIndex = '1000';
        this.debugCanvas.style.opacity = '0.8';
        this.debugCanvas.width = 160;
        this.debugCanvas.height = 120;
        
        // Add toggle button
        const toggleBtn = document.createElement('button');
        toggleBtn.textContent = 'Debug';
        toggleBtn.style.position = 'absolute';
        toggleBtn.style.top = '135px';
        toggleBtn.style.right = '10px';
        toggleBtn.style.padding = '5px 10px';
        toggleBtn.style.background = '#6c5ce7';
        toggleBtn.style.color = 'white';
        toggleBtn.style.border = 'none';
        toggleBtn.style.borderRadius = '5px';
        toggleBtn.style.zIndex = '1000';
        toggleBtn.style.cursor = 'pointer';
        toggleBtn.style.fontSize = '12px';
        
        toggleBtn.addEventListener('click', this.toggleDebugMode);
        
        // Add to container
        this.container.appendChild(this.debugCanvas);
        this.container.appendChild(toggleBtn);
        
        // Get context
        this.debugCtx = this.debugCanvas.getContext('2d');
        
        // Initially hide debug canvas
        this.debugCanvas.style.display = 'none';
        toggleBtn.style.display = 'none';
        
        // Show after 5 seconds if still in debug mode
        setTimeout(() => {
            if (this.debugMode) {
                toggleBtn.style.display = 'block';
            }
        }, 5000);
    }
    
    toggleDebugMode() {
        if (this.debugCanvas) {
            if (this.debugCanvas.style.display === 'none') {
                this.debugCanvas.style.display = 'block';
            } else {
                this.debugCanvas.style.display = 'none';
            }
        }
    }
    
    setupScene() {
        // Create scene
        this.scene = new THREE.Scene();
        
        // Setup camera with adjusted parameters
        const width = this.container.clientWidth;
        const height = this.container.clientHeight;
        this.camera = new THREE.PerspectiveCamera(
            60, // Increased FOV from 75 to 60 for less distortion
            width / height,
            0.1,
            1000
        );
        this.camera.position.z = 4; // Moved camera closer (from 5 to 4)
        this.camera.position.y = 0.5; // Slight upward offset
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
        
        // Setup renderer with improved settings
        try {
            this.renderer = new THREE.WebGLRenderer({ 
                antialias: true,
                alpha: true,
                canvas: canvas,
                preserveDrawingBuffer: true // Enable screenshot capability
            });
            this.renderer.setSize(width, height);
            this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2)); // Limit pixel ratio for better performance
        } catch (error) {
            console.error('Error creating WebGL renderer:', error);
            throw new Error('Error creating WebGL context: ' + error.message);
        }
        
        // Enhanced lighting setup
        const ambientLight = new THREE.AmbientLight(0xffffff, 0.7); // Increased intensity
        this.scene.add(ambientLight);
        
        const directionalLight = new THREE.DirectionalLight(0xffffff, 1.0); // Increased intensity
        directionalLight.position.set(0, 1, 1);
        this.scene.add(directionalLight);
        
        // Add fill light from below
        const fillLight = new THREE.DirectionalLight(0xffffff, 0.3);
        fillLight.position.set(0, -1, 1);
        this.scene.add(fillLight);
        
        // Handle window resize
        window.addEventListener('resize', this.onWindowResize);
    }
    
    async loadWatchModel(modelUrl) {
        if (!this.scene) {
            throw new Error('Scene not initialized');
        }
        
        return new Promise((resolve, reject) => {
            try {
                // Check if GLTFLoader is available
                if (!window.GLTFLoader) {
                    console.error('GLTFLoader not available');
                    reject(new Error('GLTFLoader not available'));
                    return;
                }
                
                const loader = new window.GLTFLoader();
                
                loader.load(
                    modelUrl,
                    (gltf) => {
                        this.watchModel = gltf.scene;
                        
                        // Increase initial scale for better visibility on mobile
                        const scale = 2.0; // Increased from 0.5 to 2.0
                        this.watchModel.scale.set(scale, scale, scale);
                        
                        // Hide model initially
                        this.watchModel.visible = false;
                        
                        this.scene.add(this.watchModel);
                        resolve();
                    },
                    (progress) => {
                        console.log('Loading model:', (progress.loaded / progress.total * 100) + '%');
                    },
                    (error) => {
                        console.error('Error loading watch model:', error);
                        reject(error);
                    }
                );
            } catch (error) {
                console.error('Error setting up model loader:', error);
                reject(error);
            }
        });
    }
    
    async setupVideo() {
        try {
            // Create video element
            this.video = document.createElement('video');
            this.video.style.display = 'none';
            this.video.autoplay = true;
            this.video.playsInline = true;
            document.body.appendChild(this.video);
            
            // Get camera stream
            const stream = await navigator.mediaDevices.getUserMedia({
                video: {
                    facingMode: 'environment',
                    width: { ideal: 1280 },
                    height: { ideal: 720 }
                }
            });
            
            this.video.srcObject = stream;
            
            // Wait for video to be ready
            await new Promise((resolve, reject) => {
                this.video.onloadedmetadata = () => {
                    this.video.play().then(() => {
                        // Notify that video is ready
                        if (this.onVideoReady) {
                            this.onVideoReady(this.video);
                        }
                        resolve();
                    }).catch(reject);
                };
                this.video.onerror = () => reject(new Error('Failed to load video'));
            });
            
            // Log video dimensions for debugging
            console.log(`Video dimensions: ${this.video.videoWidth}x${this.video.videoHeight}`);
            
        } catch (error) {
            console.error('Error setting up video:', error);
            throw new Error('Failed to setup video: ' + error.message);
        }
    }
    
    // Helper function to estimate wrist position from other hand landmarks
    estimateWristPosition(hand) {
        try {
            // If we have palm and index finger base, we can estimate wrist position
            if (hand.annotations.palmBase && hand.annotations.palmBase[0] && 
                hand.annotations.indexFinger && hand.annotations.indexFinger[0]) {
                
                const palm = hand.annotations.palmBase[0];
                const indexBase = hand.annotations.indexFinger[0];
                
                // Wrist is typically in the opposite direction from index finger relative to palm
                const vectorX = palm[0] - indexBase[0];
                const vectorY = palm[1] - indexBase[1];
                const vectorZ = palm[2] - indexBase[2];
                
                // Normalize and scale
                const length = Math.sqrt(vectorX * vectorX + vectorY * vectorY + vectorZ * vectorZ);
                const scale = 0.7; // Adjust this value based on testing
                
                // Estimated wrist position
                const wristX = palm[0] + (vectorX / length) * scale;
                const wristY = palm[1] + (vectorY / length) * scale;
                const wristZ = palm[2] + (vectorZ / length) * scale;
                
                if (this.debugMode) {
                    console.log('Estimated wrist position:', [wristX, wristY, wristZ]);
                }
                
                return [wristX, wristY, wristZ];
            }
            
            return null;
        } catch (error) {
            console.warn('Error estimating wrist position:', error);
            return null;
        }
    }
    
    // Draw hand landmarks on debug canvas
    drawDebugInfo(hand) {
        if (!this.debugCtx || !this.debugCanvas || !hand || this.debugCanvas.style.display === 'none') return;
        
        const ctx = this.debugCtx;
        const canvas = this.debugCanvas;
        const videoWidth = this.video.videoWidth || this.video.width;
        const videoHeight = this.video.videoHeight || this.video.height;
        
        // Clear canvas
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        
        // Draw video frame
        ctx.drawImage(
            this.video, 
            0, 0, videoWidth, videoHeight, 
            0, 0, canvas.width, canvas.height
        );
        
        // Scale factor for drawing on the small canvas
        const scaleX = canvas.width / videoWidth;
        const scaleY = canvas.height / videoHeight;
        
        // Draw hand landmarks
        if (hand.landmarks) {
            // Draw all landmarks
            hand.landmarks.forEach(landmark => {
                ctx.beginPath();
                ctx.arc(landmark[0] * scaleX, landmark[1] * scaleY, 2, 0, 2 * Math.PI);
                ctx.fillStyle = 'aqua';
                ctx.fill();
            });
            
            // Draw wrist point if available
            if (hand.annotations && hand.annotations.wrist && hand.annotations.wrist[0]) {
                const wrist = hand.annotations.wrist[0];
                ctx.beginPath();
                ctx.arc(wrist[0] * scaleX, wrist[1] * scaleY, 4, 0, 2 * Math.PI);
                ctx.fillStyle = 'red';
                ctx.fill();
                
                // Draw text
                ctx.fillStyle = 'white';
                ctx.font = '10px Arial';
                ctx.fillText('Wrist', wrist[0] * scaleX + 5, wrist[1] * scaleY);
            }
            
            // Draw palm base
            if (hand.annotations && hand.annotations.palmBase && hand.annotations.palmBase[0]) {
                const palm = hand.annotations.palmBase[0];
                ctx.beginPath();
                ctx.arc(palm[0] * scaleX, palm[1] * scaleY, 4, 0, 2 * Math.PI);
                ctx.fillStyle = 'yellow';
                ctx.fill();
                
                // Draw text
                ctx.fillStyle = 'white';
                ctx.font = '10px Arial';
                ctx.fillText('Palm', palm[0] * scaleX + 5, palm[1] * scaleY);
            }
        }
        
        // Draw status text
        ctx.fillStyle = 'white';
        ctx.font = '10px Arial';
        ctx.fillText(`Hand: ${this.handDetected ? 'Detected' : 'Not detected'}`, 5, 12);
        ctx.fillText(`Wrist: ${this.lastWristPosition ? 'Tracked' : 'Not tracked'}`, 5, 24);
        ctx.fillText(`Errors: ${this.consecutiveErrors}/${this.maxConsecutiveErrors}`, 5, 36);
    }
    
    async detectHands() {
        if (!this.isTracking || !this.handposeModel || !this.video) return;
        
        try {
            // Detect hands in the video
            const hands = await this.handposeModel.estimateHands(this.video);
            
            if (hands && hands.length > 0) {
                const hand = hands[0];
                
                // Hand is detected
                const wasHandDetected = this.handDetected;
                this.handDetected = true;
                
                // Notify about hand detection if state changed
                if (!wasHandDetected && this.onHandDetected) {
                    this.onHandDetected(true);
                }
                
                // Update debug visualization
                if (this.debugMode) {
                    this.drawDebugInfo(hand);
                }
                
                // Get wrist position - first try the standard way
                let wrist = null;
                if (hand.annotations && hand.annotations.wrist && hand.annotations.wrist[0]) {
                    wrist = hand.annotations.wrist[0];
                    this.wristDetectionAttempts = 0; // Reset attempts counter on success
                } else {
                    // If wrist not available, try to estimate it
                    wrist = this.estimateWristPosition(hand);
                    
                    if (!wrist) {
                        this.wristDetectionAttempts++;
                        
                        if (this.wristDetectionAttempts % 10 === 0) {
                            console.warn(`Hand detected but wrist position not available (attempt ${this.wristDetectionAttempts}/${this.maxWristDetectionAttempts})`);
                        }
                        
                        // If we've tried too many times without success, consider it an error
                        if (this.wristDetectionAttempts > this.maxWristDetectionAttempts) {
                            this.consecutiveErrors++;
                            
                            if (this.consecutiveErrors > this.maxConsecutiveErrors) {
                                console.error('Too many consecutive wrist detection errors, stopping tracking');
                                this.isTracking = false;
                                
                                if (this.onWristLost) {
                                    this.onWristLost('tracking_failed');
                                }
                            }
                        }
                        
                        // Keep the model hidden but don't increment error counter yet
                        if (this.watchModel) {
                            this.watchModel.visible = false;
                        }
                        
                        return;
                    }
                }
                
                // Reset error counter on successful detection
                this.consecutiveErrors = 0;
                
                // Convert to normalized coordinates with adjusted scaling
                const videoWidth = this.video.videoWidth || this.video.width;
                const videoHeight = this.video.videoHeight || this.video.height;
                
                // Adjust position scaling factors for better visibility
                const wristX = ((wrist[0] / videoWidth) * 2 - 1) * 1.5;  // Reduced from 2 to 1.5
                const wristY = -((wrist[1] / videoHeight) * 2 - 1) * 1.2; // Reduced from 1.5 to 1.2
                const wristZ = -wrist[2] / 300; // Adjusted from 200 to 300 for better depth
                
                // Update watch model position
                if (this.watchModel) {
                    this.watchModel.position.set(wristX, wristY, wristZ);
                    this.watchModel.visible = true;
                    
                    // Check if palmBase and middleFinger data exist
                    if (hand.annotations.palmBase && hand.annotations.palmBase[0] && 
                        hand.annotations.middleFinger && hand.annotations.middleFinger[0]) {
                        
                        // Adjust rotation based on hand orientation
                        const palmBase = hand.annotations.palmBase[0];
                        const middleFinger = hand.annotations.middleFinger[0];
                        
                        const angle = Math.atan2(
                            middleFinger[1] - palmBase[1],
                            middleFinger[0] - palmBase[0]
                        );
                        
                        // Add a slight tilt for better visibility
                        this.watchModel.rotation.z = angle;
                        this.watchModel.rotation.x = Math.PI * 0.1; // Add slight tilt
                    }
                }
                
                // Store position
                this.lastWristPosition = { x: wristX, y: wristY, z: wristZ };
                
                // Call callback
                if (this.onWristDetected) {
                    this.onWristDetected(this.lastWristPosition);
                }
            } else {
                // No hands detected
                const wasHandDetected = this.handDetected;
                this.handDetected = false;
                this.wristDetectionAttempts = 0; // Reset attempts when no hand is detected
                
                // Notify about hand detection state change
                if (wasHandDetected && this.onHandDetected) {
                    this.onHandDetected(false);
                }
                
                // Update debug visualization with empty hand
                if (this.debugMode && this.debugCtx && this.debugCanvas) {
                    const ctx = this.debugCtx;
                    const canvas = this.debugCanvas;
                    
                    // Clear canvas
                    ctx.clearRect(0, 0, canvas.width, canvas.height);
                    
                    // Draw video frame
                    ctx.drawImage(
                        this.video, 
                        0, 0, this.video.videoWidth || this.video.width, this.video.videoHeight || this.video.height, 
                        0, 0, canvas.width, canvas.height
                    );
                    
                    // Draw status text
                    ctx.fillStyle = 'white';
                    ctx.font = '10px Arial';
                    ctx.fillText('Hand: Not detected', 5, 12);
                    ctx.fillText('Wrist: Not tracked', 5, 24);
                    ctx.fillText(`Errors: ${this.consecutiveErrors}/${this.maxConsecutiveErrors}`, 5, 36);
                }
                
                // Increment error counter when no hands detected
                this.consecutiveErrors++;
                
                // If too many consecutive errors, stop tracking
                if (this.consecutiveErrors > this.maxConsecutiveErrors) {
                    console.error('Too many consecutive frames without hand detection, stopping tracking');
                    this.isTracking = false;
                    
                    // Call callback with null to indicate tracking failure
                    if (this.onWristLost) {
                        this.onWristLost('tracking_failed');
                    }
                    
                    return;
                }
                
                // Hide watch model if no hand detected
                if (this.watchModel) {
                    this.watchModel.visible = false;
                }
                
                // Clear position
                if (this.lastWristPosition) {
                    this.lastWristPosition = null;
                    
                    // Call callback
                    if (this.onWristLost) {
                        this.onWristLost();
                    }
                }
            }
        } catch (error) {
            console.error('Error detecting hands:', error);
            
            // Increment error counter
            this.consecutiveErrors++;
            
            // If too many consecutive errors, stop tracking
            if (this.consecutiveErrors > this.maxConsecutiveErrors) {
                console.error('Too many consecutive detection errors, stopping tracking');
                this.isTracking = false;
                
                // Call callback with null to indicate tracking failure
            if (this.onWristLost) {
                    this.onWristLost('tracking_failed');
                }
            }
        }
    }
    
    animate() {
        if (!this.isTracking) return;
        
        requestAnimationFrame(this.animate);
        
        // Detect hands
        this.detectHands();
        
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
            this.isTracking = false;
            
            // Stop video stream
            if (this.video && this.video.srcObject) {
                try {
                    const tracks = this.video.srcObject.getTracks();
                    tracks.forEach(track => track.stop());
                    this.video.srcObject = null;
                } catch (error) {
                    console.warn('Error stopping video tracks:', error);
                }
            }
            
            // Remove video element
            if (this.video && this.video.parentNode) {
                try {
                    this.video.parentNode.removeChild(this.video);
                } catch (error) {
                    console.warn('Error removing video element:', error);
                }
                this.video = null;
            }
            
            // Remove debug elements
            if (this.debugCanvas && this.debugCanvas.parentNode) {
                try {
                    this.debugCanvas.parentNode.removeChild(this.debugCanvas);
                } catch (error) {
                    console.warn('Error removing debug canvas:', error);
                }
                this.debugCanvas = null;
                this.debugCtx = null;
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
            
            // Clear references
            this.camera = null;
            this.watchModel = null;
            this.lastWristPosition = null;
            
            try {
                window.removeEventListener('resize', this.onWindowResize);
            } catch (error) {
                console.warn('Error removing event listener:', error);
            }
            
            console.log('WristTracker resources disposed');
        } catch (error) {
            console.error('Error in WristTracker.dispose():', error);
        }
    }
}

// Initialize wrist tracking
window.initWristTracking = async function(options = {}) {
    try {
        const container = options.container;
        if (!container) {
            throw new Error('Container element is required');
        }
        
        const tracker = new WristTracker(container);
        const success = await tracker.initialize({
            ...options,
            debug: true // Enable debug mode for troubleshooting
        });
        return success ? tracker : null;
    } catch (error) {
        console.error('Failed to initialize wrist tracking:', error);
        return null;
    }
};