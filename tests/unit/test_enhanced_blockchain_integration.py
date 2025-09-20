#!/usr/bin/env python3
"""
Unit tests for enhanced blockchain integration
"""

import pytest
import sys
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import json

# Add blockchain to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'blockchain'))
from enhanced_blockchain_service import (
    EnhancedBlockchainService, TollTransaction, TransactionStatus
)

class TestEnhancedBlockchainIntegration:
    
    @pytest.fixture
    def mock_web3(self):
        """Mock Web3 instance"""
        mock_w3 = Mock()
        mock_w3.isConnected.return_value = True
        mock_w3.eth.block_number = 12345
        mock_w3.eth.accounts = ['0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266']
        mock_w3.eth.get_transaction_count.return_value = 1
        mock_w3.toWei.return_value = 1000000000000000000  # 1 ETH in wei
        mock_w3.fromWei.return_value = 1.0  # 1 ETH
        mock_w3.toChecksumAddress.side_effect = lambda x: x
        return mock_w3
    
    @pytest.fixture
    def mock_contract(self):
        """Mock contract instance"""
        mock_contract = Mock()
        mock_contract.functions.getTotalTolls.return_value.call.return_value = 10
        mock_contract.functions.getVehicleBalance.return_value.call.return_value = 1000000000000000000
        mock_contract.functions.getContractBalance.return_value.call.return_value = 5000000000000000000
        return mock_contract
    
    @pytest.fixture
    def blockchain_service(self, mock_web3):
        """Create blockchain service with mocked Web3"""
        with patch('enhanced_blockchain_service.Web3') as mock_web3_class:
            mock_web3_class.return_value = mock_web3
            service = EnhancedBlockchainService()
            service.w3 = mock_web3
            return service
    
    def test_initialization(self, blockchain_service, mock_web3):
        """Test blockchain service initialization"""
        assert blockchain_service.w3 == mock_web3
        assert blockchain_service.rpc_url == "http://localhost:8545"
        assert blockchain_service.chain_id == 1337
        assert blockchain_service.owner_account == '0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266'
        assert len(blockchain_service.pending_transactions) == 0
        assert len(blockchain_service.transaction_history) == 0
    
    def test_contract_connection(self, blockchain_service, mock_contract):
        """Test connecting to existing contract"""
        with patch.object(blockchain_service.w3.eth, 'contract', return_value=mock_contract):
            result = blockchain_service.connect_to_contract('0x1234567890123456789012345678901234567890')
            
            assert result is True
            assert blockchain_service.contract == mock_contract
            assert blockchain_service.contract_address == '0x1234567890123456789012345678901234567890'
    
    def test_contract_connection_failure(self, blockchain_service):
        """Test contract connection failure"""
        with patch.object(blockchain_service.w3.eth, 'contract') as mock_contract_method:
            mock_contract_method.side_effect = Exception("Connection failed")
            
            result = blockchain_service.connect_to_contract('0x1234567890123456789012345678901234567890')
            
            assert result is False
            assert blockchain_service.contract is None
    
    def test_create_toll_record_success(self, blockchain_service, mock_contract):
        """Test successful toll record creation"""
        blockchain_service.contract = mock_contract
        
        # Mock transaction building and sending
        mock_tx_hash = '0xabcdef1234567890'
        mock_transaction = {'chainId': 1337, 'gas': 200000, 'gasPrice': 20000000000, 'nonce': 1}
        
        mock_contract.functions.createToll.return_value.buildTransaction.return_value = mock_transaction
        
        with patch.object(blockchain_service.w3.eth.account, 'sign_transaction') as mock_sign:
            mock_sign.return_value.rawTransaction = b'signed_tx'
            
            with patch.object(blockchain_service.w3.eth, 'send_raw_transaction') as mock_send:
                mock_send.return_value.hex.return_value = mock_tx_hash
                
                result = blockchain_service.create_toll_record(
                    '0x1234567890123456789012345678901234567890',
                    1,
                    0.05
                )
                
                assert result is not None
                assert result['tx_hash'] == mock_tx_hash
                assert result['status'] == 'pending'
                assert result['vehicle_address'] == '0x1234567890123456789012345678901234567890'
                assert result['gantry_id'] == 1
                assert result['amount_eth'] == 0.05
                
                # Check pending transaction was created
                assert mock_tx_hash in blockchain_service.pending_transactions
                toll_tx = blockchain_service.pending_transactions[mock_tx_hash]
                assert toll_tx.status == TransactionStatus.PENDING
                assert toll_tx.vehicle_address == '0x1234567890123456789012345678901234567890'
                assert toll_tx.gantry_id == 1
    
    def test_create_toll_record_no_contract(self, blockchain_service):
        """Test toll record creation without contract"""
        result = blockchain_service.create_toll_record(
            '0x1234567890123456789012345678901234567890',
            1,
            0.05
        )
        
        assert result is None
    
    def test_auto_pay_toll_success(self, blockchain_service, mock_contract):
        """Test successful auto-pay toll"""
        blockchain_service.contract = mock_contract
        
        # Mock sufficient balance
        mock_contract.functions.getVehicleBalance.return_value.call.return_value = 1000000000000000000  # 1 ETH
        
        mock_tx_hash = '0xabcdef1234567890'
        mock_transaction = {'chainId': 1337, 'gas': 300000, 'gasPrice': 20000000000, 'nonce': 1}
        
        mock_contract.functions.autoPayToll.return_value.buildTransaction.return_value = mock_transaction
        
        with patch.object(blockchain_service.w3.eth.account, 'sign_transaction') as mock_sign:
            mock_sign.return_value.rawTransaction = b'signed_tx'
            
            with patch.object(blockchain_service.w3.eth, 'send_raw_transaction') as mock_send:
                mock_send.return_value.hex.return_value = mock_tx_hash
                
                result = blockchain_service.auto_pay_toll(
                    '0x1234567890123456789012345678901234567890',
                    1,
                    0.05
                )
                
                assert result is not None
                assert result['tx_hash'] == mock_tx_hash
                assert result['status'] == 'pending'
                assert mock_tx_hash in blockchain_service.pending_transactions
    
    def test_auto_pay_toll_insufficient_balance(self, blockchain_service, mock_contract):
        """Test auto-pay toll with insufficient balance"""
        blockchain_service.contract = mock_contract
        
        # Mock insufficient balance
        mock_contract.functions.getVehicleBalance.return_value.call.return_value = 10000000000000000  # 0.01 ETH
        
        result = blockchain_service.auto_pay_toll(
            '0x1234567890123456789012345678901234567890',
            1,
            0.05  # Requesting 0.05 ETH but only have 0.01 ETH
        )
        
        assert result is not None
        assert 'error' in result
        assert result['error'] == 'insufficient_balance'
        assert result['current_balance'] == 0.01
        assert result['required_amount'] == 0.05
    
    def test_get_vehicle_balance(self, blockchain_service, mock_contract):
        """Test getting vehicle balance"""
        blockchain_service.contract = mock_contract
        
        balance = blockchain_service.get_vehicle_balance('0x1234567890123456789012345678901234567890')
        
        assert balance == 1.0  # 1 ETH
        mock_contract.functions.getVehicleBalance.assert_called_once()
    
    def test_get_vehicle_balance_no_contract(self, blockchain_service):
        """Test getting vehicle balance without contract"""
        balance = blockchain_service.get_vehicle_balance('0x1234567890123456789012345678901234567890')
        
        assert balance == 0.0
    
    def test_get_vehicle_balance_error(self, blockchain_service, mock_contract):
        """Test getting vehicle balance with error"""
        blockchain_service.contract = mock_contract
        mock_contract.functions.getVehicleBalance.return_value.call.side_effect = Exception("Network error")
        
        balance = blockchain_service.get_vehicle_balance('0x1234567890123456789012345678901234567890')
        
        assert balance == 0.0
    
    def test_transaction_status_pending(self, blockchain_service):
        """Test getting status of pending transaction"""
        # Create a pending transaction
        tx_hash = '0xabcdef1234567890'
        toll_tx = TollTransaction(
            tx_hash=tx_hash,
            vehicle_address='0x1234567890123456789012345678901234567890',
            gantry_id=1,
            amount_wei=50000000000000000,
            status=TransactionStatus.PENDING,
            created_at=datetime.utcnow()
        )
        blockchain_service.pending_transactions[tx_hash] = toll_tx
        
        # Mock transaction receipt not found (still pending)
        with patch.object(blockchain_service.w3.eth, 'get_transaction_receipt') as mock_receipt:
            mock_receipt.side_effect = Exception("Transaction not found")
            
            status = blockchain_service.get_transaction_status(tx_hash)
            
            assert status is not None
            assert status['tx_hash'] == tx_hash
            assert status['status'] == 'pending'
            assert 'created_at' in status
    
    def test_transaction_status_confirmed(self, blockchain_service, mock_contract):
        """Test getting status of confirmed transaction"""
        blockchain_service.contract = mock_contract
        
        # Create a pending transaction
        tx_hash = '0xabcdef1234567890'
        toll_tx = TollTransaction(
            tx_hash=tx_hash,
            vehicle_address='0x1234567890123456789012345678901234567890',
            gantry_id=1,
            amount_wei=50000000000000000,
            status=TransactionStatus.PENDING,
            created_at=datetime.utcnow()
        )
        blockchain_service.pending_transactions[tx_hash] = toll_tx
        
        # Mock successful transaction receipt
        mock_receipt = Mock()
        mock_receipt.status = 1
        mock_receipt.blockNumber = 12346
        mock_receipt.gasUsed = 150000
        
        # Mock event parsing
        mock_event_log = Mock()
        mock_event_log.__getitem__ = lambda self, key: {'tollId': 123} if key == 'args' else None
        mock_contract.events.TollCreated.return_value.processReceipt.return_value = [mock_event_log]
        
        with patch.object(blockchain_service.w3.eth, 'get_transaction_receipt', return_value=mock_receipt):
            status = blockchain_service.get_transaction_status(tx_hash)
            
            assert status is not None
            assert status['tx_hash'] == tx_hash
            assert status['status'] == 'confirmed'
            assert status['toll_id'] == 123
            assert status['block_number'] == 12346
            assert status['gas_used'] == 150000
            assert 'confirmed_at' in status
            
            # Transaction should be moved to history
            assert tx_hash not in blockchain_service.pending_transactions
            assert len(blockchain_service.transaction_history) == 1
    
    def test_transaction_status_failed(self, blockchain_service):
        """Test getting status of failed transaction"""
        # Create a pending transaction
        tx_hash = '0xabcdef1234567890'
        toll_tx = TollTransaction(
            tx_hash=tx_hash,
            vehicle_address='0x1234567890123456789012345678901234567890',
            gantry_id=1,
            amount_wei=50000000000000000,
            status=TransactionStatus.PENDING,
            created_at=datetime.utcnow()
        )
        blockchain_service.pending_transactions[tx_hash] = toll_tx
        
        # Mock failed transaction receipt
        mock_receipt = Mock()
        mock_receipt.status = 0  # Failed
        mock_receipt.blockNumber = 12346
        mock_receipt.gasUsed = 150000
        
        with patch.object(blockchain_service.w3.eth, 'get_transaction_receipt', return_value=mock_receipt):
            status = blockchain_service.get_transaction_status(tx_hash)
            
            assert status is not None
            assert status['tx_hash'] == tx_hash
            assert status['status'] == 'failed'
            assert status['error'] == 'Transaction failed'
    
    def test_transaction_status_not_found(self, blockchain_service):
        """Test getting status of non-existent transaction"""
        status = blockchain_service.get_transaction_status('0xnonexistent')
        
        assert status is None
    
    def test_deposit_balance(self, blockchain_service, mock_contract):
        """Test depositing balance to vehicle account"""
        blockchain_service.contract = mock_contract
        
        mock_tx_hash = '0xabcdef1234567890'
        mock_transaction = {'chainId': 1337, 'gas': 100000, 'gasPrice': 20000000000, 'nonce': 1, 'value': 1000000000000000000}
        
        mock_contract.functions.depositBalance.return_value.buildTransaction.return_value = mock_transaction
        
        with patch.object(blockchain_service.w3.eth.account, 'sign_transaction') as mock_sign:
            mock_sign.return_value.rawTransaction = b'signed_tx'
            
            with patch.object(blockchain_service.w3.eth, 'send_raw_transaction') as mock_send:
                mock_send.return_value.hex.return_value = mock_tx_hash
                
                result = blockchain_service.deposit_balance(
                    '0x1234567890123456789012345678901234567890',
                    1.0
                )
                
                assert result is not None
                assert result['tx_hash'] == mock_tx_hash
                assert result['status'] == 'pending'
                assert result['amount_eth'] == 1.0
    
    def test_service_stats(self, blockchain_service, mock_contract):
        """Test getting service statistics"""
        blockchain_service.contract = mock_contract
        blockchain_service.contract_address = '0x1234567890123456789012345678901234567890'
        
        # Add some test data
        blockchain_service.pending_transactions['0xpending'] = Mock()
        blockchain_service.transaction_history.append(Mock())
        
        stats = blockchain_service.get_service_stats()
        
        assert stats['connected'] is True
        assert stats['contract_address'] == '0x1234567890123456789012345678901234567890'
        assert stats['pending_transactions'] == 1
        assert stats['transaction_history_count'] == 1
        assert stats['latest_block'] == 12345
        assert 'monitoring_active' in stats
    
    def test_cleanup_old_transactions(self, blockchain_service):
        """Test cleanup of old transactions"""
        # Create old pending transaction
        old_time = datetime.utcnow() - timedelta(hours=25)
        old_tx = TollTransaction(
            tx_hash='0xold',
            vehicle_address='0x1234567890123456789012345678901234567890',
            gantry_id=1,
            amount_wei=50000000000000000,
            status=TransactionStatus.PENDING,
            created_at=old_time
        )
        blockchain_service.pending_transactions['0xold'] = old_tx
        
        # Create recent pending transaction
        recent_tx = TollTransaction(
            tx_hash='0xrecent',
            vehicle_address='0x1234567890123456789012345678901234567890',
            gantry_id=1,
            amount_wei=50000000000000000,
            status=TransactionStatus.PENDING,
            created_at=datetime.utcnow()
        )
        blockchain_service.pending_transactions['0xrecent'] = recent_tx
        
        # Run cleanup
        blockchain_service._cleanup_old_transactions()
        
        # Old transaction should be moved to history with timeout status
        assert '0xold' not in blockchain_service.pending_transactions
        assert '0xrecent' in blockchain_service.pending_transactions
        assert len(blockchain_service.transaction_history) == 1
        assert blockchain_service.transaction_history[0].status == TransactionStatus.TIMEOUT
    
    def test_error_handling_in_create_toll(self, blockchain_service, mock_contract):
        """Test error handling in create toll record"""
        blockchain_service.contract = mock_contract
        
        # Mock transaction building failure
        mock_contract.functions.createToll.return_value.buildTransaction.side_effect = Exception("Gas estimation failed")
        
        result = blockchain_service.create_toll_record(
            '0x1234567890123456789012345678901234567890',
            1,
            0.05
        )
        
        assert result is None
    
    def test_invalid_address_handling(self, blockchain_service, mock_contract):
        """Test handling of invalid addresses"""
        blockchain_service.contract = mock_contract
        
        # Mock checksum address conversion failure
        with patch.object(blockchain_service.w3, 'toChecksumAddress') as mock_checksum:
            mock_checksum.side_effect = ValueError("Invalid address")
            
            result = blockchain_service.create_toll_record(
                'invalid_address',
                1,
                0.05
            )
            
            assert result is None
    
    def test_network_connection_failure(self):
        """Test handling of network connection failure"""
        with patch('enhanced_blockchain_service.Web3') as mock_web3_class:
            mock_w3 = Mock()
            mock_w3.isConnected.return_value = False
            mock_web3_class.return_value = mock_w3
            
            with pytest.raises(ConnectionError):
                EnhancedBlockchainService()
    
    def test_transaction_timeout_handling(self, blockchain_service):
        """Test handling of transaction timeouts"""
        # Create old pending transaction that should timeout
        old_time = datetime.utcnow() - timedelta(hours=25)
        timeout_tx = TollTransaction(
            tx_hash='0xtimeout',
            vehicle_address='0x1234567890123456789012345678901234567890',
            gantry_id=1,
            amount_wei=50000000000000000,
            status=TransactionStatus.PENDING,
            created_at=old_time
        )
        blockchain_service.pending_transactions['0xtimeout'] = timeout_tx
        
        # Simulate cleanup
        blockchain_service._cleanup_old_transactions()
        
        # Check transaction was marked as timeout
        assert '0xtimeout' not in blockchain_service.pending_transactions
        assert len(blockchain_service.transaction_history) == 1
        timeout_tx_history = blockchain_service.transaction_history[0]
        assert timeout_tx_history.status == TransactionStatus.TIMEOUT
        assert timeout_tx_history.error_message == "Transaction timeout"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])