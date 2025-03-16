// OrbitControls.js - Three.js OrbitControls as ES module
export class OrbitControls {
    constructor(camera, domElement) {
        this.camera = camera;
        this.domElement = domElement;
        
        // Default settings
        this.enabled = true;
        this.target = new THREE.Vector3();
        this.enableZoom = true;
        this.zoomSpeed = 1.0;
        this.enableRotate = true;
        this.rotateSpeed = 1.0;
        this.enablePan = true;
        this.panSpeed = 1.0;
        this.enableDamping = false;
        this.dampingFactor = 0.05;
        
        // Internals
        this._spherical = new THREE.Spherical();
        this._sphericalDelta = new THREE.Spherical();
        this._scale = 1;
        this._panOffset = new THREE.Vector3();
        this._zoomChanged = false;
        
        // Event bindings
        this._onContextMenu = this._onContextMenu.bind(this);
        this._onMouseDown = this._onMouseDown.bind(this);
        this._onMouseMove = this._onMouseMove.bind(this);
        this._onMouseUp = this._onMouseUp.bind(this);
        this._onMouseWheel = this._onMouseWheel.bind(this);
        this._onTouchStart = this._onTouchStart.bind(this);
        this._onTouchMove = this._onTouchMove.bind(this);
        this._onTouchEnd = this._onTouchEnd.bind(this);
        
        this._addEventListeners();
    }
    
    // Public methods
    update() {
        const offset = new THREE.Vector3();
        
        // Move target to camera position
        offset.copy(this.camera.position).sub(this.target);
        
        // Rotate
        if (this._sphericalDelta.theta || this._sphericalDelta.phi) {
            offset.applyQuaternion(this.camera.quaternion);
        }
        
        // Apply zoom
        if (this._scale !== 1) {
            offset.multiplyScalar(this._scale);
            this._scale = 1;
        }
        
        // Apply pan
        if (!this._panOffset.equals(new THREE.Vector3())) {
            this.camera.position.add(this._panOffset);
            this.target.add(this._panOffset);
            this._panOffset.set(0, 0, 0);
        }
        
        this.camera.lookAt(this.target);
        
        if (this.enableDamping) {
            this._sphericalDelta.theta *= (1 - this.dampingFactor);
            this._sphericalDelta.phi *= (1 - this.dampingFactor);
        } else {
            this._sphericalDelta.set(0, 0, 0);
        }
        
        return false;
    }
    
    dispose() {
        this._removeEventListeners();
    }
    
    // Private methods
    _addEventListeners() {
        this.domElement.addEventListener('contextmenu', this._onContextMenu);
        this.domElement.addEventListener('mousedown', this._onMouseDown);
        this.domElement.addEventListener('wheel', this._onMouseWheel);
        this.domElement.addEventListener('touchstart', this._onTouchStart);
        this.domElement.addEventListener('touchend', this._onTouchEnd);
        this.domElement.addEventListener('touchmove', this._onTouchMove);
    }
    
    _removeEventListeners() {
        this.domElement.removeEventListener('contextmenu', this._onContextMenu);
        this.domElement.removeEventListener('mousedown', this._onMouseDown);
        this.domElement.removeEventListener('wheel', this._onMouseWheel);
        this.domElement.removeEventListener('touchstart', this._onTouchStart);
        this.domElement.removeEventListener('touchend', this._onTouchEnd);
        this.domElement.removeEventListener('touchmove', this._onTouchMove);
    }
    
    _onContextMenu(event) {
        if (this.enabled) event.preventDefault();
    }
    
    _onMouseDown(event) {
        if (!this.enabled) return;
        
        event.preventDefault();
        
        this.domElement.addEventListener('mousemove', this._onMouseMove);
        this.domElement.addEventListener('mouseup', this._onMouseUp);
    }
    
    _onMouseMove(event) {
        if (!this.enabled) return;
        
        event.preventDefault();
        
        const movementX = event.movementX || event.mozMovementX || event.webkitMovementX || 0;
        const movementY = event.movementY || event.mozMovementY || event.webkitMovementY || 0;
        
        if (event.buttons === 1) { // Left button
            if (this.enableRotate) {
                this._sphericalDelta.theta -= movementX * this.rotateSpeed * 0.002;
                this._sphericalDelta.phi -= movementY * this.rotateSpeed * 0.002;
            }
        } else if (event.buttons === 2) { // Right button
            if (this.enablePan) {
                this._panOffset.x -= movementX * this.panSpeed * 0.002;
                this._panOffset.y += movementY * this.panSpeed * 0.002;
            }
        }
    }
    
    _onMouseUp() {
        this.domElement.removeEventListener('mousemove', this._onMouseMove);
        this.domElement.removeEventListener('mouseup', this._onMouseUp);
    }
    
    _onMouseWheel(event) {
        if (!this.enabled || !this.enableZoom) return;
        
        event.preventDefault();
        
        if (event.deltaY < 0) {
            this._scale /= Math.pow(0.95, this.zoomSpeed);
        } else {
            this._scale *= Math.pow(0.95, this.zoomSpeed);
        }
    }
    
    _onTouchStart(event) {
        if (!this.enabled) return;
        
        event.preventDefault();
    }
    
    _onTouchMove(event) {
        if (!this.enabled) return;
        
        event.preventDefault();
    }
    
    _onTouchEnd() {
        // Touch end handler
    }
}

// Add to THREE namespace for compatibility with non-module scripts
if (window.THREE) {
    window.THREE.OrbitControls = OrbitControls;
} 