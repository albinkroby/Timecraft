/**
 * 3D Part Configurator
 * This script handles the interactive 3D model viewer and part configuration functionality
 */

// Initialize all the core components
document.addEventListener('DOMContentLoaded', function() {
    // Initialize 3D viewer
    const configurator = new WatchConfigurator();
    configurator.initialize();
    
    // Initialize UI interactions
    setupUIInteractions(configurator);
});

/**
 * Main Watch Configurator class
 * Handles 3D rendering and interaction
 */
class WatchConfigurator {
    constructor() {
        // THREE.js core components
        this.scene = null;
        this.camera = null;
        this.renderer = null;
        this.controls = null;
        
        // Model and parts management
        this.model = null;
        this.modelPath = null;
        this.loadedParts = []; // All mesh parts in the model
        this.configuredParts = []; // Parts that have been configured
        
        // Raycaster for clicking parts
        this.raycaster = new THREE.Raycaster();
        this.mouse = new THREE.Vector2();
        
        // Currently selected part
        this.selectedPart = null;
        this.originalMaterials = {}; // Store original materials
        this.highlightMaterial = new THREE.MeshStandardMaterial({
            color: 0x2194ce,
            emissive: 0x072534,
            side: THREE.DoubleSide,
            transparent: true,
            opacity: 0.8
        });
        
        // Track application state
        this.isWireframe = false;
    }
    
    /**
     * Initialize the 3D environment
     */
    initialize() {
        const container = document.getElementById('model-container');
        
        // Create scene
        this.scene = new THREE.Scene();
        this.scene.background = new THREE.Color(0xf5f5f5);
        
        // Create camera
        this.camera = new THREE.PerspectiveCamera(
            75, 
            container.clientWidth / container.clientHeight,
            0.1,
            1000
        );
        this.camera.position.set(0, 0, 5);
        
        // Create renderer
        this.renderer = new THREE.WebGLRenderer({ antialias: true });
        this.renderer.setSize(container.clientWidth, container.clientHeight);
        this.renderer.setPixelRatio(window.devicePixelRatio);
        this.renderer.shadowMap.enabled = true;
        container.appendChild(this.renderer.domElement);
        
        // Create orbit controls
        this.controls = new THREE.OrbitControls(this.camera, this.renderer.domElement);
        this.controls.enableDamping = true;
        this.controls.dampingFactor = 0.25;
        
        // Add lights
        this.addLights();
        
        // Set up event listeners
        this.setupEventListeners();
        
        // Get model path from the data attribute
        const watchId = document.getElementById('watch-id').value;
        this.fetchModelPath(watchId);
        
        // Start animation loop
        this.animate();
    }
    
    /**
     * Add lights to the scene
     */
    addLights() {
        // Ambient light
        const ambientLight = new THREE.AmbientLight(0xffffff, 0.5);
        this.scene.add(ambientLight);
        
        // Directional lights
        const directionalLight1 = new THREE.DirectionalLight(0xffffff, 0.8);
        directionalLight1.position.set(5, 10, 7.5);
        directionalLight1.castShadow = true;
        this.scene.add(directionalLight1);
        
        const directionalLight2 = new THREE.DirectionalLight(0xffffff, 0.5);
        directionalLight2.position.set(-5, 5, -7.5);
        this.scene.add(directionalLight2);
    }
    
    /**
     * Set up event listeners
     */
    setupEventListeners() {
        const container = document.getElementById('model-container');
        
        // Handle window resizing
        window.addEventListener('resize', () => this.onWindowResize());
        
        // Handle clicking on model parts
        container.addEventListener('click', (event) => this.onModelClick(event));
    }
    
    /**
     * Handle window resize
     */
    onWindowResize() {
        const container = document.getElementById('model-container');
        this.camera.aspect = container.clientWidth / container.clientHeight;
        this.camera.updateProjectionMatrix();
        this.renderer.setSize(container.clientWidth, container.clientHeight);
    }
    
