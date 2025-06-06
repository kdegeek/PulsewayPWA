<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Pulseway Dashboard</title>
    <link rel="manifest" href="/manifest.json">
    <meta name="theme-color" content="#0a0a0a">
    <link rel="apple-touch-icon" href="/icon-192.png">
    
    <style>
        :root {
            --primary-glow: #00f5ff;
            --secondary-glow: #ff00ff;
            --success-glow: #00ff88;
            --warning-glow: #ff8800;
            --error-glow: #ff0055;
            --bg-primary: #0a0a0a;
            --bg-glass: rgba(15, 15, 25, 0.8);
            --text-primary: #ffffff;
            --text-secondary: rgba(255, 255, 255, 0.7);
            --border-glow: rgba(255, 255, 255, 0.1);
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: var(--bg-primary);
            background-image: 
                radial-gradient(circle at 20% 80%, rgba(120, 119, 198, 0.3) 0%, transparent 50%),
                radial-gradient(circle at 80% 20%, rgba(255, 119, 198, 0.3) 0%, transparent 50%),
                radial-gradient(circle at 40% 40%, rgba(120, 200, 255, 0.3) 0%, transparent 50%);
            color: var(--text-primary);
            min-height: 100vh;
            overflow-x: hidden;
        }

        /* Glassmorphism Effect */
        .glass {
            background: var(--bg-glass);
            backdrop-filter: blur(20px);
            border: 1px solid var(--border-glow);
            border-radius: 16px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
            transition: all 0.3s ease;
        }

        .glass:hover {
            transform: translateY(-4px);
            box-shadow: 0 12px 40px rgba(0, 245, 255, 0.2);
            border: 1px solid rgba(0, 245, 255, 0.3);
        }

        /* Glow Text */
        .glow-text {
            text-shadow: 0 0 10px currentColor, 0 0 20px currentColor, 0 0 30px currentColor;
        }

        /* Header */
        .header {
            background: rgba(10, 10, 20, 0.9);
            backdrop-filter: blur(20px);
            padding: 1rem 2rem;
            position: sticky;
            top: 0;
            z-index: 100;
            display: flex;
            align-items: center;
            justify-content: space-between;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5);
        }

        .header-left {
            display: flex;
            align-items: center;
            gap: 1rem;
        }

        .header-right {
            display: flex;
            align-items: center;
            gap: 1rem;
        }

        .logo {
            color: var(--primary-glow);
            font-size: 1.5rem;
            font-weight: bold;
        }

        .badge {
            background: var(--error-glow);
            color: white;
            border-radius: 50%;
            padding: 0.25rem 0.5rem;
            font-size: 0.75rem;
            min-width: 1.5rem;
            text-align: center;
            position: absolute;
            top: -8px;
            right: -8px;
        }

        .icon-button {
            background: none;
            border: none;
            color: var(--text-primary);
            padding: 0.5rem;
            border-radius: 50%;
            cursor: pointer;
            transition: all 0.3s ease;
            position: relative;
        }

        .icon-button:hover {
            background: rgba(0, 245, 255, 0.1);
            color: var(--primary-glow);
        }

        /* Main Content */
        .main-content {
            padding: 2rem;
        }

        .grid {
            display: grid;
            gap: 1.5rem;
            margin-bottom: 2rem;
        }

        .grid-4 {
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
        }

        .grid-3 {
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
        }

        /* Stat Cards */
        .stat-card {
            padding: 1.5rem;
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            min-height: 140px;
        }

        .stat-content h3 {
            color: var(--text-secondary);
            font-size: 0.875rem;
            font-weight: normal;
            margin-bottom: 0.5rem;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .stat-value {
            font-size: 2.5rem;
            font-weight: bold;
            margin-bottom: 0.5rem;
        }

        .stat-subtitle {
            color: var(--text-secondary);
            font-size: 0.875rem;
        }

        .stat-icon {
            width: 60px;
            height: 60px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.5rem;
            border: 1px solid;
            box-shadow: 0 0 20px;
        }

        /* Progress Bars */
        .progress-container {
            margin: 1rem 0;
        }

        .progress-header {
            display: flex;
            justify-content: space-between;
            margin-bottom: 0.5rem;
        }

        .progress-bar {
            background: rgba(255, 255, 255, 0.1);
            height: 8px;
            border-radius: 4px;
            overflow: hidden;
        }

        .progress-fill {
            height: 100%;
            border-radius: 4px;
            transition: width 0.3s ease;
            box-shadow: 0 0 10px currentColor;
        }

        /* Alert List */
        .alert-list {
            padding: 1.5rem;
        }

        .alert-item {
            display: flex;
            align-items: center;
            gap: 1rem;
            padding: 1rem 0;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }

        .alert-item:last-child {
            border-bottom: none;
        }

        .alert-icon {
            width: 40px;
            height: 40px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.25rem;
        }

        .alert-content {
            flex: 1;
        }

        .alert-device {
            font-weight: bold;
            margin-bottom: 0.25rem;
        }

        .alert-message {
            color: var(--text-secondary);
            font-size: 0.875rem;
            margin-bottom: 0.25rem;
        }

        .alert-time {
            color: var(--text-secondary);
            font-size: 0.75rem;
        }

        .alert-badge {
            padding: 0.25rem 0.75rem;
            border-radius: 12px;
            font-size: 0.75rem;
            font-weight: bold;
            text-transform: uppercase;
            border: 1px solid;
        }

        /* Status Indicators */
        .status-online { color: var(--success-glow); }
        .status-offline { color: var(--error-glow); }
        .status-warning { color: var(--warning-glow); }
        .status-primary { color: var(--primary-glow); }

        /* Responsive Design */
        @media (max-width: 768px) {
            .header {
                padding: 1rem;
            }
            
            .main-content {
                padding: 1rem;
            }
            
            .grid-4, .grid-3 {
                grid-template-columns: 1fr;
            }
            
            .stat-card {
                flex-direction: column;
                gap: 1rem;
                text-align: center;
            }
        }

        /* Offline indicator */
        .offline-banner {
            background: var(--error-glow);
            color: white;
            padding: 0.5rem 1rem;
            text-align: center;
            font-size: 0.875rem;
            display: none;
        }

        .offline-banner.show {
            display: block;
        }

        /* Animations */
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }

        .pulse {
            animation: pulse 2s infinite;
        }

        /* Custom scrollbar */
        ::-webkit-scrollbar {
            width: 8px;
        }

        ::-webkit-scrollbar-track {
            background: rgba(255, 255, 255, 0.1);
        }

        ::-webkit-scrollbar-thumb {
            background: var(--primary-glow);
            border-radius: 4px;
        }

        ::-webkit-scrollbar-thumb:hover {
            background: var(--secondary-glow);
        }
    </style>
