// Smart Transportation Dashboard JavaScript

class TransportDashboard {
    constructor() {
        this.map = null;
        this.vehicleMarkers = new Map();
        this.eventMarkers = new Map();
        this.websocket = null;
        this.apiBaseUrl = 'http://localhost:5000/api/v1';
        
        this.initializeMap();
        this.connectWebSocket();
        this.startDataRefresh();
        this.checkSystemHealth();
    }
    
    initializeMap() {
        // Initialize Leaflet map centered on Bhubaneswar
        this.map = L.map('map').setView([20.2961, 85.8245], 12);
        
        // Add OpenStreetMap tiles
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors'
        }).addTo(this.map);
        
        // Add toll gantry markers
        this.addTollGantries();
    }
    
    addTollGantries() {
        const gantries = [
            { id: 'G-001', name: 'Highway Entry Point 1', lat: 20.2961, lon: 85.8245 },
            { id: 'G-002', name: 'City Center Toll', lat: 20.3000, lon: 85.8300 },
            { id: 'G-003', name: 'Airport Express', lat: 20.2500, lon: 85.8100 }
        ];
        
        gantries.forEach(gantry => {
            const marker = L.marker([gantry.lat, gantry.lon], {
                icon: L.divIcon({
                    className: 'toll-gantry-marker',
                    html: '🏛️',
                    iconSize: [30, 30]
                })
            }).addTo(this.map);
            
            marker.bindPopup(`
                <strong>${gantry.name}</strong><br>
                ID: ${gantry.id}<br>
                Status: Active
            `);
        });
    }
    
    connectWebSocket() {
        try {
            this.websocket = new WebSocket('ws://localhost:5000/ws/admin/stream');
            
            this.websocket.onopen = () => {
                console.log('WebSocket connected');
                this.updateConnectionStatus(true);
            };
            
            this.websocket.onmessage = (event) => {
                const data = JSON.parse(event.data);
                this.handleRealtimeData(data);
            };
            
            this.websocket.onclose = () => {
                console.log('WebSocket disconnected');
                this.updateConnectionStatus(false);
                // Reconnect after 5 seconds
                setTimeout(() => this.connectWebSocket(), 5000);
            };
            
            this.websocket.onerror = (error) => {
                console.error('WebSocket error:', error);
                this.updateConnectionStatus(false);
            };
        } catch (error) {
            console.error('WebSocket connection failed:', error);
            this.updateConnectionStatus(false);
        }
    }
    
    updateConnectionStatus(connected) {
        const statusElement = document.getElementById('connectionStatus');
        if (connected) {
            statusElement.innerHTML = '<span class="status-online">● Connected</span>';
        } else {
            statusElement.innerHTML = '<span class="status-offline">● Disconnected</span>';
        }
    }
    
    handleRealtimeData(data) {
        switch (data.type) {
            case 'telemetry':
                this.updateVehiclePosition(data);
                break;
            case 'event':
                this.addEvent(data);
                break;
            case 'alert':
                this.showAlert(data);
                break;
        }
    }
    
    updateVehiclePosition(telemetry) {
        const deviceId = telemetry.deviceId;
        const lat = telemetry.location.lat;
        const lon = telemetry.location.lon;
        const speed = telemetry.speedKmph;
        
        if (this.vehicleMarkers.has(deviceId)) {
            // Update existing marker
            const marker = this.vehicleMarkers.get(deviceId);
            marker.setLatLng([lat, lon]);
            marker.setPopupContent(this.getVehiclePopupContent(telemetry));
        } else {
            // Create new marker
            const marker = L.marker([lat, lon], {
                icon: L.divIcon({
                    className: 'vehicle-marker',
                    html: '🚗',
                    iconSize: [25, 25]
                })
            }).addTo(this.map);
            
            marker.bindPopup(this.getVehiclePopupContent(telemetry));
            this.vehicleMarkers.set(deviceId, marker);
        }
        
        // Update vehicle list
        this.updateVehiclesList();
    }
    
    getVehiclePopupContent(telemetry) {
        return `
            <strong>Vehicle ${telemetry.deviceId}</strong><br>
            Speed: ${telemetry.speedKmph} km/h<br>
            Heading: ${telemetry.heading}°<br>
            Battery: ${telemetry.batteryVoltage}V<br>
            Last Update: ${new Date(telemetry.timestamp).toLocaleTimeString()}
        `;
    }
    
    addEvent(event) {
        const lat = event.location?.lat;
        const lon = event.location?.lon;
        
        if (lat && lon) {
            const marker = L.marker([lat, lon], {
                icon: L.divIcon({
                    className: 'event-marker',
                    html: '⚠️',
                    iconSize: [20, 20]
                })
            }).addTo(this.map);
            
            marker.bindPopup(`
                <strong>${event.eventType}</strong><br>
                Device: ${event.deviceId}<br>
                Speed: ${event.speedBefore} → ${event.speedAfter} km/h<br>
                Time: ${new Date(event.timestamp).toLocaleString()}
            `);
            
            this.eventMarkers.set(event.eventId || Date.now(), marker);
            
            // Remove marker after 5 minutes
            setTimeout(() => {
                this.map.removeLayer(marker);
            }, 300000);
        }
        
        // Update events list
        this.updateEventsList(event);
    }
    
    updateEventsList(event) {
        const eventsList = document.getElementById('eventsList');
        
        // Remove "No events" message
        if (eventsList.children.length === 1 && eventsList.children[0].textContent === 'No events') {
            eventsList.innerHTML = '';
        }
        
        const eventElement = document.createElement('div');
        eventElement.className = 'list-group-item';
        eventElement.innerHTML = `
            <div class="d-flex w-100 justify-content-between">
                <h6 class="mb-1">${event.eventType}</h6>
                <small>${new Date(event.timestamp).toLocaleTimeString()}</small>
            </div>
            <p class="mb-1">Device: ${event.deviceId}</p>
            <small>Speed: ${event.speedBefore} → ${event.speedAfter} km/h</small>
        `;
        
        // Add to top of list
        eventsList.insertBefore(eventElement, eventsList.firstChild);
        
        // Keep only last 10 events
        while (eventsList.children.length > 10) {
            eventsList.removeChild(eventsList.lastChild);
        }
    }
    
    updateVehiclesList() {
        const vehiclesList = document.getElementById('vehiclesList');
        
        if (this.vehicleMarkers.size === 0) {
            vehiclesList.innerHTML = '<div class="list-group-item text-muted text-center">No vehicles online</div>';
            return;
        }
        
        vehiclesList.innerHTML = '';
        
        this.vehicleMarkers.forEach((marker, deviceId) => {
            const vehicleElement = document.createElement('div');
            vehicleElement.className = 'list-group-item';
            vehicleElement.innerHTML = `
                <div class="d-flex w-100 justify-content-between">
                    <h6 class="mb-1">${deviceId}</h6>
                    <span class="badge bg-success">Online</span>
                </div>
                <p class="mb-1">Last seen: ${new Date().toLocaleTimeString()}</p>
            `;
            
            // Click to center map on vehicle
            vehicleElement.addEventListener('click', () => {
                const latLng = marker.getLatLng();
                this.map.setView(latLng, 15);
                marker.openPopup();
            });
            
            vehiclesList.appendChild(vehicleElement);
        });
    }
    
    async startDataRefresh() {
        // Refresh dashboard data every 30 seconds
        setInterval(async () => {
            await this.refreshDashboardData();
        }, 30000);
        
        // Initial load
        await this.refreshDashboardData();
    }
    
    async refreshDashboardData() {
        try {
            // Get dashboard statistics
            const response = await fetch(`${this.apiBaseUrl}/admin/dashboard`);
            if (response.ok) {
                const data = await response.json();
                this.updateMetrics(data);
            }
        } catch (error) {
            console.error('Failed to refresh dashboard data:', error);
        }
    }
    
    updateMetrics(data) {
        const stats = data.statistics || {};
        
        document.getElementById('activeVehicles').textContent = data.active_devices?.length || 0;
        document.getElementById('dailyRevenue').textContent = `$${(stats.daily_revenue || 0).toFixed(2)}`;
        document.getElementById('activeAlerts').textContent = this.eventMarkers.size;
        document.getElementById('avgScore').textContent = '75'; // Mock data
    }
    
    async checkSystemHealth() {
        const services = [
            { id: 'apiStatus', url: 'http://localhost:5000/health' },
            { id: 'mlStatus', url: 'http://localhost:5001/health' },
            { id: 'blockchainStatus', url: 'http://localhost:5002/health' }
        ];
        
        for (const service of services) {
            try {
                const response = await fetch(service.url);
                const element = document.getElementById(service.id);
                
                if (response.ok) {
                    element.textContent = 'Online';
                    element.className = 'badge bg-success';
                } else {
                    element.textContent = 'Error';
                    element.className = 'badge bg-danger';
                }
            } catch (error) {
                const element = document.getElementById(service.id);
                element.textContent = 'Offline';
                element.className = 'badge bg-danger';
            }
        }
        
        // Check again in 60 seconds
        setTimeout(() => this.checkSystemHealth(), 60000);
    }
    
    showAlert(alert) {
        // Show browser notification if supported
        if ('Notification' in window && Notification.permission === 'granted') {
            new Notification(`Transport Alert: ${alert.type}`, {
                body: alert.message,
                icon: '🚨'
            });
        }
    }
}

