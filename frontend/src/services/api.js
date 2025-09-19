import axios from 'axios';

const API_BASE_URL = process.env.NODE_ENV === 'production' ? '/api/v1' : 'http://localhost:5000/api/v1';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
});

api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

export const authAPI = {
  login: async (email, password) => {
    const response = await api.post('/auth/login', { email, password });
    return response.data;
  },
  
  register: async (name, email, password) => {
    const response = await api.post('/auth/register', { name, email, password });
    return response.data;
  }
};

export const vehicleAPI = {
  getVehicles: async () => {
    const response = await api.get('/vehicles');
    return response.data;
  },
  
  getDriverScore: async (vehicleId) => {
    const response = await api.get(`/vehicles/${vehicleId}/score`);
    return response.data;
  }
};

export const adminAPI = {
  getDashboardData: async () => {
    const response = await api.get('/admin/dashboard');
    return response.data;
  }
};

export default api;