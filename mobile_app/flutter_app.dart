// Flutter Mobile App - Driver Dashboard
// File: lib/main.dart

import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'dart:async';

void main() {
  runApp(TransportApp());
}

class TransportApp extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Smart Transport',
      theme: ThemeData(
        primarySwatch: Colors.blue,
        visualDensity: VisualDensity.adaptivePlatformDensity,
      ),
      home: LoginScreen(),
    );
  }
}

class LoginScreen extends StatefulWidget {
  @override
  _LoginScreenState createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();
  bool _isLoading = false;

  Future<void> _login() async {
    setState(() => _isLoading = true);
    
    try {
      final response = await http.post(
        Uri.parse('http://localhost:5000/api/v1/auth/login'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({
          'email': _emailController.text,
          'password': _passwordController.text,
        }),
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        Navigator.pushReplacement(
          context,
          MaterialPageRoute(
            builder: (context) => DashboardScreen(
              token: data['access_token'],
              user: data['user'],
            ),
          ),
        );
      } else {
        _showError('Login failed');
      }
    } catch (e) {
      _showError('Network error');
    } finally {
      setState(() => _isLoading = false);
    }
  }

  void _showError(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(message)),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('Smart Transport Login')),
      body: Padding(
        padding: EdgeInsets.all(16.0),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            TextField(
              controller: _emailController,
              decoration: InputDecoration(labelText: 'Email'),
              keyboardType: TextInputType.emailAddress,
            ),
            SizedBox(height: 16),
            TextField(
              controller: _passwordController,
              decoration: InputDecoration(labelText: 'Password'),
              obscureText: true,
            ),
            SizedBox(height: 24),
            _isLoading
                ? CircularProgressIndicator()
                : ElevatedButton(
                    onPressed: _login,
                    child: Text('Login'),
                  ),
          ],
        ),
      ),
    );
  }
}

class DashboardScreen extends StatefulWidget {
  final String token;
  final Map<String, dynamic> user;

  DashboardScreen({required this.token, required this.user});

  @override
  _DashboardScreenState createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  List<dynamic> vehicles = [];
  Map<String, dynamic>? selectedVehicle;
  Map<String, dynamic>? driverScore;
  List<dynamic> transactions = [];
  Timer? _refreshTimer;

  @override
  void initState() {
    super.initState();
    _loadVehicles();
    _startAutoRefresh();
  }

  @override
  void dispose() {
    _refreshTimer?.cancel();
    super.dispose();
  }

  void _startAutoRefresh() {
    _refreshTimer = Timer.periodic(Duration(seconds: 30), (timer) {
      if (selectedVehicle != null) {
        _loadDriverScore();
        _loadTransactions();
      }
    });
  }

  Future<void> _loadVehicles() async {
    try {
      final response = await http.get(
        Uri.parse('http://localhost:5000/api/v1/vehicles'),
        headers: {'Authorization': 'Bearer ${widget.token}'},
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        setState(() {
          vehicles = data['vehicles'];
          if (vehicles.isNotEmpty) {
            selectedVehicle = vehicles[0];
            _loadDriverScore();
            _loadTransactions();
          }
        });
      }
    } catch (e) {
      print('Error loading vehicles: $e');
    }
  }

  Future<void> _loadDriverScore() async {
    if (selectedVehicle == null) return;

    try {
      final response = await http.get(
        Uri.parse('http://localhost:5000/api/v1/vehicles/${selectedVehicle!['vehicle_id']}/score'),
        headers: {'Authorization': 'Bearer ${widget.token}'},
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        setState(() {
          driverScore = data['current_score'];
        });
      }
    } catch (e) {
      print('Error loading driver score: $e');
    }
  }