    /**
     * Animation loop
     */
    animate() {
        requestAnimationFrame(() => this.animate());
        this.controls.update();
        this.renderer.render(this.scene, this.camera);
    }
    
    /**
     * Fetch the model path from the server
     */
    fetchModelPath(watchId) {
        fetch(`/adminapp/get-model-path/${watchId}/`)
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    this.modelPath = data.model_path;
                    this.loadModel();
                } else {
                    console.error('Failed to get model path:', data.message);
                    alert('Failed to load model path. Please check the console for details.');
                }
            })
            .catch(error => {
                console.error('Error fetching model path:', error);
                alert('Error fetching model path. Please check the console for details.');
            });
    }
    
    /**
     * Load the 3D model
     */
    loadModel() {
        if (!this.modelPath) {
            console.error('No model path specified');
            return;
        }
        
        const loader = new THREE.GLTFLoader();
        
        // Show loading message
        const container = document.getElementById('model-container');
        const loadingElement = document.createElement('div');
        loadingElement.className = 'loading-overlay';
        loadingElement.innerHTML = `
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
            <div class="mt-2">Loading model...</div>
        `;
        loadingElement.style.cssText = `
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            background-color: rgba(255, 255, 255, 0.7);
            z-index: 10;
        `;
        container.appendChild(loadingElement);
        
        // Load the model
        loader.load(
            this.modelPath,
            (gltf) => {
                // Remove loading message
                container.removeChild(loadingElement);
                
                // Add model to scene
                this.model = gltf.scene;
                
                // Traverse model to find meshes
                this.model.traverse((node) => {
                    if (node.isMesh) {
                        // Add to loadedParts array
                        this.loadedParts.push(node);
                        
                        // Store original material
                        this.originalMaterials[node.uuid] = node.material.clone();
                        
                        // Enable shadows
                        node.castShadow = true;
                        node.receiveShadow = true;
                    }
                });
                
                // Center model
                const box = new THREE.Box3().setFromObject(this.model);
                const center = box.getCenter(new THREE.Vector3());
                this.model.position.sub(center);
                
                // Scale model to fit view
                const size = box.getSize(new THREE.Vector3());
                const maxDim = Math.max(size.x, size.y, size.z);
                const scale = 3 / maxDim;
                this.model.scale.set(scale, scale, scale);
                
                // Add to scene
                this.scene.add(this.model);
                
                // Log model hierarchy for debugging
                console.log('Model loaded, hierarchy:');
                this.logModelHierarchy(this.model);
            },
            (xhr) => {
                // Progress callback
                const percent = xhr.loaded / xhr.total * 100;
                console.log(`Loading model: ${Math.round(percent)}%`);
            },
            (error) => {
                // Error callback
                container.removeChild(loadingElement);
                console.error('Error loading model:', error);
                alert('Failed to load 3D model. Please check the console for details.');
            }
        );
    }
    
    /**
     * Handle clicking on model parts
     */
    onModelClick(event) {
        // Get mouse position
        const container = document.getElementById('model-container');
        const rect = container.getBoundingClientRect();
        
        this.mouse.x = ((event.clientX - rect.left) / container.clientWidth) * 2 - 1;
        this.mouse.y = -((event.clientY - rect.top) / container.clientHeight) * 2 + 1;
        
        // Update raycaster
        this.raycaster.setFromCamera(this.mouse, this.camera);
        
        // Find intersections with model parts
        const intersects = this.raycaster.intersectObjects(this.loadedParts, true);
        
        // Clear previous selection
        if (this.selectedPart) {
            this.selectedPart.material = this.originalMaterials[this.selectedPart.uuid].clone();
        }
        
        // Update selection
        if (intersects.length > 0) {
            this.selectedPart = intersects[0].object;
            
            // Highlight selected part
            this.selectedPart.material = this.highlightMaterial.clone();
            
            // Update UI
            this.updatePartSelectionUI();
        } else {
            this.selectedPart = null;
            
            // Update UI
            document.getElementById('selected-part-info').style.display = 'none';
            document.getElementById('selectionHelp').style.display = 'block';
            document.getElementById('color-options-container').style.display = 'none';
            document.getElementById('color-options-help').style.display = 'block';
        }
    }
    
    /**
     * Update UI based on selected part
     */
    updatePartSelectionUI() {
        const partNameElement = document.getElementById('selected-part-name');
        const selectionHelpElement = document.getElementById('selectionHelp');
        const selectedPartInfoElement = document.getElementById('selected-part-info');
        const colorOptionsContainer = document.getElementById('color-options-container');
        const colorOptionsHelp = document.getElementById('color-options-help');
        
        // Check if there is a selected part
        if (!this.selectedPart) {
            return;
        }
        
        // Update part name display
        const partName = this.selectedPart.name || `Part ${this.selectedPart.uuid.slice(0, 8)}`;
        partNameElement.textContent = partName;
        
        // Update display visibility
        selectionHelpElement.style.display = 'none';
        selectedPartInfoElement.style.display = 'block';
        colorOptionsContainer.style.display = 'block';
        colorOptionsHelp.style.display = 'none';
        
        // Check if part is already configured
        const existingConfig = this.configuredParts.find(p => p.uuid === this.selectedPart.uuid);
        if (existingConfig) {
            document.getElementById('part-category').value = existingConfig.category || '';
            document.getElementById('part-description').value = existingConfig.description || '';
        } else {
            document.getElementById('part-category').value = '';
            document.getElementById('part-description').value = '';
        }
    }
    
    /**
     * Apply color to selected part
     */
    applyColorToPart(colorHex) {
        if (!this.selectedPart) {
            return;
        }
        
        // Create new material with selected color
        const newMaterial = new THREE.MeshStandardMaterial({
            color: new THREE.Color(colorHex),
            metalness: 0.2,
            roughness: 0.5
        });
        
        // Apply to selected part
        this.selectedPart.material = newMaterial;
    }
    
    /**
     * Save part configuration
     */
    savePartConfiguration(category, description) {
        if (!this.selectedPart) {
            return false;
        }
        
        // Get part information
        const partName = this.selectedPart.name || `Part ${this.selectedPart.uuid.slice(0, 8)}`;
        const modelPath = this.getPartPath(this.selectedPart);
        
        // Find or create part config
        const existingIndex = this.configuredParts.findIndex(p => p.uuid === this.selectedPart.uuid);
        
        const partConfig = {
            uuid: this.selectedPart.uuid,
            name: partName,
            category: category,
            description: description,
            modelPath: modelPath,
            colorOptions: []
        };
        
        // Update or add to configured parts
        if (existingIndex >= 0) {
            // Keep existing color options
            partConfig.colorOptions = this.configuredParts[existingIndex].colorOptions || [];
            this.configuredParts[existingIndex] = partConfig;
        } else {
            this.configuredParts.push(partConfig);
        }
        
        // Update UI
        this.updateConfiguredPartsList();
        
        return true;
    }
    
    /**
     * Add color option to selected part
     */
    addColorOption(colorHex, colorName, price) {
        if (!this.selectedPart) {
            return false;
        }
        
        // Find part in configured parts
        const partIndex = this.configuredParts.findIndex(p => p.uuid === this.selectedPart.uuid);
        
        if (partIndex < 0) {
            alert('Please save part configuration first');
            return false;
        }
        
        // Create color option
        const colorOption = {
            id: Date.now(), // Temporary ID for client-side use
            color: colorHex,
            name: colorName,
            price: price || 0
        };
        
        // Add to part's color options
        if (!this.configuredParts[partIndex].colorOptions) {
            this.configuredParts[partIndex].colorOptions = [];
        }
        
        this.configuredParts[partIndex].colorOptions.push(colorOption);
        
        // Update UI
        this.updateColorOptionsList();
        
        return true;
    }
    
    /**
     * Update the list of configured parts in the UI
     */
    updateConfiguredPartsList() {
        const container = document.getElementById('configured-parts-list');
        container.innerHTML = '';
        
        if (this.configuredParts.length === 0) {
            container.innerHTML = '<div class="alert alert-secondary">No parts configured yet</div>';
            return;
        }
        
        // Group parts by category
        const categories = {};
        this.configuredParts.forEach(part => {
            const category = part.category || 'uncategorized';
            if (!categories[category]) {
                categories[category] = [];
            }
            categories[category].push(part);
        });
        
        // Create list items for each category and part
        for (const [category, parts] of Object.entries(categories)) {
            const categoryTitle = document.createElement('h6');
            categoryTitle.className = 'mt-3 mb-2';
            categoryTitle.textContent = category.charAt(0).toUpperCase() + category.slice(1);
            container.appendChild(categoryTitle);
            
            parts.forEach(part => {
                const item = document.createElement('div');
                item.className = 'list-group-item d-flex justify-content-between align-items-center';
                item.innerHTML = `
                    <div>
                        <span class="fw-bold">${part.name}</span>
                        <small class="d-block text-muted">${part.description || ''}</small>
                    </div>
                    <div>
                        <span class="badge bg-info me-2">${part.colorOptions?.length || 0} colors</span>
                        <button class="btn btn-sm btn-outline-primary edit-part" data-uuid="${part.uuid}">
                            <i class="fas fa-pencil-alt"></i>
                        </button>
                    </div>
                `;
                container.appendChild(item);
                
                // Add click event for editing
                item.querySelector('.edit-part').addEventListener('click', () => this.editConfiguredPart(part.uuid));
            });
        }
    }
    
    /**
     * Update the list of color options for the selected part
     */
    updateColorOptionsList() {
        const container = document.getElementById('saved-colors-container');
        container.innerHTML = '';
        
        if (!this.selectedPart) {
            return;
        }
        
        // Find part in configured parts
        const part = this.configuredParts.find(p => p.uuid === this.selectedPart.uuid);
        
        if (!part || !part.colorOptions || part.colorOptions.length === 0) {
            container.innerHTML = '<div class="alert alert-secondary">No color options yet</div>';
            return;
        }
        
        // Create list items for each color option
        part.colorOptions.forEach(option => {
            const item = document.createElement('div');
            item.className = 'list-group-item d-flex justify-content-between align-items-center color-option-item';
            item.setAttribute('data-color', option.color);
            item.innerHTML = `
                <div>
                    <span class="color-preview" style="display: inline-block; width: 20px; height: 20px; background-color: ${option.color}; border: 1px solid #ccc; margin-right: 8px;"></span>
                    <span>${option.name}</span>
                </div>
                <div>
                    <span class="badge bg-primary">$${option.price || 0}</span>
                    <button class="btn btn-sm btn-danger delete-color ms-2" data-id="${option.id}">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            `;
            container.appendChild(item);
            
            // Add click event for color preview
            item.addEventListener('click', (e) => {
                if (!e.target.closest('.delete-color')) {
                    this.applyColorToPart(option.color);
                }
            });
            
            // Add click event for delete button
            item.querySelector('.delete-color').addEventListener('click', (e) => {
                e.stopPropagation();
                this.deleteColorOption(option.id);
            });
        });
    }
    
    /**
     * Delete a color option
     */
    deleteColorOption(optionId) {
        if (!this.selectedPart) {
            return;
        }
        
        // Find part in configured parts
        const partIndex = this.configuredParts.findIndex(p => p.uuid === this.selectedPart.uuid);
        
        if (partIndex < 0) {
            return;
        }
        
        // Remove color option
        const part = this.configuredParts[partIndex];
        part.colorOptions = part.colorOptions.filter(option => option.id !== optionId);
        
        // Update UI
        this.updateColorOptionsList();
    }
    
    /**
     * Edit a configured part
     */
    editConfiguredPart(uuid) {
        // Find mesh in the model
        let targetMesh = null;
        this.model.traverse(node => {
            if (node.uuid === uuid) {
                targetMesh = node;
            }
        });
        
        if (!targetMesh) {
            console.error('Could not find part with UUID:', uuid);
            return;
        }
        
        // Select this part
        if (this.selectedPart) {
            this.selectedPart.material = this.originalMaterials[this.selectedPart.uuid].clone();
        }
        
        this.selectedPart = targetMesh;
        this.selectedPart.material = this.highlightMaterial.clone();
        
        // Update UI
        this.updatePartSelectionUI();
        this.updateColorOptionsList();
    }
    
    /**
     * Get the path to a part in the model hierarchy
     */
    getPartPath(part) {
        // Start with the part itself
        let path = part.name || part.uuid;
        let current = part;
        
        // Traverse up the hierarchy
        while (current.parent && current !== this.model) {
            current = current.parent;
            const nodeName = current.name || current.uuid;
            path = `${nodeName}>${path}`;
            
            if (current === this.scene) break;
        }
        
        return path;
    }
    
    /**
     * Toggle wireframe mode
     */
    toggleWireframe() {
        this.isWireframe = !this.isWireframe;
        
        this.model.traverse(node => {
            if (node.isMesh) {
                node.material.wireframe = this.isWireframe;
            }
        });
    }
    
    /**
     * Reset camera view
     */
    resetView() {
        this.camera.position.set(0, 0, 5);
        this.controls.reset();
    }
    
    /**
     * Log model hierarchy for debugging
     */
    logModelHierarchy(model, indent = '') {
        console.log(indent + (model.name || 'unnamed') + (model.isMesh ? ' (Mesh)' : ''));
        model.children.forEach(child => this.logModelHierarchy(child, indent + '  '));
    }
    
    /**
     * Get data for saving to the server
     */
    getDataForSave() {
        return this.configuredParts;
    }
}

