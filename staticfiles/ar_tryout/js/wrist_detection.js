// Global variable to store current wrist position
let wristPosition = null;

// Wrist tracking module using TensorFlow.js HandPose
class WristTracker {
    constructor() {
        this.handposeModel = null;
        this.video = null;
        this.lastDetectedWrist = null;
        this.isTracking = false;
    }
    
    async initialize() {
        try {
            // Load the handpose model
            this.handposeModel = await handpose.load();
            
            // Create video element for camera feed
            this.video = document.createElement('video');
            this.video.style.display = 'none';
            this.video.autoplay = true;
            this.video.playsInline = true;
            document.body.appendChild(this.video);
            
            // Get camera feed
            const stream = await navigator.mediaDevices.getUserMedia({
                video: {
                    facingMode: 'environment',
                    width: { ideal: 1280 },
                    height: { ideal: 720 }
                }
            });
            
            this.video.srcObject = stream;
            
            // Wait for video to be ready
            await new Promise(resolve => {
                this.video.onloadedmetadata = () => {
                    this.video.play();
                    resolve();
                };
            });
            
            return true;
        } catch (error) {
            console.error('Error initializing wrist tracker:', error);
            return false;
        }
    }
    
    async startTracking() {
        if (!this.handposeModel || !this.video || this.isTracking) return;
        
        this.isTracking = true;
        this.trackWrist();
    }
    
    async trackWrist() {
        if (!this.isTracking) return;
        
        try {
            // Detect hands in the video feed
            const hands = await this.handposeModel.estimateHands(this.video);
            
            if (hands.length > 0) {
                // Get wrist position from the first detected hand
                const wristLandmark = hands[0].landmarks[0]; // Index 0 is the wrist in handpose model
                
                // Convert to normalized coordinates for Three.js
                const wristX = ((wristLandmark[0] / this.video.width) - 0.5) * 2;
                const wristY = -((wristLandmark[1] / this.video.height) - 0.5) * 2;
                const wristZ = -wristLandmark[2] / 100; // Scale Z coordinate
                
                // Update global wrist position
                wristPosition = new THREE.Vector3(wristX, wristY, wristZ);
                
                // Store timestamp of detection
                this.lastDetectedWrist = Date.now();
            } else if (this.lastDetectedWrist && Date.now() - this.lastDetectedWrist > 1000) {
                // If no hand detected for more than 1 second, clear wrist position
                wristPosition = null;
                this.lastDetectedWrist = null;
            }
        } catch (error) {
            console.error('Error tracking wrist:', error);
        }
        
        // Continue tracking in animation frame
        requestAnimationFrame(() => this.trackWrist());
    }
    
    stopTracking() {
        this.isTracking = false;
        
        // Clean up video stream
        if (this.video && this.video.srcObject) {
            const tracks = this.video.srcObject.getTracks();
            tracks.forEach(track => track.stop());
            this.video.srcObject = null;
        }
        
        // Remove video element
        if (this.video && this.video.parentNode) {
            this.video.parentNode.removeChild(this.video);
        }
        
        this.video = null;
        wristPosition = null;
    }
}

// Initialize wrist tracker when AR experience starts
async function initializeWristTracking() {
    const tracker = new WristTracker();
    const initialized = await tracker.initialize();
    
    if (initialized) {
        tracker.startTracking();
        
        // Return the tracker object so it can be stopped later
        return tracker;
    }
    
    return null;
}