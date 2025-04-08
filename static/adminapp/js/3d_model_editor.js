/**
 * 3D Model Editor
 * A custom tool for editing 3D watch models directly in the browser
 */

class ModelEditor {
    constructor(modelUrl, watchId) {
        // Editor properties
        this.modelUrl = modelUrl;
        this.watchId = watchId;
        this.container = document.getElementById('editor-canvas');
        
        // Three.js components
        this.scene = null;
        this.camera = null;
        this.renderer = null;
        this.orbitControls = null;
        this.transformControls = null;
        
        // Editor state
        this.model = null;
        this.selectedObject = null;
        this.isWireframe = false;
        this.editHistory = [];
        this.grid = null;
        this.axes = null;
        
        // Bind methods to maintain 'this' context
        this.onWindowResize = this.onWindowResize.bind(this);
        this.animate = this.animate.bind(this);
        this.onObjectSelected = this.onObjectSelected.bind(this);
        this.handleTransformChange = this.handleTransformChange.bind(this);
    }
    
    /**
     * Initialize the editor
     */
    initialize() {
        // Create scene
        this.scene = new THREE.Scene();
        this.scene.background = new THREE.Color(0xf0f0f0);
        
        // Create renderer
        this.renderer = new THREE.WebGLRenderer({ antialias: true });
        this.renderer.setPixelRatio(window.devicePixelRatio);
        this.renderer.setSize(this.container.clientWidth, this.container.clientHeight);
        this.renderer.shadowMap.enabled = true;
        this.container.appendChild(this.renderer.domElement);
        
        // Create camera
        this.camera = new THREE.PerspectiveCamera(
            60,
            this.container.clientWidth / this.container.clientHeight,
            0.1,
            1000
        );
        this.camera.position.set(5, 5, 5);
        this.camera.lookAt(0, 0, 0);
        
        // Add lights
        this.addLights();
        
        // Create controls
        this.setupControls();
        
        // Add grid and axes
        this.setupHelpers();
        
        // Load the model
        this.loadModel();
        
        // Set up event listeners
        this.setupEventListeners();
        
        // Start rendering loop
        this.animate();
    }
    
    /**
     * Setup visualization helpers (grid, axes)
     */
    setupHelpers() {
        // Add grid
        this.grid = new THREE.GridHelper(10, 10, 0x888888, 0x444444);
        this.grid.material.opacity = 0.5;
        this.grid.material.transparent = true;
        this.scene.add(this.grid);
        
        // Add axes
        this.axes = new THREE.AxesHelper(5);
        this.scene.add(this.axes);
    }
    
    /**
     * Add lights to the scene
     */
    addLights() {
        // Ambient light
        const ambientLight = new THREE.AmbientLight(0xffffff, 0.5);
        this.scene.add(ambientLight);
        
        // Directional lights for better visibility
        const light1 = new THREE.DirectionalLight(0xffffff, 0.8);
        light1.position.set(1, 1, 1).normalize();
        light1.castShadow = true;
        this.scene.add(light1);
        
        const light2 = new THREE.DirectionalLight(0xffffff, 0.5);
        light2.position.set(-1, 0.5, -1).normalize();
        this.scene.add(light2);
    }
    
    /**
     * Set up editor controls
     */
    setupControls() {
        // Orbit controls for camera navigation
        this.orbitControls = new THREE.OrbitControls(this.camera, this.renderer.domElement);
        this.orbitControls.enableDamping = true;
        this.orbitControls.dampingFactor = 0.1;
        
        // Transform controls for object manipulation
        this.transformControls = new THREE.TransformControls(this.camera, this.renderer.domElement);
        this.transformControls.addEventListener('dragging-changed', (event) => {
            // Disable orbit controls when using transform controls
            this.orbitControls.enabled = !event.value;
        });
        this.transformControls.addEventListener('objectChange', this.handleTransformChange);
        this.scene.add(this.transformControls);
    }
    
