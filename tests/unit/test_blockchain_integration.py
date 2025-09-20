#!/usr/bin/env python3
"""
Unit tests for blockchain integration
"""

import pytest
import sys
import os
from unittest.mock import Mock, patch, MagicMock
import json

# Add blockchain to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'blockchain'))

class TestBlockchainIntegration:
    
    @patch('blockchain_service.Web3')
    def test_blockchain_service_initialization(self, mock_web3):
        """Test blockchain service initialization"""
        from blockchain_service import BlockchainService
        
        # Mock Web3 connection
        mock_w3_instance = Mock()
        mock_w3_instance.isConnected.return_value = True
        mock_w3_instance.eth.accounts = ['0x123...', '0x456...']
        mock_web3.return_value = mock_w3_instance
        
        service = BlockchainService()
        
        assert service.w3 == mock_w3_instance
        assert service.owner_account == '0x123...'
        mock_web3.assert_called_once()
    
    @patch('blockchain_service.Web3')
    def test_contract_deployment_success(self, mock_web3):
        """Test successful contract deployment"""
        from blockchain_service import BlockchainService
        
        # Mock Web3 and contract deployment
        mock_w3_instance = Mock()
        mock_w3_instance.isConnected.return_value = True
        mock_w3_instance.eth.accounts = ['0x123...']
        
        mock_contract = Mock()
        mock_constructor = Mock()
        mock_constructor.transact.return_value = '0xabc123'
        mock_contract.constructor.return_value = mock_constructor
        
        mock_receipt = Mock()
        mock_receipt.contractAddress = '0xcontract123'
        mock_w3_instance.eth.waitForTransactionReceipt.return_value = mock_receipt
        mock_w3_instance.eth.contract.return_value = mock_contract
        
        mock_web3.return_value = mock_w3_instance
        
        service = BlockchainService()
        result = service.deploy_contract()
        
        assert result == '0xcontract123'
        assert service.contract_address == '0xcontract123'
    
    @patch('blockchain_service.Web3')
    def test_toll_record_creation_success(self, mock_web3):
        """Test successful toll record creation"""
        from blockchain_service import BlockchainService
        
        # Setup mocks
        mock_w3_instance = Mock()
        mock_w3_instance.isConnected.return_value = True
        mock_w3_instance.eth.accounts = ['0x123...']
        mock_w3_instance.toWei.return_value = 1000000000000000000  # 1 ETH in wei
        
        mock_contract = Mock()
        mock_function = Mock()
        mock_function.transact.return_value = '0xtxhash123'
        mock_contract.functions.createToll.return_value = mock_function
        
        mock_receipt = Mock()
        mock_receipt.blockNumber = 12345
        mock_w3_instance.eth.waitForTransactionReceipt.return_value = mock_receipt
        
        # Mock event processing
        mock_event = Mock()
        mock_event_instance = Mock()
        mock_event_instance.processReceipt.return_value = [{'args': {'tollId': 1}}]
        mock_contract.events.TollCreated.return_value = mock_event_instance
        
        mock_web3.return_value = mock_w3_instance
        
        service = BlockchainService()
        service.contract = mock_contract
        service.owner_account = '0x123...'
        
        result = service.create_toll_record('0xvehicle123', 1, 0.05)
        
        assert result is not None
        assert result['toll_id'] == 1
        assert result['tx_hash'] == '0xtxhash123'
        assert result['block_number'] == 12345
    
    @patch('blockchain_service.Web3')
    def test_auto_pay_toll_success(self, mock_web3):
        """Test successful auto-pay toll"""
        from blockchain_service import BlockchainService
        
        # Setup mocks
        mock_w3_instance = Mock()
        mock_w3_instance.isConnected.return_value = True
        mock_w3_instance.eth.accounts = ['0x123...']
        mock_w3_instance.toWei.return_value = 50000000000000000  # 0.05 ETH in wei
        
        mock_contract = Mock()
        mock_function = Mock()
        mock_function.transact.return_value = '0xtxhash456'
        mock_contract.functions.autoPayToll.return_value = mock_function
        
        mock_receipt = Mock()
        mock_receipt.blockNumber = 12346
        mock_w3_instance.eth.waitForTransactionReceipt.return_value = mock_receipt
        
        # Mock events
        mock_toll_created_event = Mock()
        mock_toll_created_event.processReceipt.return_value = [{'args': {'tollId': 2}}]
        mock_contract.events.TollCreated.return_value = mock_toll_created_event
        
        mock_toll_paid_event = Mock()
        mock_toll_paid_event.processReceipt.return_value = [{'args': {'tollId': 2}}]
        mock_contract.events.TollPaid.return_value = mock_toll_paid_event
        
        mock_web3.return_value = mock_w3_instance
        
        service = BlockchainService()
        service.contract = mock_contract
        service.owner_account = '0x123...'
        
        result = service.auto_pay_toll('0xvehicle123', 1, 0.05)
        
        assert result is not None
        assert result['toll_id'] == 2
        assert result['paid'] == True
        assert result['tx_hash'] == '0xtxhash456'
    
    @patch('blockchain_service.Web3')
    def test_get_toll_record(self, mock_web3):
        """Test getting toll record"""
        from blockchain_service import BlockchainService
        
        # Setup mocks
        mock_w3_instance = Mock()
        mock_w3_instance.isConnected.return_value = True
        mock_w3_instance.eth.accounts = ['0x123...']
        mock_w3_instance.fromWei.return_value = 0.05
        
        mock_contract = Mock()
        mock_function = Mock()
        mock_function.call.return_value = [
            '0xvehicle123',  # vehicle
            1,              # gantry_id
            1640995200,     # timestamp
            50000000000000000,  # amount_wei
            True            # paid
        ]
        mock_contract.functions.tollRecords.return_value = mock_function
        
        mock_web3.return_value = mock_w3_instance
        
        service = BlockchainService()
        service.contract = mock_contract
        
        result = service.get_toll_record(1)
        
        assert result is not None
        assert result['vehicle'] == '0xvehicle123'
        assert result['gantry_id'] == 1
        assert result['amount_eth'] == 0.05
        assert result['paid'] == True
    
    @patch('blockchain_service.Web3')
    def test_get_vehicle_balance(self, mock_web3):
        """Test getting vehicle balance"""
        from blockchain_service import BlockchainService
        
        # Setup mocks
        mock_w3_instance = Mock()
        mock_w3_instance.isConnected.return_value = True
        mock_w3_instance.eth.accounts = ['0x123...']
        mock_w3_instance.fromWei.return_value = 1.5
        
        mock_contract = Mock()
        mock_function = Mock()
        mock_function.call.return_value = 1500000000000000000  # 1.5 ETH in wei
        mock_contract.functions.vehicleBalances.return_value = mock_function
        
        mock_web3.return_value = mock_w3_instance
        
        service = BlockchainService()
        service.contract = mock_contract
        
        balance = service.get_vehicle_balance('0xvehicle123')
        
        assert balance == 1.5
    
    @patch('blockchain_service.Web3')
    def test_contract_connection_failure(self, mock_web3):
        """Test contract connection failure handling"""
        from blockchain_service import BlockchainService
        
        # Mock Web3 connection failure
        mock_w3_instance = Mock()
        mock_w3_instance.isConnected.return_value = False
        mock_w3_instance.eth.accounts = []
        mock_web3.return_value = mock_w3_instance
        
        service = BlockchainService()
        
        # Should handle connection failure gracefully
        assert service.owner_account is None
    
    @patch('blockchain_service.Web3')
    def test_toll_creation_failure(self, mock_web3):
        """Test toll creation failure handling"""
        from blockchain_service import BlockchainService
        
        # Setup mocks for failure scenario
        mock_w3_instance = Mock()
        mock_w3_instance.isConnected.return_value = True
        mock_w3_instance.eth.accounts = ['0x123...']
        mock_w3_instance.toWei.side_effect = Exception("Transaction failed")
        
        mock_web3.return_value = mock_w3_instance
        
        service = BlockchainService()
        service.contract = Mock()
        service.owner_account = '0x123...'
        
        result = service.create_toll_record('0xvehicle123', 1, 0.05)
        
        assert result is None
    
    def test_blockchain_service_without_contract(self):
        """Test blockchain service methods without contract connection"""
        from blockchain_service import BlockchainService
        
        with patch('blockchain_service.Web3') as mock_web3:
            mock_w3_instance = Mock()
            mock_w3_instance.isConnected.return_value = True
            mock_w3_instance.eth.accounts = ['0x123...']
            mock_web3.return_value = mock_w3_instance
            
            service = BlockchainService()
            # Don't set contract
            
            # All contract-dependent methods should return None or 0
            assert service.create_toll_record('0xvehicle', 1, 0.05) is None
            assert service.auto_pay_toll('0xvehicle', 1, 0.05) is None
            assert service.get_toll_record(1) is None
            assert service.get_vehicle_balance('0xvehicle') == 0
    
    def test_wei_eth_conversion_logic(self):
        """Test Wei to ETH conversion logic"""
        from blockchain_service import BlockchainService
        
        with patch('blockchain_service.Web3') as mock_web3:
            mock_w3_instance = Mock()
            mock_w3_instance.isConnected.return_value = True
            mock_w3_instance.eth.accounts = ['0x123...']
            mock_w3_instance.toWei.return_value = 50000000000000000  # 0.05 ETH
            mock_w3_instance.fromWei.return_value = 0.05
            mock_web3.return_value = mock_w3_instance
            
            service = BlockchainService()
            
            # Test conversion calls
            service.w3.toWei(0.05, 'ether')
            service.w3.fromWei(50000000000000000, 'ether')
            
            mock_w3_instance.toWei.assert_called_with(0.05, 'ether')
            mock_w3_instance.fromWei.assert_called_with(50000000000000000, 'ether')

if __name__ == "__main__":
    pytest.main([__file__])