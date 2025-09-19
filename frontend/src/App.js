import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, PieChart, Pie, Cell, AreaChart, Area, BarChart, Bar } from 'recharts';
import { Car, Shield, AlertTriangle, Wallet, MapPin, Users, Zap, TrafficCone, DollarSign, Settings, Bell, Sun, Moon, LayoutDashboard, User as UserIcon, LogOut, ChevronRight, ArrowUp, ArrowDown, BatteryCharging, ChevronsUpDown, Siren, Search, Server, Database, Activity, Globe, BrainCircuit, UserPlus, Clock, Wifi } from 'lucide-react';
import axios from 'axios';

// API Configuration
const API_BASE = process.env.NODE_ENV === 'production' ? '/api/v1' : 'http://localhost:5000/api/v1';

// Mock data for demo purposes
const mockUsers = {
  'user@example.com': {
    name: 'Anjali Sharma',
    email: 'user@example.com',
    password: 'password123',
    role: 'user',
    vehicles: [101, 102],
  }
};

const mockAdmins = {
  'admin@example.com': {
    name: 'Admin',
    email: 'admin@example.com',
    password: 'admin123',
    role: 'admin',
  }
};

const mockVehicles = {
  101: {
    name: 'Tata Nexon EV',
    plate: 'OD 02 AB 1234',
    type: 'EV',
    owner: 'Anjali Sharma',
    driverScore: 88,
    walletBalance: 1250.75,
    lat: 20.354, 
    lng: 85.818,
    driverScoreHistory: [
      { name: 'Jan', score: 82 }, { name: 'Feb', score: 85 }, { name: 'Mar', score: 83 },
      { name: 'Apr', score: 88 }, { name: 'May', score: 90 }, { name: 'Jun', score: 88 },
    ],
  },
  102: {
    name: 'Hyundai Creta',
    plate: 'OD 01 C 5678',
    type: 'ICE',
    owner: 'Anjali Sharma',
    driverScore: 76,
    walletBalance: 875.50,
    lat: 20.27,
    lng: 85.82,
    driverScoreHistory: [
      { name: 'Jan', score: 75 }, { name: 'Feb', score: 72 }, { name: 'Mar', score: 78 },
      { name: 'Apr', score: 75 }, { name: 'May', score: 79 }, { name: 'Jun', score: 76 },
    ],
  }
};

// Helper Components
const Card = ({ children, className = '' }) => (
  <div className={`bg-white/50 dark:bg-gray-800/40 backdrop-blur-2xl rounded-2xl shadow-lg p-6 border border-white/20 dark:border-gray-700/50 transition-all duration-300 ${className}`}>
    {children}
  </div>
);

const AnimatedNumber = ({ value }) => {
  const [currentValue, setCurrentValue] = useState(0);
  useEffect(() => {
    const animation = requestAnimationFrame(() => setCurrentValue(value));
    return () => cancelAnimationFrame(animation);
  }, [value]);
  return <span style={{ transition: 'all 0.5s ease-out' }}>{Math.round(value)}</span>;
};

const StatCard = ({ icon, title, value, unit, color, trend }) => {
  const Icon = icon;
  return (
    <Card className="hover:-translate-y-1 hover:shadow-2xl">
      <div className="flex items-center">
        <div className={`p-3 rounded-full mr-4 ${color} shadow-lg`}>
          <Icon className="text-white" size={24} />
        </div>
        <div>
          <p className="text-sm text-gray-600 dark:text-gray-400 font-medium">{title}</p>
          <div className="flex items-baseline">
            <p className="text-2xl font-bold text-gray-800 dark:text-white">
              {typeof value === 'number' ? <AnimatedNumber value={value} /> : value}
              <span className="text-lg font-medium"> {unit}</span>
            </p>
            {trend && (trend === 'up' ? <ArrowUp size={16} className="ml-2 text-green-500"/> : <ArrowDown size={16} className="ml-2 text-red-500"/>)}
          </div>
        </div>
      </div>
    </Card>
  );
};

