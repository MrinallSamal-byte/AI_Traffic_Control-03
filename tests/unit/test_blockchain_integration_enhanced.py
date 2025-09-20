#!/usr/bin/env python3
"""
Enhanced unit tests for blockchain integration
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add blockchain to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'blockchain'))

from blockchain_service import BlockchainService

class TestBlockchainService:
    
    @pytest.fixture
    def mock_web3(self):
        """Mock Web3 instance"""
        mock_w3 = Mock()
        mock_w3.isConnected.return_value = True
        mock_w3.eth.accounts = ['0x1234567890123456789012345678901234567890']
        mock_w3.toWei.return_value = 1000000000000000000  # 1 ETH in wei
        mock_w3.fromWei.return_value = 1.0  # 1 ETH
        return mock_w3
    
    @pytest.fixture
    def blockchain_service(self, mock_web3):
        """Create blockchain service with mocked Web3"""
        with patch('blockchain_service.Web3') as mock_web3_class:
            mock_web3_class.return_value = mock_web3
            service = BlockchainService()
            service.w3 = mock_web3
            return service
    
    def test_initialization(self, blockchain_service, mock_web3):
        """Test blockchain service initialization"""
        assert blockchain_service.w3 == mock_web3
        assert blockchain_service.owner_account == '0x1234567890123456789012345678901234567890'
    
    def test_deploy_contract_success(self, blockchain_service, mock_web3):
        """Test successful contract deployment"""
        # Mock contract deployment
        mock_contract = Mock()
        mock_constructor = Mock()
        mock_constructor.transact.return_value = '0xdeploymenthash'
        mock_contract.constructor.return_value = mock_constructor
        
        mock_receipt = Mock()
        mock_receipt.contractAddress = '0xcontractaddress'
        
        mock_web3.eth.contract.return_value = mock_contract
        mock_web3.eth.waitForTransactionReceipt.return_value = mock_receipt
        
        # Deploy contract
        address = blockchain_service.deploy_contract()
        
        assert address == '0xcontractaddress'
        assert blockchain_service.contract_address == '0xcontractaddress'
    
    def test_connect_to_contract(self, blockchain_service, mock_web3):
        """Test connecting to existing contract"""
        mock_contract = Mock()
        mock_web3.eth.contract.return_value = mock_contract
        
        result = blockchain_service.connect_to_contract('0xexistingcontract')
        
        assert result is True
        assert blockchain_service.contract_address == '0xexistingcontract'
        assert blockchain_service.contract == mock_contract
    
    def test_create_toll_record_success(self, blockchain_service, mock_web3):
        """Test successful toll record creation"""
        # Setup mock contract
        mock_contract = Mock()
        mock_function = Mock()
        mock_function.transact.return_value = '0xtxhash'
        mock_contract.functions.createToll.return_value = mock_function
        
        # Mock transaction receipt and events
        mock_receipt = Mock()
        mock_receipt.blockNumber = 12345
        
        mock_event = Mock()
        mock_event.processReceipt.return_value = [{'args': {'tollId': 1}}]
        mock_contract.events.TollCreated.return_value = mock_event
        
        mock_web3.eth.waitForTransactionReceipt.return_value = mock_receipt
        
        blockchain_service.contract = mock_contract
        
        # Create toll record
        result = blockchain_service.create_toll_record(
            '0xvehicleaddress',
            'GANTRY_001',
            0.05
        )
        
        assert result is not None
        assert result['toll_id'] == 1
        assert result['tx_hash'] == '0xtxhash'
        assert result['block_number'] == 12345
    
    def test_auto_pay_toll_success(self, blockchain_service, mock_web3):
        """Test successful auto-pay toll"""
        # Setup mock contract
        mock_contract = Mock()
        mock_function = Mock()
        mock_function.transact.return_value = '0xtxhash'
        mock_contract.functions.autoPayToll.return_value = mock_function
        
        # Mock transaction receipt and events
        mock_receipt = Mock()
        mock_receipt.blockNumber = 12345
        
        mock_toll_event = Mock()
        mock_toll_event.processReceipt.return_value = [{'args': {'tollId': 1}}]
        mock_contract.events.TollCreated.return_value = mock_toll_event
        
        mock_paid_event = Mock()
        mock_paid_event.processReceipt.return_value = [{'args': {'tollId': 1}}]
        mock_contract.events.TollPaid.return_value = mock_paid_event
        
        mock_web3.eth.waitForTransactionReceipt.return_value = mock_receipt
        
        blockchain_service.contract = mock_contract
        
        # Auto-pay toll
        result = blockchain_service.auto_pay_toll(
            '0xvehicleaddress',
            'GANTRY_001',
            0.05
        )
        
        assert result is not None
        assert result['toll_id'] == 1
        assert result['paid'] is True
        assert result['tx_hash'] == '0xtxhash'
    
    def test_auto_pay_toll_insufficient_balance(self, blockchain_service, mock_web3):
        """Test auto-pay toll with insufficient balance"""
        # Setup mock contract
        mock_contract = Mock()
        mock_function = Mock()
        mock_function.transact.return_value = '0xtxhash'
        mock_contract.functions.autoPayToll.return_value = mock_function
        
        # Mock transaction receipt and events (no paid event = insufficient balance)
        mock_receipt = Mock()
        mock_receipt.blockNumber = 12345
        
        mock_toll_event = Mock()
        mock_toll_event.processReceipt.return_value = [{'args': {'tollId': 1}}]
        mock_contract.events.TollCreated.return_value = mock_toll_event
        
        mock_paid_event = Mock()
        mock_paid_event.processReceipt.return_value = []  # No paid event
        mock_contract.events.TollPaid.return_value = mock_paid_event
        
        mock_web3.eth.waitForTransactionReceipt.return_value = mock_receipt
        
        blockchain_service.contract = mock_contract
        
        # Auto-pay toll
        result = blockchain_service.auto_pay_toll(
            '0xvehicleaddress',
            'GANTRY_001',
            0.05\n        )\n        \n        assert result is not None\n        assert result['toll_id'] == 1\n        assert result['paid'] is False  # Payment failed due to insufficient balance\n    \n    def test_get_toll_record(self, blockchain_service, mock_web3):\n        \"\"\"Test getting toll record from blockchain\"\"\"\n        # Setup mock contract\n        mock_contract = Mock()\n        mock_function = Mock()\n        mock_function.call.return_value = [\n            '0xvehicleaddress',  # vehicle\n            'GANTRY_001',        # gantry_id\n            1640995200,          # timestamp\n            50000000000000000,   # amount_wei (0.05 ETH)\n            True                 # paid\n        ]\n        mock_contract.functions.tollRecords.return_value = mock_function\n        \n        blockchain_service.contract = mock_contract\n        \n        # Get toll record\n        result = blockchain_service.get_toll_record(1)\n        \n        assert result is not None\n        assert result['vehicle'] == '0xvehicleaddress'\n        assert result['gantry_id'] == 'GANTRY_001'\n        assert result['amount_eth'] == 1.0  # Mocked fromWei conversion\n        assert result['paid'] is True\n    \n    def test_get_vehicle_balance(self, blockchain_service, mock_web3):\n        \"\"\"Test getting vehicle balance\"\"\"\n        # Setup mock contract\n        mock_contract = Mock()\n        mock_function = Mock()\n        mock_function.call.return_value = 1000000000000000000  # 1 ETH in wei\n        mock_contract.functions.vehicleBalances.return_value = mock_function\n        \n        blockchain_service.contract = mock_contract\n        \n        # Get balance\n        balance = blockchain_service.get_vehicle_balance('0xvehicleaddress')\n        \n        assert balance == 1.0  # Mocked fromWei conversion\n    \n    def test_deposit_balance(self, blockchain_service, mock_web3):\n        \"\"\"Test depositing balance to vehicle account\"\"\"\n        # Setup mock contract\n        mock_contract = Mock()\n        mock_function = Mock()\n        mock_function.transact.return_value = '0xtxhash'\n        mock_contract.functions.depositBalance.return_value = mock_function\n        \n        mock_receipt = Mock()\n        mock_receipt.blockNumber = 12345\n        mock_web3.eth.waitForTransactionReceipt.return_value = mock_receipt\n        \n        blockchain_service.contract = mock_contract\n        \n        # Deposit balance\n        result = blockchain_service.deposit_balance('0xvehicleaddress', 1.0)\n        \n        assert result is not None\n        assert result['tx_hash'] == '0xtxhash'\n        assert result['block_number'] == 12345\n    \n    def test_contract_not_connected_error(self, blockchain_service):\n        \"\"\"Test operations when contract is not connected\"\"\"\n        blockchain_service.contract = None\n        \n        # All operations should return None when contract not connected\n        assert blockchain_service.create_toll_record('0xaddr', 'GANTRY_001', 0.05) is None\n        assert blockchain_service.auto_pay_toll('0xaddr', 'GANTRY_001', 0.05) is None\n        assert blockchain_service.get_toll_record(1) is None\n        assert blockchain_service.get_vehicle_balance('0xaddr') == 0\n        assert blockchain_service.deposit_balance('0xaddr', 1.0) is None\n\nclass TestBlockchainAPI:\n    \"\"\"Test blockchain Flask API endpoints\"\"\"\n    \n    @pytest.fixture\n    def client(self):\n        \"\"\"Create test client for blockchain API\"\"\"\n        from blockchain_service import app\n        app.config['TESTING'] = True\n        return app.test_client()\n    \n    @patch('blockchain_service.blockchain')\n    def test_health_endpoint(self, mock_blockchain, client):\n        \"\"\"Test health endpoint\"\"\"\n        mock_blockchain.w3.isConnected.return_value = True\n        \n        response = client.get('/health')\n        assert response.status_code == 200\n        \n        data = json.loads(response.data)\n        assert data['status'] == 'healthy'\n        assert data['service'] == 'blockchain'\n        assert data['connected'] is True\n    \n    @patch('blockchain_service.blockchain')\n    def test_deploy_contract_endpoint(self, mock_blockchain, client):\n        \"\"\"Test contract deployment endpoint\"\"\"\n        mock_blockchain.deploy_contract.return_value = '0xcontractaddress'\n        \n        response = client.post('/deploy')\n        assert response.status_code == 200\n        \n        data = json.loads(response.data)\n        assert data['contract_address'] == '0xcontractaddress'\n    \n    @patch('blockchain_service.blockchain')\n    def test_connect_contract_endpoint(self, mock_blockchain, client):\n        \"\"\"Test contract connection endpoint\"\"\"\n        mock_blockchain.connect_to_contract.return_value = True\n        \n        response = client.post('/connect', json={\n            'contract_address': '0xexistingcontract'\n        })\n        assert response.status_code == 200\n        \n        data = json.loads(response.data)\n        assert data['status'] == 'connected'\n    \n    @patch('blockchain_service.blockchain')\n    def test_create_toll_endpoint(self, mock_blockchain, client):\n        \"\"\"Test toll creation endpoint\"\"\"\n        mock_blockchain.create_toll_record.return_value = {\n            'toll_id': 1,\n            'tx_hash': '0xtxhash',\n            'block_number': 12345\n        }\n        \n        response = client.post('/toll/create', json={\n            'vehicle_address': '0xvehicleaddress',\n            'gantry_id': 'GANTRY_001',\n            'amount': 0.05\n        })\n        assert response.status_code == 200\n        \n        data = json.loads(response.data)\n        assert data['toll_id'] == 1\n        assert data['tx_hash'] == '0xtxhash'\n    \n    @patch('blockchain_service.blockchain')\n    def test_auto_pay_toll_endpoint(self, mock_blockchain, client):\n        \"\"\"Test auto-pay toll endpoint\"\"\"\n        mock_blockchain.auto_pay_toll.return_value = {\n            'toll_id': 1,\n            'paid': True,\n            'tx_hash': '0xtxhash',\n            'block_number': 12345\n        }\n        \n        response = client.post('/toll/autopay', json={\n            'vehicle_address': '0xvehicleaddress',\n            'gantry_id': 'GANTRY_001',\n            'amount': 0.05\n        })\n        assert response.status_code == 200\n        \n        data = json.loads(response.data)\n        assert data['toll_id'] == 1\n        assert data['paid'] is True\n    \n    @patch('blockchain_service.blockchain')\n    def test_get_toll_endpoint(self, mock_blockchain, client):\n        \"\"\"Test get toll record endpoint\"\"\"\n        mock_blockchain.get_toll_record.return_value = {\n            'vehicle': '0xvehicleaddress',\n            'gantry_id': 'GANTRY_001',\n            'amount_eth': 0.05,\n            'paid': True\n        }\n        \n        response = client.get('/toll/1')\n        assert response.status_code == 200\n        \n        data = json.loads(response.data)\n        assert data['vehicle'] == '0xvehicleaddress'\n        assert data['paid'] is True\n    \n    @patch('blockchain_service.blockchain')\n    def test_get_balance_endpoint(self, mock_blockchain, client):\n        \"\"\"Test get vehicle balance endpoint\"\"\"\n        mock_blockchain.get_vehicle_balance.return_value = 1.5\n        \n        response = client.get('/balance/0xvehicleaddress')\n        assert response.status_code == 200\n        \n        data = json.loads(response.data)\n        assert data['balance'] == 1.5\n    \n    @patch('blockchain_service.blockchain')\n    def test_blockchain_service_failure(self, mock_blockchain, client):\n        \"\"\"Test API behavior when blockchain service fails\"\"\"\n        mock_blockchain.auto_pay_toll.return_value = None\n        \n        response = client.post('/toll/autopay', json={\n            'vehicle_address': '0xvehicleaddress',\n            'gantry_id': 'GANTRY_001',\n            'amount': 0.05\n        })\n        assert response.status_code == 500\n        \n        data = json.loads(response.data)\n        assert 'error' in data\n\nif __name__ == \"__main__\":\n    pytest.main([__file__])