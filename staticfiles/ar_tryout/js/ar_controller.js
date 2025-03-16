// AR Experience Controller
async function initARExperience(watchData) {
    const arCanvas = document.getElementById('ar-canvas');
    const arOverlay = document.getElementById('ar-overlay');
    const arNotSupported = document.getElementById('ar-not-supported');
    const arLoading = document.getElementById('ar-loading');
    const exitArButton = document.getElementById('exit-ar');
    const captureButton = document.getElementById('capture-ar');
    const captureSuccess = document.getElementById('capture-success');
    const continueArButton = document.getElementById('continue-ar');
    const sizeLargerButton = document.getElementById('size-larger');
    const sizeSmallerButton = document.getElementById('size-smaller');
    const shareButton = document.getElementById('share-capture');
    const downloadButton = document.getElementById('download-capture');

    // Check for WebXR Support
    if (!navigator.xr || !navigator.xr.isSessionSupported) {
        showARNotSupported();
        return;
    }

    // Check if AR is supported
    try {
        const isSupported = await navigator.xr.isSessionSupported('immersive-ar');
        if (!isSupported) {
            showARNotSupported();
            return;
        }
    } catch (error) {
        console.error('Error checking AR support:', error);
        showARNotSupported();
        return;
    }

    arLoading.style.display = 'flex';

    // Set up Three.js
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
    const renderer = new THREE.WebGLRenderer({
        canvas: arCanvas,
        alpha: true,
        antialias: true
    });

    // Variables to store session and watch model
    let xrSession = null;
    let xrRefSpace = null;
    let watchModel = null;
    let handPoseModel = null;
    let watchScale = 0.01;  // Initial scale factor for the watch

    // Initialize pose detection
    async function initHandPoseDetection() {
        try {
            handPoseModel = await handpose.load();
            return true;
        } catch (error) {
            console.error('Error loading handpose model:', error);
            return false;
        }
    }

    // Initialize lighting
    function setupLighting() {
        // Add lights
        const ambientLight = new THREE.AmbientLight(0xffffff, 0.5);
        scene.add(ambientLight);

        const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
        directionalLight.position.set(0, 10, 5);
        scene.add(directionalLight);
    }

    // Load the watch model
    async function loadWatchModel() {
        return new Promise((resolve, reject) => {
            const loader = new THREE.GLTFLoader();
            loader.load(
                watchData.modelUrl,
                function(gltf) {
                    watchModel = gltf.scene;
                    watchModel.scale.set(watchScale, watchScale, watchScale);
                    
                    // Apply materials if we have custom materials data
                    if (watchData.materials) {
                        applyMaterials(watchModel, watchData.materials);
                    }
                    
                    scene.add(watchModel);
                    watchModel.visible = false; // Hide until we detect a wrist
                    resolve(watchModel);
                },
                undefined,
                function(error) {
                    console.error('Error loading model:', error);
                    reject(error);
                }
            );
        });
    }

    function applyMaterials(model, materials) {
        // Apply custom materials to the model parts
        // This should match your watch customizer logic
        Object.entries(materials).forEach(([partName, materialData]) => {
            model.traverse((node) => {
                if (node.isMesh && node.name === partName) {
                    // Apply texture or material properties
                    if (materialData.textureUrl) {
                        const texture = new THREE.TextureLoader().load(materialData.textureUrl);
                        node.material.map = texture;
                    }
                    
                    if (materialData.color) {
                        node.material.color.set(materialData.color);
                    }
                    
                    node.material.needsUpdate = true;
                }
            });
        });
    }

    // Start AR Session
    async function startARSession() {
        try {
            xrSession = await navigator.xr.requestSession('immersive-ar', {
                requiredFeatures: ['hit-test'],
                optionalFeatures: ['dom-overlay'],
                domOverlay: { root: arOverlay }
            });
            
            // Set up WebXR rendering
            renderer.xr.enabled = true;
            renderer.xr.setReferenceSpaceType('local');
            renderer.xr.setSession(xrSession);
            
            xrSession.addEventListener('end', onSessionEnd);
            
            // Get reference space for hit testing
            xrRefSpace = await xrSession.requestReferenceSpace('local');
            
            // Start rendering loop
            renderer.setAnimationLoop(onXRFrame);
            
            // Hide loading screen
            arLoading.style.display = 'none';
            
        } catch (error) {
            console.error('Error starting AR session:', error);
            showARNotSupported();
        }
    }

    function onXRFrame(timestamp, frame) {
        if (!xrSession || !frame) return;
        
        const pose = frame.getViewerPose(xrRefSpace);
        if (pose) {
            // Update camera from AR pose
            const view = pose.views[0];
            const viewport = xrSession.renderState.baseLayer.getViewport(view);
            renderer.setSize(viewport.width, viewport.height);
            
            camera.matrix.fromArray(view.transform.matrix);
            camera.matrix.decompose(camera.position, camera.quaternion, camera.scale);
            
            // If wrist is detected, position watch
            if (wristPosition && watchModel) {
                watchModel.visible = true;
                watchModel.position.copy(wristPosition);
                watchModel.rotation.set(0, 0, 0); // Adjust based on wrist orientation
            }
            
            // Render scene
            renderer.render(scene, camera);
        }
    }

    // Handle exiting AR
    function onSessionEnd() {
        xrSession = null;
        renderer.setAnimationLoop(null);
        window.location.href = `/product/${watchData.slug}/`;
    }
    
    // Show AR not supported message
    function showARNotSupported() {
        arLoading.style.display = 'none';
        arNotSupported.style.display = 'flex';
    }

    // Capture AR view to image
    function captureARView() {
        if (!xrSession) return;
        
        // Create a data URL from the canvas
        const capturedImage = renderer.domElement.toDataURL('image/png');
        
        // Show success message
        captureSuccess.style.display = 'flex';
        
        // Store image data for sharing/downloading
        captureSuccess.dataset.imageData = capturedImage;
        
        // Pause AR session (optional)
        // xrSession.requestAnimationFrame(() => {}); // This pauses rendering loop
    }

    // Adjust watch size
    function adjustWatchSize(larger) {
        if (!watchModel) return;
        
        if (larger) {
            watchScale *= 1.1;
        } else {
            watchScale *= 0.9;
        }
        
        watchModel.scale.set(watchScale, watchScale, watchScale);
    }

    // Share captured image
    async function shareImage() {
        const imageData = captureSuccess.dataset.imageData;
        
        if (!imageData) return;
        
        if (navigator.share) {
            // Convert data URL to file
            const blob = await (await fetch(imageData)).blob();
            const file = new File([blob], "timecraft-ar-try-on.png", { type: "image/png" });
            
            try {
                await navigator.share({
                    title: `${watchData.name} - TimeCraft AR Try-On`,
                    text: 'Check out how this watch looks on my wrist with TimeCraft AR!',
                    files: [file]
                });
            } catch (error) {
                console.error('Error sharing:', error);
                downloadImage(); // Fallback to download if sharing fails
            }
        } else {
            downloadImage(); // Fallback for browsers that don't support sharing
        }
    }

    // Download captured image
    function downloadImage() {
        const imageData = captureSuccess.dataset.imageData;
        
        if (!imageData) return;
        
        const link = document.createElement('a');
        link.href = imageData;
        link.download = `timecraft-${watchData.slug}-ar-try-on.png`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }

    // Event Listeners
    exitArButton.addEventListener('click', () => {
        if (xrSession) {
            xrSession.end();
        }
    });
    
    captureButton.addEventListener('click', captureARView);
    
    continueArButton.addEventListener('click', () => {
        captureSuccess.style.display = 'none';
    });
    
    sizeLargerButton.addEventListener('click', () => adjustWatchSize(true));
    sizeSmallerButton.addEventListener('click', () => adjustWatchSize(false));
    
    shareButton.addEventListener('click', shareImage);
    downloadButton.addEventListener('click', downloadImage);

    // Initialize AR experience
    try {
        // Initialize everything in sequence
        await initHandPoseDetection();
        setupLighting();
        await loadWatchModel();
        startARSession();
    } catch (error) {
        console.error('Error initializing AR:', error);
        showARNotSupported();
    }
}