export default function App() {
  const [appStatus, setAppStatus] = useState('auth');
  const [auth, setAuth] = useState({ userType: null, currentUser: null });
  const [isDarkMode, setIsDarkMode] = useState(false);
  const [apiData, setApiData] = useState({});

  useEffect(() => {
    if (isDarkMode) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [isDarkMode]);

  // API Integration
  const fetchDashboardData = async () => {
    try {
      const response = await axios.get(`${API_BASE}/admin/dashboard`, {
        headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
      });
      setApiData(response.data);
    } catch (error) {
      console.error('API Error:', error);
    }
  };

  const handleLogin = async (email, password) => {
    try {
      const response = await axios.post(`${API_BASE}/auth/login`, { email, password });
      const { access_token, user } = response.data;
      
      localStorage.setItem('token', access_token);
      setAuth({ userType: user.role || 'user', currentUser: user });
      setAppStatus('show_welcome');
      return true;
    } catch (error) {
      // Fallback to mock data for demo
      const user = mockUsers[email];
      const admin = mockAdmins[email];

      if (user && user.password === password) {
        setAuth({ userType: 'user', currentUser: user });
        setAppStatus('show_welcome');
        return true;
      }
      if (admin && admin.password === password) {
        setAuth({ userType: 'admin', currentUser: admin });
        setAppStatus('show_welcome');
        return true;
      }
      return false;
    }
  };

  const handleSignup = async (name, email, password) => {
    try {
      const response = await axios.post(`${API_BASE}/auth/register`, { name, email, password });
      const { access_token, user } = response.data;
      
      localStorage.setItem('token', access_token);
      setAuth({ userType: 'user', currentUser: user });
      setAppStatus('show_welcome');
      return true;
    } catch (error) {
      // Fallback to mock data for demo
      if (mockUsers[email] || mockAdmins[email]) {
        return false;
      }
      const newUser = { name, email, password, role: 'user', vehicles: [] };
      mockUsers[email] = newUser;
      setAuth({ userType: 'user', currentUser: newUser });
      setAppStatus('show_welcome');
      return true;
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    setAppStatus('auth');
    setAuth({ userType: null, currentUser: null });
  };

  const handleWelcomeFinish = () => {
    setAppStatus('ready');
    if (auth.userType === 'admin') {
      fetchDashboardData();
    }
  };

  const toggleTheme = () => setIsDarkMode(!isDarkMode);

  const backgroundStyle = {
    backgroundSize: '30px 30px',
    backgroundImage: isDarkMode
      ? 'radial-gradient(circle, rgba(255, 255, 255, 0.05) 1px, transparent 1px)'
      : 'radial-gradient(circle, rgba(0, 0, 0, 0.05) 1px, transparent 1px)',
  };

  const renderApp = () => {
    switch(appStatus) {
      case 'auth':
        return <AuthPage onLogin={handleLogin} onSignup={handleSignup} />;
      case 'show_welcome':
        return <WelcomePage user={auth.currentUser} onFinish={handleWelcomeFinish} />;
      case 'ready':
        return auth.userType === 'user' 
          ? <UserApp isDarkMode={isDarkMode} onToggleTheme={toggleTheme} onLogout={handleLogout} user={auth.currentUser} /> 
          : <AdminDashboard isDarkMode={isDarkMode} onToggleTheme={toggleTheme} onLogout={handleLogout} apiData={apiData} />;
      default:
        return <AuthPage onLogin={handleLogin} onSignup={handleSignup} />;
    }
  };

  return (
    <div style={backgroundStyle} className="bg-gray-100 dark:bg-gray-900 min-h-screen text-gray-900 dark:text-gray-100 font-sans transition-colors duration-300">
      {renderApp()}
    </div>
  );
}

// Auth Components
const AuthPage = ({ onLogin, onSignup }) => {
  const [isLogin, setIsLogin] = useState(true);
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    const success = isLogin ? await onLogin(email, password) : await onSignup(name, email, password);
    if (!success) {
      setError(isLogin ? 'Invalid credentials.' : 'User already exists.');
    }
  };
  
  return (
    <div className="flex items-center justify-center min-h-screen w-full relative overflow-hidden bg-gray-900">
      <style>{`
        .road-line {
          position: absolute;
          height: 100%;
          width: 4px;
          background-image: linear-gradient(to bottom, rgba(255, 255, 255, 0.2) 50%, transparent 50%);
          background-size: 100% 50px;
          animation: move-lines 10s linear infinite;
        }
        @keyframes move-lines {
          from { background-position-y: 0; }
          to { background-position-y: -100px; }
        }
        .auth-card {
          animation: slide-up-fade-in 0.5s ease-out forwards;
        }
        @keyframes slide-up-fade-in {
          from { opacity: 0; transform: translateY(20px); }
          to { opacity: 1; transform: translateY(0); }
        }
      `}</style>
      <div className="road-line" style={{ left: '20%' }}></div>
      <div className="road-line" style={{ left: '80%', animationDuration: '15s' }}></div>

      <Card className="w-full max-w-md z-10 auth-card">
        <div className="flex items-center justify-center mb-6">
          <Shield size={40} className="text-indigo-600 dark:text-indigo-400"/>
          <h2 className="text-2xl font-bold ml-2 text-gray-800 dark:text-white">Smart Transport System</h2>
        </div>
        
        <div className="relative h-[300px] overflow-hidden">
          <form onSubmit={handleSubmit} className={`absolute top-0 left-0 w-full transition-transform duration-500 ease-in-out space-y-4 p-1 ${isLogin ? 'translate-x-0' : '-translate-x-full'}`}>
            <h3 className="text-xl font-bold text-center mb-4">Login</h3>
            <input type="email" value={email} onChange={e => setEmail(e.target.value)} placeholder="Email (user@example.com)" className="w-full p-3 rounded-lg bg-gray-100/50 dark:bg-gray-700/50 border-2 border-transparent focus:border-indigo-500 outline-none transition" required />
            <input type="password" value={password} onChange={e => setPassword(e.target.value)} placeholder="Password (password123)" className="w-full p-3 rounded-lg bg-gray-100/50 dark:bg-gray-700/50 border-2 border-transparent focus:border-indigo-500 outline-none transition" required />
            <button type="submit" className="w-full bg-indigo-600 text-white py-3 rounded-lg hover:bg-indigo-700 transition font-bold shadow-lg">Login</button>
            <p className="text-center text-sm">Don't have an account? <button type="button" onClick={() => setIsLogin(false)} className="font-semibold text-indigo-500">Sign Up</button></p>
          </form>
          
          <form onSubmit={handleSubmit} className={`absolute top-0 left-0 w-full transition-transform duration-500 ease-in-out space-y-4 p-1 ${isLogin ? 'translate-x-full' : 'translate-x-0'}`}>
            <h3 className="text-xl font-bold text-center mb-4">Sign Up</h3>
            <input type="text" value={name} onChange={e => setName(e.target.value)} placeholder="Full Name" className="w-full p-3 rounded-lg bg-gray-100/50 dark:bg-gray-700/50 border-2 border-transparent focus:border-indigo-500 outline-none transition" required />
            <input type="email" value={email} onChange={e => setEmail(e.target.value)} placeholder="Email" className="w-full p-3 rounded-lg bg-gray-100/50 dark:bg-gray-700/50 border-2 border-transparent focus:border-indigo-500 outline-none transition" required />
            <input type="password" value={password} onChange={e => setPassword(e.target.value)} placeholder="Password" className="w-full p-3 rounded-lg bg-gray-100/50 dark:bg-gray-700/50 border-2 border-transparent focus:border-indigo-500 outline-none transition" required />
            <button type="submit" className="w-full bg-indigo-600 text-white py-3 rounded-lg hover:bg-indigo-700 transition font-bold shadow-lg">Create Account</button>
            <p className="text-center text-sm">Already have an account? <button type="button" onClick={() => setIsLogin(true)} className="font-semibold text-indigo-500">Login</button></p>
          </form>
        </div>
        {error && <p className="text-red-500 text-sm text-center mt-2">{error}</p>}
      </Card>
    </div>
  );
};

const WelcomePage = ({ user, onFinish }) => {
  useEffect(() => {
    const timer = setTimeout(onFinish, 2500);
    return () => clearTimeout(timer);
  }, [onFinish]);
  
  return (
    <div className="flex flex-col items-center justify-center h-screen w-full bg-indigo-50 dark:bg-indigo-900/50 overflow-hidden">
      <style>{`
        .car-silhouette {
          width: 200px;
          height: auto;
          fill: #4f46e5;
          animation: drive-in 2.5s ease-out forwards;
        }
        @keyframes drive-in {
          0% { transform: translateX(-150vw); }
          30% { transform: translateX(0); }
          70% { transform: translateX(0); }
          100% { transform: translateX(150vw); }
        }
        .welcome-text {
          animation: text-fade 2.5s ease-out forwards;
        }
        @keyframes text-fade {
          0% { opacity: 0; transform: translateY(20px); }
          40% { opacity: 1; transform: translateY(0); }
          70% { opacity: 1; transform: translateY(0); }
          100% { opacity: 0; transform: translateY(-20px);}
        }
      `}</style>
      <div className="welcome-text">
        <h1 className="text-4xl md:text-6xl font-bold text-indigo-800 dark:text-white">
          Welcome, {user.name}!
        </h1>
        <p className="text-lg text-center text-indigo-600 dark:text-indigo-300 mt-4">
          Redirecting to your dashboard...
        </p>
      </div>
      <svg className="car-silhouette absolute bottom-1/4" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
        <path d="M5.5,21 C6.32842712,21 7,20.3284271 7,19.5 C7,18.6715729 6.32842712,18 5.5,18 C4.67157288,18 4,18.6715729 4,19.5 C4,20.3284271 4.67157288,21 5.5,21 Z M18.5,21 C19.3284271,21 20,20.3284271 20,19.5 C20,18.6715729 19.3284271,18 18.5,18 C17.6715729,18 17,18.6715729 17,19.5 C17,20.3284271 17.6715729,21 18.5,21 Z"/>
      </svg>
    </div>
  );
};

// User App Components will be in separate files for better organization
const UserApp = ({ isDarkMode, onToggleTheme, onLogout, user }) => {
  const [activePage, setActivePage] = useState('Dashboard');
  const [selectedVehicleId, setSelectedVehicleId] = useState(user.vehicles.length > 0 ? user.vehicles[0] : null);

  return (
    <div className="h-screen relative">
      <div className="md:flex h-full w-full">
        <UserSidebar activePage={activePage} setActivePage={setActivePage} isDarkMode={isDarkMode} onToggleTheme={onToggleTheme} onLogout={onLogout} />
        <main className="flex-1 p-4 md:p-8 overflow-y-auto pb-24 md:pb-8 flex flex-col">
          <UserHeader title={activePage} vehicles={mockVehicles} selectedVehicleId={selectedVehicleId} onSelectVehicle={setSelectedVehicleId} user={user} />
          <div className="flex-grow">
            {activePage === 'Dashboard' && <DashboardPage selectedVehicle={mockVehicles[selectedVehicleId]} user={user} />}
            {activePage === 'Map' && <MapPage />}
            {activePage === 'Wallet' && <WalletPage selectedVehicle={mockVehicles[selectedVehicleId]} />}
            {activePage === 'Safety' && <SafetyPage selectedVehicle={mockVehicles[selectedVehicleId]} />}
            {activePage === 'Profile' && <ProfilePage vehicles={mockVehicles} selectedVehicleId={selectedVehicleId} user={user} />}
          </div>
        </main>
        <UserNavbar activePage={activePage} setActivePage={setActivePage} />
      </div>
    </div>
  );
};

// Placeholder components - will be implemented in separate files
const UserSidebar = ({ activePage, setActivePage, isDarkMode, onToggleTheme, onLogout }) => (
  <div className="hidden md:flex flex-col w-64 p-4 bg-white/40 dark:bg-gray-800/30 backdrop-blur-xl border-r border-white/20 dark:border-gray-700/50 flex-shrink-0">
    <div className="flex items-center mb-10 pl-2">
      <Shield size={32} className="text-indigo-600 dark:text-indigo-400"/>
      <h2 className="text-xl font-bold ml-2 text-gray-800 dark:text-white">Smart Transport</h2>
    </div>
    <nav className="flex-grow">
      {['Dashboard', 'Map', 'Wallet', 'Safety', 'Profile'].map(item => (
        <button key={item} onClick={() => setActivePage(item)}
          className={`w-full flex items-center p-3 my-1 rounded-lg text-left transition-all duration-300 ${activePage === item ? 'bg-indigo-600 text-white shadow-lg' : 'text-gray-600 dark:text-gray-300 hover:bg-black/5 dark:hover:bg-white/5'}`}>
          <span className="ml-4 font-semibold">{item}</span>
        </button>
      ))}
    </nav>
  </div>
);

const UserHeader = ({ title, user }) => (
  <div className="flex justify-between items-center mb-6">
    <h1 className="text-3xl font-bold text-gray-800 dark:text-white hidden md:block">{title}</h1>
    <div className="flex items-center space-x-4">
      <Bell size={24} className="text-gray-600 dark:text-gray-300" />
      <img src={`https://i.pravatar.cc/150?u=${user.name}`} alt="User" className="w-12 h-12 rounded-full ring-2 ring-indigo-300 dark:ring-indigo-500" />
    </div>
  </div>
);

const UserNavbar = ({ activePage, setActivePage }) => (
  <div className="fixed bottom-0 left-0 right-0 bg-white/60 dark:bg-gray-800/60 backdrop-blur-xl shadow-lg border-t border-white/20 dark:border-gray-700/50 md:hidden">
    <div className="flex justify-around items-center max-w-xl mx-auto p-2">
      {['Dashboard', 'Map', 'Wallet', 'Safety', 'Profile'].map(item => (
        <button key={item} onClick={() => setActivePage(item)}
          className={`flex flex-col items-center justify-center w-16 h-16 rounded-xl transition-all duration-300 ${activePage === item ? 'text-indigo-600 dark:text-indigo-400' : 'text-gray-500 dark:text-gray-400'}`}>
          <span className="text-xs font-bold mt-1">{item}</span>
        </button>
      ))}
    </div>
  </div>
);

// Page Components
const DashboardPage = ({ selectedVehicle, user }) => (
  <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
    <div className="lg:col-span-2 space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <StatCard icon={Car} title="Current Speed" value={68} unit="km/h" color="bg-blue-500" />
        <StatCard icon={MapPin} title="Trip Distance" value={128.5} unit="km" color="bg-purple-500" />
        <StatCard icon={Zap} title="EV Charge" value={80} unit="%" color="bg-teal-500" />
      </div>
    </div>
    <div className="space-y-6">
      <Card className="flex flex-col items-center justify-center text-center">
        <h2 className="text-xl font-bold mb-2 text-gray-800 dark:text-white">Driver Score</h2>
        <div className="text-6xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-green-400 to-emerald-600">{selectedVehicle?.driverScore || 88}</div>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-2">Excellent</p>
      </Card>
    </div>
  </div>
);

const MapPage = () => (
  <Card className="h-[75vh] flex flex-col">
    <div className="flex-grow bg-gray-200 dark:bg-gray-700 rounded-lg overflow-hidden relative">
      <img src="https://i.imgur.com/gAY933g.png" className="w-full h-full object-cover" alt="Map" />
    </div>
  </Card>
);

const WalletPage = ({ selectedVehicle }) => (
  <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
    <Card>
      <p className="text-sm text-gray-500 dark:text-gray-400">Current Balance</p>
      <p className="text-5xl font-bold text-indigo-600 dark:text-indigo-400 my-2">₹{selectedVehicle?.walletBalance?.toFixed(2) || '1250.75'}</p>
      <button className="w-full bg-indigo-600 text-white py-3 rounded-lg hover:bg-indigo-700 transition shadow-lg">Add Funds</button>
    </Card>
  </div>
);

const SafetyPage = ({ selectedVehicle }) => (
  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
    <Card className="flex flex-col items-center justify-center">
      <h2 className="text-xl font-bold mb-2">Driver Score</h2>
      <div className="text-4xl font-bold">{selectedVehicle?.driverScore || 88}</div>
    </Card>
  </div>
);

const ProfilePage = ({ user }) => (
  <div className="max-w-2xl mx-auto">
    <Card>
      <div className="flex items-center pb-6 border-b border-gray-200 dark:border-gray-700/50">
        <img src={`https://i.pravatar.cc/150?u=${user.name}`} alt="User" className="w-20 h-20 rounded-full" />
        <div className="ml-6">
          <h2 className="text-2xl font-bold">{user.name}</h2>
          <p className="text-gray-500 dark:text-gray-400">{user.email}</p>
        </div>
      </div>
    </Card>
  </div>
);

// Admin Dashboard
const AdminDashboard = ({ isDarkMode, onToggleTheme, onLogout, apiData }) => {
  const [activeView, setActiveView] = useState('Overview');

  return (
    <div className="flex h-screen">
      <AdminSidebar activeView={activeView} setActiveView={setActiveView} onLogout={onLogout} />
      <main className="flex-1 flex flex-col overflow-hidden">
        <AdminHeader onToggleTheme={onToggleTheme} isDarkMode={isDarkMode} />
        <div className="flex-1 overflow-y-auto">
          <AdminOverview apiData={apiData} />
        </div>
      </main>
    </div>
  );
};

const AdminSidebar = ({ activeView, setActiveView, onLogout }) => (
  <div className="w-64 bg-white/40 dark:bg-gray-800/30 p-4 flex-col hidden md:flex backdrop-blur-xl border-r border-white/20 dark:border-gray-700/50 flex-shrink-0">
    <div className="flex items-center mb-8 pl-2">
      <Shield size={32} className="text-indigo-600 dark:text-indigo-400"/>
      <h2 className="text-xl font-bold ml-2 text-gray-800 dark:text-white">Smart Transport</h2>
    </div>
    <nav className="flex-grow">
      {['Overview', 'Incidents', 'Tolling', 'System Health'].map(item => (
        <button key={item} onClick={() => setActiveView(item)}
          className={`w-full flex items-center p-3 my-1 rounded-lg transition-colors ${activeView === item ? 'bg-indigo-600 text-white shadow-lg' : 'text-gray-600 dark:text-gray-300 hover:bg-black/5 dark:hover:bg-white/5'}`}>
          <span className="ml-4 font-medium">{item}</span>
        </button>
      ))}
    </nav>
  </div>
);

const AdminHeader = ({ onToggleTheme, isDarkMode }) => (
  <div className="flex justify-between items-center p-6 bg-white/40 dark:bg-gray-800/30 backdrop-blur-xl border-b border-white/20 dark:border-gray-700/50">
    <h1 className="text-2xl font-bold text-gray-800 dark:text-white">Admin Dashboard</h1>
    <div className="flex items-center space-x-4">
      <button onClick={onToggleTheme} className="p-2 rounded-full bg-black/5 dark:bg-white/10 text-gray-600 dark:text-gray-300">
        {isDarkMode ? <Sun size={20} /> : <Moon size={20} />}
      </button>
      <Bell size={24} className="text-gray-600 dark:text-gray-300" />
      <img src="https://i.pravatar.cc/150?u=admin" alt="Admin" className="w-10 h-10 rounded-full" />
    </div>
  </div>
);

const AdminOverview = ({ apiData }) => (
  <div className="p-6 space-y-6">
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
      <StatCard icon={DollarSign} title="Daily Revenue" value="₹5.4M" unit="" color="bg-green-500" />
      <StatCard icon={Car} title="Vehicles Online" value={18765} unit="" color="bg-blue-500" />
      <StatCard icon={AlertTriangle} title="Active Incidents" value={4} unit="" color="bg-red-500" />
      <StatCard icon={Zap} title="Avg Network Speed" value={62} unit="km/h" color="bg-purple-500" />
    </div>
    <Card>
      <h3 className="text-lg font-semibold mb-4">System Status</h3>
      <p>All systems operational. Real-time data from {apiData?.active_devices?.length || 0} devices.</p>
    </Card>
  </div>
);