    /**
     * Load the 3D model
     */
    loadModel() {
        const loader = new THREE.GLTFLoader();
        
        loader.load(
            this.modelUrl,
            (gltf) => {
                // Success callback
                this.model = gltf.scene;
                
                // Enable shadows
                this.model.traverse((object) => {
                    if (object.isMesh) {
                        object.castShadow = true;
                        object.receiveShadow = true;
                        
                        // Store original material
                        object.userData.originalMaterial = object.material.clone();
                        
                        // Make objects clickable
                        object.userData.selectable = true;
                    }
                });
                
                // Center the model
                const box = new THREE.Box3().setFromObject(this.model);
                const center = box.getCenter(new THREE.Vector3());
                this.model.position.sub(center);
                
                // Scale model to fit view
                const size = box.getSize(new THREE.Vector3());
                const maxDim = Math.max(size.x, size.y, size.z);
                const scale = 4 / maxDim;
                this.model.scale.set(scale, scale, scale);
                
                // Add to scene
                this.scene.add(this.model);
                
                // Hide loading indicator
                document.getElementById('loading-indicator').style.display = 'none';
                
                // Build model structure
                this.buildModelStructure();
            },
            (xhr) => {
                // Progress callback
                const percent = (xhr.loaded / xhr.total) * 100;
                console.log(`Loading model: ${Math.round(percent)}%`);
            },
            (error) => {
                // Error callback
                console.error('Error loading model:', error);
                document.getElementById('loading-indicator').innerHTML = `
                    <div class="alert alert-danger">
                        <i class="fas fa-exclamation-triangle me-2"></i>
                        Failed to load model
                    </div>
                `;
            }
        );
    }
    
    /**
     * Set up event listeners
     */
    setupEventListeners() {
        // Handle window resize
        window.addEventListener('resize', this.onWindowResize);
        
        // Handle clicks on the canvas for object selection
        this.renderer.domElement.addEventListener('click', (event) => {
            // Don't handle clicks when using transform controls
            if (this.transformControls.dragging) return;
            
            // Get mouse position
            const rect = this.renderer.domElement.getBoundingClientRect();
            const x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
            const y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
            
            this.selectObjectAtMouse(x, y);
        });
        
        // Transform mode buttons
        document.getElementById('mode-translate').addEventListener('change', () => {
            this.transformControls.setMode('translate');
        });
        document.getElementById('mode-rotate').addEventListener('change', () => {
            this.transformControls.setMode('rotate');
        });
        document.getElementById('mode-scale').addEventListener('change', () => {
            this.transformControls.setMode('scale');
        });
        
        // Wireframe toggle
        document.getElementById('show-wireframe').addEventListener('change', (event) => {
            this.toggleWireframe(event.target.checked);
        });
        
        // Grid toggle
        document.getElementById('show-grid').addEventListener('change', (event) => {
            this.grid.visible = event.target.checked;
        });
        
        // Axes toggle
        document.getElementById('show-axes').addEventListener('change', (event) => {
            this.axes.visible = event.target.checked;
        });
        
        // Reset view button
        document.getElementById('reset-view').addEventListener('click', () => {
            this.resetView();
        });
        
        // Apply transform button
        document.getElementById('apply-transform').addEventListener('click', () => {
            this.applyTransformFromInputs();
        });
        
        // Undo button
        document.getElementById('undo-action').addEventListener('click', () => {
            this.undoLastAction();
        });
        
        // Save model button
        document.getElementById('save-model').addEventListener('click', () => {
            this.saveModel();
        });
    }
    
    /**
     * Handle window resize
     */
    onWindowResize() {
        this.camera.aspect = this.container.clientWidth / this.container.clientHeight;
        this.camera.updateProjectionMatrix();
        this.renderer.setSize(this.container.clientWidth, this.container.clientHeight);
    }
    
    /**
     * Animation loop
     */
    animate() {
        requestAnimationFrame(this.animate);
        this.orbitControls.update();
        this.renderer.render(this.scene, this.camera);
    }
    
    /**
     * Select object at mouse position
     */
    selectObjectAtMouse(x, y) {
        const raycaster = new THREE.Raycaster();
        const mouse = new THREE.Vector2(x, y);
        
        raycaster.setFromCamera(mouse, this.camera);
        
        // Get all objects that can be selected
        const selectableObjects = [];
        this.model.traverse((object) => {
            if (object.isMesh && object.userData.selectable) {
                selectableObjects.push(object);
            }
        });
        
        const intersects = raycaster.intersectObjects(selectableObjects);
        
        if (intersects.length > 0) {
            this.onObjectSelected(intersects[0].object);
        } else {
            this.clearSelection();
        }
    }
    
    /**
     * Handle object selected
     */
    onObjectSelected(object) {
        // Clear previous selection
        this.clearSelection();
        
        // Set new selection
        this.selectedObject = object;
        
        // Highlight selected object
        const material = object.material.clone();
        material.emissive = new THREE.Color(0x555555);
        material.emissiveIntensity = 0.5;
        object.material = material;
        
        // Attach transform controls
        this.transformControls.attach(object);
        
        // Update UI
        this.updateSelectionUI(object);
        
        // Show selection panel
        document.getElementById('no-selection').style.display = 'none';
        document.getElementById('selection-details').style.display = 'block';
    }
    