  Future<void> _loadTransactions() async {
    if (selectedVehicle == null) return;

    try {
      final response = await http.get(
        Uri.parse('http://localhost:5000/api/v1/vehicles/${selectedVehicle!['vehicle_id']}/transactions'),
        headers: {'Authorization': 'Bearer ${widget.token}'},
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        setState(() {
          transactions = data['transactions'];
        });
      }
    } catch (e) {
      print('Error loading transactions: $e');
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('Driver Dashboard'),
        actions: [
          IconButton(
            icon: Icon(Icons.refresh),
            onPressed: () {
              _loadDriverScore();
              _loadTransactions();
            },
          ),
        ],
      ),
      body: vehicles.isEmpty
          ? Center(child: CircularProgressIndicator())
          : SingleChildScrollView(
              padding: EdgeInsets.all(16.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _buildVehicleSelector(),
                  SizedBox(height: 20),
                  _buildDriverScoreCard(),
                  SizedBox(height: 20),
                  _buildWalletCard(),
                  SizedBox(height: 20),
                  _buildTransactionsList(),
                ],
              ),
            ),
    );
  }

  Widget _buildVehicleSelector() {
    return Card(
      child: Padding(
        padding: EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Select Vehicle', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
            SizedBox(height: 8),
            DropdownButton<Map<String, dynamic>>(
              value: selectedVehicle,
              isExpanded: true,
              items: vehicles.map((vehicle) {
                return DropdownMenuItem(
                  value: vehicle,
                  child: Text('${vehicle['registration_no']} (${vehicle['obu_device_id']})'),
                );
              }).toList(),
              onChanged: (vehicle) {
                setState(() {
                  selectedVehicle = vehicle;
                });
                _loadDriverScore();
                _loadTransactions();
              },
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildDriverScoreCard() {
    return Card(
      child: Padding(
        padding: EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Driver Score', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
            SizedBox(height: 16),
            if (driverScore != null) ...[
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text('Score:', style: TextStyle(fontSize: 16)),
                  Container(
                    padding: EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                    decoration: BoxDecoration(
                      color: _getScoreColor(driverScore!['driver_score'] ?? 0.5),
                      borderRadius: BorderRadius.circular(20),
                    ),
                    child: Text(
                      '${((driverScore!['driver_score'] ?? 0.5) * 100).toInt()}/100',
                      style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold),
                    ),
                  ),
                ],
              ),
              SizedBox(height: 8),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text('Confidence:', style: TextStyle(fontSize: 16)),
                  Text('${((driverScore!['confidence'] ?? 0.8) * 100).toInt()}%'),
                ],
              ),
            ] else
              Text('Loading score...'),
          ],
        ),
      ),
    );
  }

  Widget _buildWalletCard() {
    return Card(
      child: Padding(
        padding: EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Wallet Balance', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
            SizedBox(height: 16),
            if (selectedVehicle != null) ...[
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text('Balance:', style: TextStyle(fontSize: 16)),
                  Text(
                    '\$${selectedVehicle!['balance']?.toStringAsFixed(2) ?? '0.00'}',
                    style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: Colors.green),
                  ),
                ],
              ),
              SizedBox(height: 8),
              Text(
                'Wallet: ${selectedVehicle!['wallet_address'] ?? 'N/A'}',
                style: TextStyle(fontSize: 12, color: Colors.grey),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildTransactionsList() {
    return Card(
      child: Padding(
        padding: EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Recent Transactions', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
            SizedBox(height: 16),
            if (transactions.isEmpty)
              Text('No transactions found')
            else
              ListView.builder(
                shrinkWrap: true,
                physics: NeverScrollableScrollPhysics(),
                itemCount: transactions.length,
                itemBuilder: (context, index) {
                  final transaction = transactions[index];
                  return ListTile(
                    leading: Icon(Icons.toll, color: Colors.blue),
                    title: Text('Toll Payment'),
                    subtitle: Text('${transaction['gantry_name'] ?? 'Unknown Gantry'}'),
                    trailing: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      crossAxisAlignment: CrossAxisAlignment.end,
                      children: [
                        Text(
                          '\$${transaction['price']?.toStringAsFixed(2) ?? '0.00'}',
                          style: TextStyle(fontWeight: FontWeight.bold),
                        ),
                        Text(
                          transaction['status'] ?? 'pending',
                          style: TextStyle(
                            fontSize: 12,
                            color: transaction['status'] == 'completed' ? Colors.green : Colors.orange,
                          ),
                        ),
                      ],
                    ),
                  );
                },
              ),
          ],
        ),
      ),
    );
  }

  Color _getScoreColor(double score) {
    if (score >= 0.8) return Colors.green;
    if (score >= 0.6) return Colors.orange;
    return Colors.red;
  }
}