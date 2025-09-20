// Smart Transportation Dashboard - Real-time Updates
class TransportDashboard {
    constructor() {
        this.map = null;
        this.socket = null;
        this.vehicles = new Map();
        this.markers = new Map();
        this.events = [];
        this.tollEvents = [];
        this.metrics = {
            activeVehicles: 0,
            dailyRevenue: 0,
            activeAlerts: 0,
            avgScore: 0
        };
        
        this.init();
    }
    
    init() {
        this.initMap();
        this.initWebSocket();
        this.initEventHandlers();
        this.checkSystemHealth();
    }
    
    initMap() {
        // Initialize Leaflet map
        this.map = L.map('map').setView([20.2961, 85.8245], 13);
        
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors'
        }).addTo(this.map);
        
        // Add toll gantry markers
        this.addTollGantries();
    }
    
    addTollGantries() {
        const gantries = [
            { id: 1, lat: 20.2961, lon: 85.8245, name: "Gantry 1" },
            { id: 2, lat: 20.3000, lon: 85.8300, name: "Gantry 2" },
            { id: 3, lat: 20.2900, lon: 85.8200, name: "Gantry 3" }
        ];
        
        gantries.forEach(gantry => {
            const marker = L.marker([gantry.lat, gantry.lon], {
                icon: L.divIcon({
                    className: 'toll-gantry',
                    html: '🏛️',
                    iconSize: [20, 20]
                })
            }).addTo(this.map);
            
            marker.bindPopup(`<b>${gantry.name}</b><br>Toll Collection Point`);
        });
    }
    
    initWebSocket() {
        // Connect to WebSocket server
        this.socket = io('http://localhost:5003');
        
        this.socket.on('connect', () => {
            console.log('Connected to WebSocket server');
            this.updateConnectionStatus(true);
        });
        
        this.socket.on('disconnect', () => {
            console.log('Disconnected from WebSocket server');
            this.updateConnectionStatus(false);
        });
        
        this.socket.on('telemetry_update', (data) => {
            this.handleTelemetryUpdate(data);
        });
        
        this.socket.on('event_update', (data) => {
            this.handleEventUpdate(data);
        });
        
        this.socket.on('toll_update', (data) => {
            this.handleTollUpdate(data);
        });
    }
    
    handleTelemetryUpdate(data) {
        const deviceId = data.deviceId;
        const location = data.location;
        
        // Update vehicle data
        this.vehicles.set(deviceId, {
            ...data,
            lastSeen: new Date()
        });
        
        // Update or create marker
        if (this.markers.has(deviceId)) {
            const marker = this.markers.get(deviceId);
            marker.setLatLng([location.lat, location.lon]);
            
            // Update popup content
            const popupContent = this.createVehiclePopup(data);
            marker.setPopupContent(popupContent);
        } else {
            // Create new marker
            const marker = L.marker([location.lat, location.lon], {
                icon: L.divIcon({
                    className: 'vehicle-marker',
                    html: '🚗',
                    iconSize: [20, 20]
                })
            }).addTo(this.map);
            
            const popupContent = this.createVehiclePopup(data);
            marker.bindPopup(popupContent);
            
            this.markers.set(deviceId, marker);
        }
        
        this.updateMetrics();
        this.updateVehiclesList();
    }
    
    handleEventUpdate(data) {
        // Add to events list
        this.events.unshift(data);
        if (this.events.length > 50) {
            this.events = this.events.slice(0, 50);
        }
        
        // Show event marker temporarily
        this.showEventMarker(data);
        
        this.updateEventsList();
        this.updateMetrics();
    }
    
    handleTollUpdate(data) {
        // Add to toll events
        this.tollEvents.unshift(data);
        if (this.tollEvents.length > 100) {
            this.tollEvents = this.tollEvents.slice(0, 100);
        }
        
        // Show toll animation
        this.showTollAnimation(data);
        
        this.updateMetrics();
    }
    
    createVehiclePopup(data) {
        return `
            <div>
                <b>Vehicle: ${data.deviceId}</b><br>
                <b>Speed:</b> ${data.speedKmph.toFixed(1)} km/h<br>
                <b>Heading:</b> ${data.heading?.toFixed(0) || 'N/A'}°<br>
                <b>Last Update:</b> ${new Date(data.timestamp).toLocaleTimeString()}
            </div>
        `;
    }
    
    showEventMarker(event) {
        if (!event.location) return;
        
        const marker = L.marker([event.location.lat, event.location.lon], {
            icon: L.divIcon({
                className: 'event-marker',
                html: '⚠️',
                iconSize: [25, 25]
            })
        }).addTo(this.map);
        
        marker.bindPopup(`
            <div>
                <b>Event: ${event.eventType}</b><br>
                <b>Device:</b> ${event.deviceId}<br>
                <b>Severity:</b> ${event.severity}<br>
                <b>Time:</b> ${new Date(event.timestamp).toLocaleTimeString()}
            </div>
        `);
        
        // Remove marker after 30 seconds
        setTimeout(() => {
            this.map.removeLayer(marker);
        }, 30000);
    }
    
    showTollAnimation(toll) {
        // Find gantry location (mock)
        const gantryLocations = {
            1: [20.2961, 85.8245],
            2: [20.3000, 85.8300],
            3: [20.2900, 85.8200]
        };
        
        const location = gantryLocations[toll.gantryId];
        if (!location) return;
        
        // Create temporary animation marker
        const marker = L.marker(location, {
            icon: L.divIcon({
                className: 'toll-animation',
                html: '💰',
                iconSize: [30, 30]
            })
        }).addTo(this.map);
        
        marker.bindPopup(`
            <div>
                <b>Toll Charged</b><br>
                <b>Vehicle:</b> ${toll.deviceId}<br>
                <b>Amount:</b> $${toll.amount.toFixed(2)}<br>
                <b>Status:</b> ${toll.paid ? 'Paid' : 'Pending'}<br>
                <b>TX Hash:</b> ${toll.txHash?.substring(0, 10)}...
            </div>
        `);
        
        // Remove after 10 seconds
        setTimeout(() => {
            this.map.removeLayer(marker);
        }, 10000);
    }
    
    updateMetrics() {
        // Active vehicles (seen in last 5 minutes)
        const now = new Date();
        const activeVehicles = Array.from(this.vehicles.values()).filter(
            vehicle => (now - vehicle.lastSeen) < 5 * 60 * 1000
        ).length;
        
        // Daily revenue from toll events
        const today = new Date().toDateString();
        const dailyRevenue = this.tollEvents
            .filter(toll => new Date(toll.timestamp).toDateString() === today)
            .reduce((sum, toll) => sum + toll.amount, 0);
        
        // Active alerts (events in last hour)
        const oneHourAgo = new Date(now - 60 * 60 * 1000);
        const activeAlerts = this.events.filter(
            event => new Date(event.timestamp) > oneHourAgo
        ).length;
        
        // Mock average score
        const avgScore = 75 + Math.random() * 20;
        
        // Update UI
        document.getElementById('activeVehicles').textContent = activeVehicles;
        document.getElementById('dailyRevenue').textContent = `$${dailyRevenue.toFixed(2)}`;
        document.getElementById('activeAlerts').textContent = activeAlerts;
        document.getElementById('avgScore').textContent = avgScore.toFixed(0);
    }
    
    updateVehiclesList() {
        const vehiclesList = document.getElementById('vehiclesList');
        const vehicles = Array.from(this.vehicles.values())
            .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))
            .slice(0, 10);
        
        if (vehicles.length === 0) {
            vehiclesList.innerHTML = '<div class="list-group-item text-muted text-center">No vehicles online</div>';
            return;
        }
        
        vehiclesList.innerHTML = vehicles.map(vehicle => `
            <div class="list-group-item d-flex justify-content-between align-items-center">
                <div>
                    <strong>${vehicle.deviceId}</strong><br>
                    <small class="text-muted">${vehicle.speedKmph.toFixed(1)} km/h</small>
                </div>
                <span class="badge bg-success">Online</span>
            </div>
        `).join('');
    }
    
    updateEventsList() {
        const eventsList = document.getElementById('eventsList');
        const recentEvents = this.events.slice(0, 10);
        
        if (recentEvents.length === 0) {
            eventsList.innerHTML = '<div class="list-group-item text-muted text-center">No events</div>';
            return;
        }
        
        eventsList.innerHTML = recentEvents.map(event => {
            const severityClass = {
                'HIGH': 'danger',
                'MEDIUM': 'warning',
                'LOW': 'info'
            }[event.severity] || 'secondary';
            
            return `
                <div class="list-group-item">
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <strong>${event.eventType}</strong><br>
                            <small class="text-muted">${event.deviceId}</small>
                        </div>
                        <span class="badge bg-${severityClass}">${event.severity}</span>
                    </div>
                    <small class="text-muted">${new Date(event.timestamp).toLocaleTimeString()}</small>
                </div>
            `;
        }).join('');
    }
    
    updateConnectionStatus(connected) {
        const statusElement = document.getElementById('connectionStatus');
        if (connected) {
            statusElement.innerHTML = '<span class="status-online">● Connected</span>';
        } else {
            statusElement.innerHTML = '<span class="status-offline">● Disconnected</span>';
        }
    }
    
    async checkSystemHealth() {
        const services = [
            { name: 'API Server', url: 'http://localhost:5000/health', element: 'apiStatus' },
            { name: 'ML Service', url: 'http://localhost:5001/health', element: 'mlStatus' },
            { name: 'Blockchain', url: 'http://localhost:5002/health', element: 'blockchainStatus' }
        ];
        
        for (const service of services) {
            try {
                const response = await fetch(service.url);
                const element = document.getElementById(service.element);
                
                if (response.ok) {
                    element.textContent = 'Online';
                    element.className = 'badge bg-success';
                } else {
                    element.textContent = 'Error';
                    element.className = 'badge bg-danger';
                }
            } catch (error) {
                const element = document.getElementById(service.element);
                element.textContent = 'Offline';
                element.className = 'badge bg-danger';
            }
        }
        
        // Check again in 30 seconds
        setTimeout(() => this.checkSystemHealth(), 30000);
    }
    
    initEventHandlers() {
        // Add any additional event handlers here
        console.log('Dashboard initialized');
    }
}

// Initialize dashboard when page loads
document.addEventListener('DOMContentLoaded', () => {
    new TransportDashboard();
});