// Initialize dashboard when page loads
document.addEventListener('DOMContentLoaded', () => {
    // Request notification permission
    if ('Notification' in window && Notification.permission === 'default') {
        Notification.requestPermission();
    }
    
    // Create dashboard instance
    window.dashboard = new TransportDashboard();
    
    // Simulate some test data for demo
    setTimeout(() => {
        window.dashboard.simulateTestData();
    }, 2000);
});

// Add simulation method for testing
TransportDashboard.prototype.simulateTestData = function() {
    // Simulate vehicle telemetry
    const testVehicles = [
        { deviceId: 'OBU-001', lat: 20.2961, lon: 85.8245, speed: 45 },
        { deviceId: 'OBU-002', lat: 20.3000, lon: 85.8300, speed: 62 },
        { deviceId: 'OBU-003', lat: 20.2500, lon: 85.8100, speed: 38 }
    ];
    
    testVehicles.forEach((vehicle, index) => {
        setTimeout(() => {
            const telemetry = {
                deviceId: vehicle.deviceId,
                timestamp: new Date().toISOString(),
                location: { lat: vehicle.lat, lon: vehicle.lon },
                speedKmph: vehicle.speed,
                heading: Math.random() * 360,
                batteryVoltage: 12.1 + Math.random() * 0.5
            };
            
            this.updateVehiclePosition(telemetry);
        }, index * 1000);
    });
    
    // Simulate an event after 5 seconds
    setTimeout(() => {
        const event = {
            eventType: 'HARSH_BRAKE',
            deviceId: 'OBU-002',
            timestamp: new Date().toISOString(),
            location: { lat: 20.3000, lon: 85.8300 },
            speedBefore: 62,
            speedAfter: 25,
            accelPeak: -7.2
        };
        
        this.addEvent(event);
    }, 5000);
};