</head>
<body>
    <div class="offline-banner" id="offlineBanner">
        ⚠️ You are currently offline. Data may not be up to date.
    </div>

    <header class="header">
        <div class="header-left">
            <div class="logo glow-text">🛡️ Pulseway Dashboard</div>
        </div>
        <div class="header-right">
            <span class="status-primary" id="lastUpdate">Last updated: --:--:--</span>
            <button class="icon-button" id="notificationBtn">
                🔔
                <span class="badge" id="alertBadge">15</span>
            </button>
            <button class="icon-button" id="refreshBtn">🔄</button>
            <button class="icon-button">⚙️</button>
        </div>
    </header>

    <main class="main-content">
        <!-- Top Stats Grid -->
        <div class="grid grid-4">
            <div class="glass stat-card">
                <div class="stat-content">
                    <h3>Total Devices</h3>
                    <div class="stat-value glow-text status-primary" id="totalDevices">247</div>
                    <div class="stat-subtitle">94.7% agent coverage</div>
                </div>
                <div class="stat-icon status-primary" style="background: rgba(0, 245, 255, 0.2); border-color: var(--primary-glow); box-shadow: 0 0 20px rgba(0, 245, 255, 0.4);">
                    💻
                </div>
            </div>

            <div class="glass stat-card">
                <div class="stat-content">
                    <h3>Online Devices</h3>
                    <div class="stat-value glow-text status-online" id="onlineDevices">231</div>
                    <div class="stat-subtitle">16 offline</div>
                </div>
                <div class="stat-icon status-online" style="background: rgba(0, 255, 136, 0.2); border-color: var(--success-glow); box-shadow: 0 0 20px rgba(0, 255, 136, 0.4);">
                    ✅
                </div>
            </div>

            <div class="glass stat-card">
                <div class="stat-content">
                    <h3>Critical Alerts</h3>
                    <div class="stat-value glow-text status-offline pulse" id="criticalAlerts">3</div>
                    <div class="stat-subtitle">12 elevated</div>
                </div>
                <div class="stat-icon status-offline" style="background: rgba(255, 0, 85, 0.2); border-color: var(--error-glow); box-shadow: 0 0 20px rgba(255, 0, 85, 0.4);">
                    ⚠️
                </div>
            </div>

            <div class="glass stat-card">
                <div class="stat-content">
                    <h3>Avg CPU Usage</h3>
                    <div class="stat-value glow-text status-warning" id="avgCpu">23.4%</div>
                    <div class="stat-subtitle">Memory: 67.8%</div>
                </div>
                <div class="stat-icon status-warning" style="background: rgba(255, 136, 0, 0.2); border-color: var(--warning-glow); box-shadow: 0 0 20px rgba(255, 136, 0, 0.4);">
                    ⚡
                </div>
            </div>
        </div>

        <!-- Secondary Stats -->
        <div class="grid grid-3">
            <div class="glass">
                <div style="padding: 1.5rem;">
                    <h3 style="color: var(--primary-glow); margin-bottom: 1rem;">System Health</h3>
                    
                    <div class="progress-container">
                        <div class="progress-header">
                            <span>Device Availability</span>
                            <span class="status-online">93.5%</span>
                        </div>
                        <div class="progress-bar">
                            <div class="progress-fill status-online" style="width: 93.5%; background: var(--success-glow);"></div>
                        </div>
                    </div>

                    <div class="progress-container">
                        <div class="progress-header">
                            <span>Agent Coverage</span>
                            <span class="status-primary">94.7%</span>
                        </div>
                        <div class="progress-bar">
                            <div class="progress-fill status-primary" style="width: 94.7%; background: var(--primary-glow);"></div>
                        </div>
                    </div>
                </div>
            </div>

            <div class="glass">
                <div style="padding: 1.5rem;">
                    <h3 style="color: var(--primary-glow); margin-bottom: 1rem;">Organization Breakdown</h3>
                    
                    <div style="display: flex; justify-content: space-between; align-items: center; padding: 0.75rem 0; border-bottom: 1px solid rgba(255,255,255,0.1);">
                        <div>
                            <div style="font-weight: bold;">Main Office</div>
                            <div style="color: var(--text-secondary); font-size: 0.875rem;">145/156 devices online</div>
                        </div>
                        <div style="background: rgba(0, 255, 136, 0.2); color: var(--success-glow); padding: 0.25rem 0.75rem; border-radius: 12px; border: 1px solid var(--success-glow);">93%</div>
                    </div>
                    
                    <div style="display: flex; justify-content: space-between; align-items: center; padding: 0.75rem 0; border-bottom: 1px solid rgba(255,255,255,0.1);">
                        <div>
                            <div style="font-weight: bold;">Branch Office</div>
                            <div style="color: var(--text-secondary); font-size: 0.875rem;">62/67 devices online</div>
                        </div>
                        <div style="background: rgba(255, 136, 0, 0.2); color: var(--warning-glow); padding: 0.25rem 0.75rem; border-radius: 12px; border: 1px solid var(--warning-glow);">93%</div>
                    </div>
                    
                    <div style="display: flex; justify-content: space-between; align-items: center; padding: 0.75rem 0;">
                        <div>
                            <div style="font-weight: bold;">Remote Workers</div>
                            <div style="color: var(--text-secondary); font-size: 0.875rem;">24/24 devices online</div>
                        </div>
                        <div style="background: rgba(0, 255, 136, 0.2); color: var(--success-glow); padding: 0.25rem 0.75rem; border-radius: 12px; border: 1px solid var(--success-glow);">100%</div>
                    </div>
                </div>
            </div>

            <div class="glass">
                <div style="padding: 1.5rem;">
                    <h3 style="color: var(--primary-glow); margin-bottom: 1rem;">Top Devices by Alerts</h3>
                    
                    <div style="display: flex; align-items: center; gap: 1rem; padding: 0.5rem 0; border-bottom: 1px solid rgba(255,255,255,0.1);">
                        <div style="color: var(--error-glow); font-size: 1.25rem;">💻</div>
                        <div style="flex: 1;">
                            <div style="font-weight: bold;">SRV-WEB-01</div>
                            <div style="color: var(--text-secondary); font-size: 0.875rem;">8 alerts</div>
                        </div>
                    </div>
                    
                    <div style="display: flex; align-items: center; gap: 1rem; padding: 0.5rem 0; border-bottom: 1px solid rgba(255,255,255,0.1);">
                        <div style="color: var(--warning-glow); font-size: 1.25rem;">💻</div>
                        <div style="flex: 1;">
                            <div style="font-weight: bold;">WS-ADMIN-15</div>
                            <div style="color: var(--text-secondary); font-size: 0.875rem;">5 alerts</div>
                        </div>
                    </div>
                    
                    <div style="display: flex; align-items: center; gap: 1rem; padding: 0.5rem 0; border-bottom: 1px solid rgba(255,255,255,0.1);">
                        <div style="color: var(--warning-glow); font-size: 1.25rem;">💻</div>
                        <div style="flex: 1;">
                            <div style="font-weight: bold;">SRV-DB-02</div>
                            <div style="color: var(--text-secondary); font-size: 0.875rem;">3 alerts</div>
                        </div>
                    </div>
                    
                    <div style="display: flex; align-items: center; gap: 1rem; padding: 0.5rem 0;">
                        <div style="color: var(--primary-glow); font-size: 1.25rem;">💻</div>
                        <div style="flex: 1;">
                            <div style="font-weight: bold;">WS-DEV-08</div>
                            <div style="color: var(--text-secondary); font-size: 0.875rem;">2 alerts</div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Recent Alerts -->
        <div class="glass alert-list">
            <h3 style="color: var(--primary-glow); margin-bottom: 1rem;">Recent Alerts</h3>
            
            <div class="alert-item">
                <div class="alert-icon status-offline" style="background: rgba(255, 0, 85, 0.2);">⚠️</div>
                <div class="alert-content">
                    <div class="alert-device">SRV-WEB-01</div>
                    <div class="alert-message">High CPU usage detected</div>
                    <div class="alert-time">2 minutes ago</div>
                </div>
                <div class="alert-badge status-offline" style="background: rgba(255, 0, 85, 0.2); border-color: var(--error-glow); color: var(--error-glow);">Critical</div>
            </div>
            
            <div class="alert-item">
                <div class="alert-icon status-warning" style="background: rgba(255, 136, 0, 0.2);">⚠️</div>
                <div class="alert-content">
                    <div class="alert-device">WS-ADMIN-15</div>
                    <div class="alert-message">Low disk space warning</div>
                    <div class="alert-time">5 minutes ago</div>
                </div>
                <div class="alert-badge status-warning" style="background: rgba(255, 136, 0, 0.2); border-color: var(--warning-glow); color: var(--warning-glow);">Elevated</div>
            </div>
            
            <div class="alert-item">
                <div class="alert-icon status-warning" style="background: rgba(255, 136, 0, 0.2);">⚠️</div>
                <div class="alert-content">
                    <div class="alert-device">SRV-DB-02</div>
                    <div class="alert-message">Memory usage above threshold</div>
                    <div class="alert-time">12 minutes ago</div>
                </div>
                <div class="alert-badge status-warning" style="background: rgba(255, 136, 0, 0.2); border-color: var(--warning-glow); color: var(--warning-glow);">Elevated</div>
            </div>
            
            <div class="alert-item">
                <div class="alert-icon status-primary" style="background: rgba(0, 245, 255, 0.2);">ℹ️</div>
                <div class="alert-content">
                    <div class="alert-device">WS-DEV-08</div>
                    <div class="alert-message">Windows update required</div>
                    <div class="alert-time">18 minutes ago</div>
                </div>
                <div class="alert-badge status-primary" style="background: rgba(0, 245, 255, 0.2); border-color: var(--primary-glow); color: var(--primary-glow);">Normal</div>
            </div>
        </div>
    </main>

    <script>
        // PWA Registration
        if ('serviceWorker' in navigator) {
            navigator.serviceWorker.register('/sw.js')
                .then(registration => console.log('SW registered'))
                .catch(error => console.log('SW registration failed'));
        }

        // Real-time updates simulation
        function updateDashboard() {
            const now = new Date();
            document.getElementById('lastUpdate').textContent = `Last updated: ${now.toLocaleTimeString()}`;
            
            // Simulate data changes
            const totalDevices = Math.floor(Math.random() * 10) + 245;
            const onlineDevices = totalDevices - Math.floor(Math.random() * 20);
            const criticalAlerts = Math.floor(Math.random() * 5);
            
            document.getElementById('totalDevices').textContent = totalDevices;
            document.getElementById('onlineDevices').textContent = onlineDevices;
            document.getElementById('criticalAlerts').textContent = criticalAlerts;
            document.getElementById('alertBadge').textContent = criticalAlerts + Math.floor(Math.random() * 15);
        }

        // Online/Offline detection
        function handleOnlineStatus() {
            const offlineBanner = document.getElementById('offlineBanner');
            if (navigator.onLine) {
                offlineBanner.classList.remove('show');
            } else {
                offlineBanner.classList.add('show');
            }
        }

        // Event listeners
        window.addEventListener('online', handleOnlineStatus);
        window.addEventListener('offline', handleOnlineStatus);
        
        document.getElementById('refreshBtn').addEventListener('click', () => {
            updateDashboard();
            // Add loading animation
            document.getElementById('refreshBtn').style.animation = 'pulse 1s';
            setTimeout(() => {
                document.getElementById('refreshBtn').style.animation = '';
            }, 1000);
        });

        document.getElementById('notificationBtn').addEventListener('click', () => {
            // Request notification permission
            if ('Notification' in window && Notification.permission === 'default') {
                Notification.requestPermission();
            }
        });

        // Initialize
        updateDashboard();
        handleOnlineStatus();
        
        // Auto-refresh every 30 seconds
        setInterval(updateDashboard, 30000);

        // Request notification permission on load
        if ('Notification' in window && Notification.permission === 'default') {
            setTimeout(() => {
                Notification.requestPermission().then(permission => {
                    if (permission === 'granted') {
                        new Notification('Pulseway Dashboard', {
                            body: 'Push notifications enabled!',
                            icon: '/icon-192.png',
                            badge: '/icon-192.png'
                        });
                    }
                });
            }, 2000);
        }
    </script>
</body>
</html>