    /**
     * Clear current selection
     */
    clearSelection() {
        if (this.selectedObject) {
            // Restore original material
            if (this.selectedObject.userData.originalMaterial) {
                this.selectedObject.material = this.selectedObject.userData.originalMaterial.clone();
                
                // Keep wireframe state
                this.selectedObject.material.wireframe = this.isWireframe;
            }
            
            // Detach transform controls
            this.transformControls.detach();
            this.selectedObject = null;
            
            // Update UI
            document.getElementById('no-selection').style.display = 'block';
            document.getElementById('selection-details').style.display = 'none';
        }
    }
    
    /**
     * Update selection UI
     */
    updateSelectionUI(object) {
        // Update name
        document.getElementById('object-name').value = object.name || 'Unnamed Object';
        
        // Update position
        document.getElementById('pos-x').value = object.position.x.toFixed(2);
        document.getElementById('pos-y').value = object.position.y.toFixed(2);
        document.getElementById('pos-z').value = object.position.z.toFixed(2);
        
        // Convert rotation from radians to degrees
        const rotation = {
            x: THREE.MathUtils.radToDeg(object.rotation.x).toFixed(0),
            y: THREE.MathUtils.radToDeg(object.rotation.y).toFixed(0),
            z: THREE.MathUtils.radToDeg(object.rotation.z).toFixed(0)
        };
        
        // Update rotation
        document.getElementById('rot-x').value = rotation.x;
        document.getElementById('rot-y').value = rotation.y;
        document.getElementById('rot-z').value = rotation.z;
        
        // Update scale
        document.getElementById('scale-x').value = object.scale.x.toFixed(2);
        document.getElementById('scale-y').value = object.scale.y.toFixed(2);
        document.getElementById('scale-z').value = object.scale.z.toFixed(2);
    }
    
    /**
     * Apply transformation from input fields
     */
    applyTransformFromInputs() {
        if (!this.selectedObject) return;
        
        // Store current state for undo
        this.storeStateForUndo();
        
        // Update object name
        this.selectedObject.name = document.getElementById('object-name').value;
        
        // Update position
        const posX = parseFloat(document.getElementById('pos-x').value);
        const posY = parseFloat(document.getElementById('pos-y').value);
        const posZ = parseFloat(document.getElementById('pos-z').value);
        this.selectedObject.position.set(posX, posY, posZ);
        
        // Update rotation (convert from degrees to radians)
        const rotX = THREE.MathUtils.degToRad(parseFloat(document.getElementById('rot-x').value));
        const rotY = THREE.MathUtils.degToRad(parseFloat(document.getElementById('rot-y').value));
        const rotZ = THREE.MathUtils.degToRad(parseFloat(document.getElementById('rot-z').value));
        this.selectedObject.rotation.set(rotX, rotY, rotZ);
        
        // Update scale
        const scaleX = parseFloat(document.getElementById('scale-x').value);
        const scaleY = parseFloat(document.getElementById('scale-y').value);
        const scaleZ = parseFloat(document.getElementById('scale-z').value);
        this.selectedObject.scale.set(scaleX, scaleY, scaleZ);
        
        // Update transform controls
        this.transformControls.update();
        
        // Show success message
        this.showNotification('Changes applied successfully', 'success');
    }
    
    /**
     * Handle transform controls change
     */
    handleTransformChange() {
        if (this.selectedObject) {
            this.updateSelectionUI(this.selectedObject);
        }
    }
    
    /**
     * Toggle wireframe mode
     */
    toggleWireframe(enabled) {
        this.isWireframe = enabled;
        
        // Apply to all meshes
        this.model.traverse((object) => {
            if (object.isMesh) {
                object.material.wireframe = enabled;
            }
        });
    }
    
    /**
     * Reset camera view
     */
    resetView() {
        this.camera.position.set(5, 5, 5);
        this.camera.lookAt(0, 0, 0);
        this.orbitControls.reset();
    }
    