/**
 * Setup UI interactions
 */
function setupUIInteractions(configurator) {
    // Handle Reset View button
    document.getElementById('resetView').addEventListener('click', () => {
        configurator.resetView();
    });
    
    // Handle Toggle Wireframe button
    document.getElementById('toggleWireframe').addEventListener('click', () => {
        configurator.toggleWireframe();
    });
    
    // Handle Save Part Configuration button
    document.getElementById('save-part-config').addEventListener('click', () => {
        const category = document.getElementById('part-category').value;
        const description = document.getElementById('part-description').value;
        
        if (!category) {
            alert('Please select a category');
            return;
        }
        
        if (configurator.savePartConfiguration(category, description)) {
            alert('Part configuration saved');
        }
    });
    
    // Handle Add Color Option button
    document.getElementById('add-color-option').addEventListener('click', () => {
        const colorHex = document.getElementById('color-picker').value;
        const colorName = document.getElementById('color-name').value;
        const price = document.getElementById('color-price').value;
        
        if (!colorName) {
            alert('Please enter a name for the color');
            return;
        }
        
        if (configurator.addColorOption(colorHex, colorName, price)) {
            // Clear inputs
            document.getElementById('color-name').value = '';
            document.getElementById('color-price').value = '';
        }
    });
    
    // Handle Complete Configuration button
    document.getElementById('complete-configuration').addEventListener('click', () => {
        // Get data
        const configData = configurator.getDataForSave();
        
        if (configData.length === 0) {
            alert('Please configure at least one part before completing');
            return;
        }
        
        // Set form data
        document.getElementById('part-data').value = JSON.stringify(configData);
        
        // Submit form
        document.getElementById('part-config-form').submit();
    });
} 