    /**
     * Build model structure UI
     */
    buildModelStructure() {
        const container = document.getElementById('model-structure');
        container.innerHTML = '';
        
        // Function to create structure items
        const createStructureItem = (object, level = 0) => {
            // Skip non-mesh objects with no children
            if (!object.isMesh && object.children.length === 0) {
                return '';
            }
            
            // Create item
            const itemEl = document.createElement('div');
            itemEl.className = 'list-group-item ps-' + (level + 2);
            itemEl.innerHTML = `
                <div class="d-flex justify-content-between align-items-center">
                    <span class="${object.isMesh ? 'text-primary' : ''}">
                        ${object.isMesh ? '<i class="fas fa-cube me-2"></i>' : '<i class="fas fa-folder me-2"></i>'}
                        ${object.name || 'Unnamed Object'}
                    </span>
                    ${object.isMesh ? '<button class="btn btn-sm btn-outline-primary select-object" data-uuid="' + object.uuid + '"><i class="fas fa-edit"></i></button>' : ''}
                </div>
            `;
            
            // Add click event for mesh objects
            if (object.isMesh) {
                itemEl.querySelector('.select-object').addEventListener('click', () => {
                    this.onObjectSelected(object);
                });
            }
            
            container.appendChild(itemEl);
            
            // Process children
            object.children.forEach(child => {
                createStructureItem(child, level + 1);
            });
        };
        
        // Create structure
        createStructureItem(this.model);
    }
    
    /**
     * Store current state for undo
     */
    storeStateForUndo() {
        if (!this.selectedObject) return;
        
        const state = {
            uuid: this.selectedObject.uuid,
            position: this.selectedObject.position.clone(),
            rotation: this.selectedObject.rotation.clone(),
            scale: this.selectedObject.scale.clone(),
            name: this.selectedObject.name
        };
        
        this.editHistory.push(state);
        
        // Limit history size
        if (this.editHistory.length > 20) {
            this.editHistory.shift();
        }
    }
    
    /**
     * Undo last action
     */
    undoLastAction() {
        if (this.editHistory.length === 0) {
            this.showNotification('Nothing to undo', 'warning');
            return;
        }
        
        const state = this.editHistory.pop();
        
        // Find the object
        let object = null;
        this.model.traverse((node) => {
            if (node.uuid === state.uuid) {
                object = node;
            }
        });
        
        if (!object) {
            this.showNotification('Cannot find object to undo', 'error');
            return;
        }
        
        // Apply previous state
        object.position.copy(state.position);
        object.rotation.copy(state.rotation);
        object.scale.copy(state.scale);
        object.name = state.name;
        
        // Select the object again
        this.onObjectSelected(object);
        
        // Show notification
        this.showNotification('Action undone', 'success');
    }
    
    /**
     * Save the model
     */
    saveModel() {
        // Create exporter
        const exporter = new THREE.GLTFExporter();
        
        // Clone model to prevent modifying original
        const modelClone = this.model.clone();
        
        // Export the model
        exporter.parse(
            modelClone,
            (result) => {
                // Success callback
                const output = JSON.stringify(result);
                
                // Set form data
                document.getElementById('model-data').value = output;
                
                // Submit form
                const form = document.getElementById('save-model-form');
                
                // Show loading message
                this.showNotification('Saving model...', 'info');
                
                // Use fetch to submit form
                fetch(
                    window.location.href,
                    {
                        method: 'POST',
                        body: new FormData(form),
                        headers: {
                            'X-Requested-With': 'XMLHttpRequest'
                        }
                    }
                )
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        this.showNotification('Model saved successfully', 'success');
                    } else {
                        this.showNotification('Failed to save model: ' + data.message, 'error');
                    }
                })
                .catch(error => {
                    console.error('Error saving model:', error);
                    this.showNotification('Error saving model', 'error');
                });
            },
            (error) => {
                // Error callback
                console.error('Error exporting model:', error);
                this.showNotification('Error exporting model', 'error');
            },
            { binary: false }
        );
    }
    
    /**
     * Show notification
     */
    showNotification(message, type = 'info') {
        // Create toast element
        const toast = document.createElement('div');
        toast.className = `toast align-items-center text-white bg-${type} border-0`;
        toast.setAttribute('role', 'alert');
        toast.setAttribute('aria-live', 'assertive');
        toast.setAttribute('aria-atomic', 'true');
        
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">
                    ${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
        `;
        
        // Create toast container if not exists
        let toastContainer = document.querySelector('.toast-container');
        if (!toastContainer) {
            toastContainer = document.createElement('div');
            toastContainer.className = 'toast-container position-fixed top-0 end-0 p-3';
            document.body.appendChild(toastContainer);
        }
        
        // Add to container
        toastContainer.appendChild(toast);
        
        // Initialize Bootstrap toast
        const bsToast = new bootstrap.Toast(toast, {
            autohide: true,
            delay: 3000
        });
        
        // Show toast
        bsToast.show();
        
        // Remove after hidden
        toast.addEventListener('hidden.bs.toast', () => {
            toastContainer.removeChild(toast);
        });
    }
} 