#!/usr/bin/env python3
"""
Enhanced Blockchain Service with comprehensive error handling and transaction management
"""

from web3 import Web3
from web3.middleware import geth_poa_middleware
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import time
import threading
from collections import defaultdict
from dataclasses import dataclass
from enum import Enum
import hashlib
import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TransactionStatus(Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    FAILED = "failed"
    TIMEOUT = "timeout"

@dataclass
class TollTransaction:
    tx_hash: str
    vehicle_address: str
    gantry_id: int
    amount_wei: int
    status: TransactionStatus
    created_at: datetime
    confirmed_at: Optional[datetime] = None
    block_number: Optional[int] = None
    gas_used: Optional[int] = None
    error_message: Optional[str] = None

# Prometheus metrics
BLOCKCHAIN_REQUESTS = Counter('blockchain_requests_total', 'Total blockchain requests', ['method', 'status'])
TRANSACTION_DURATION = Histogram('blockchain_transaction_duration_seconds', 'Transaction processing time')
GAS_USAGE = Histogram('blockchain_gas_used', 'Gas used per transaction')
PENDING_TRANSACTIONS = Gauge('blockchain_pending_transactions', 'Number of pending transactions')
CONTRACT_BALANCE = Gauge('blockchain_contract_balance_eth', 'Contract balance in ETH')

class EnhancedBlockchainService:
    """Enhanced blockchain service with comprehensive transaction management"""
    
    def __init__(self, rpc_url: str = "http://localhost:8545", chain_id: int = 1337):
        self.rpc_url = rpc_url
        self.chain_id = chain_id
        self.w3 = None
        self.contract = None
        self.contract_address = None
        self.owner_account = None
        self.private_key = None
        
        # Transaction management
        self.pending_transactions = {}
        self.transaction_history = []
        self.nonce_manager = defaultdict(int)
        
        # Monitoring
        self.monitoring_thread = None
        self.is_monitoring = False
        
        # Contract ABI (enhanced)
        self.contract_abi = [
            {
                "inputs": [],
                "stateMutability": "nonpayable",
                "type": "constructor"
            },
            {
                "anonymous": False,
                "inputs": [
                    {"indexed": True, "name": "tollId", "type": "uint256"},
                    {"indexed": True, "name": "vehicle", "type": "address"},
                    {"indexed": False, "name": "gantryId", "type": "uint256"},
                    {"indexed": False, "name": "amount", "type": "uint256"},
                    {"indexed": False, "name": "timestamp", "type": "uint256"}
                ],
                "name": "TollCreated",
                "type": "event"
            },
            {
                "anonymous": False,
                "inputs": [
                    {"indexed": True, "name": "tollId", "type": "uint256"},
                    {"indexed": True, "name": "payer", "type": "address"},
                    {"indexed": False, "name": "amount", "type": "uint256"}
                ],
                "name": "TollPaid",
                "type": "event"
            },
            {
                "anonymous": False,
                "inputs": [
                    {"indexed": True, "name": "vehicle", "type": "address"},
                    {"indexed": False, "name": "amount", "type": "uint256"}
                ],
                "name": "BalanceDeposited",
                "type": "event"
            },
            {
                "inputs": [
                    {"name": "vehicle", "type": "address"},
                    {"name": "gantryId", "type": "uint256"},
                    {"name": "amount", "type": "uint256"}
                ],
                "name": "createToll",
                "outputs": [{"name": "tollId", "type": "uint256"}],
                "stateMutability": "nonpayable",
                "type": "function"
            },
            {
                "inputs": [
                    {"name": "vehicle", "type": "address"},
                    {"name": "gantryId", "type": "uint256"},
                    {"name": "amount", "type": "uint256"}
                ],
                "name": "autoPayToll",
                "outputs": [{"name": "tollId", "type": "uint256"}],
                "stateMutability": "nonpayable",
                "type": "function"
            },
            {
                "inputs": [{"name": "tollId", "type": "uint256"}],
                "name": "payToll",
                "outputs": [],
                "stateMutability": "payable",
                "type": "function"
            },
            {
                "inputs": [],
                "name": "depositBalance",
                "outputs": [],
                "stateMutability": "payable",
                "type": "function"
            },
            {
                "inputs": [{"name": "amount", "type": "uint256"}],
                "name": "withdrawBalance",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function"
            },
            {
                "inputs": [{"name": "tollId", "type": "uint256"}],
                "name": "getTollRecord",
                "outputs": [
                    {"name": "vehicle", "type": "address"},
                    {"name": "gantryId", "type": "uint256"},
                    {"name": "timestamp", "type": "uint256"},
                    {"name": "amount", "type": "uint256"},
                    {"name": "paid", "type": "bool"}
                ],
                "stateMutability": "view",
                "type": "function"
            },
            {
                "inputs": [{"name": "vehicle", "type": "address"}],
                "name": "getVehicleBalance",
                "outputs": [{"name": "", "type": "uint256"}],
                "stateMutability": "view",
                "type": "function"
            },
            {
                "inputs": [],
                "name": "getTotalTolls",
                "outputs": [{"name": "", "type": "uint256"}],
                "stateMutability": "view",
                "type": "function"
            },
            {
                "inputs": [],
                "name": "getContractBalance",
                "outputs": [{"name": "", "type": "uint256"}],
                "stateMutability": "view",
                "type": "function"
            }
        ]
        
        self._initialize_connection()
    
    def _initialize_connection(self):
        """Initialize blockchain connection"""
        try:
            self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
            
            # Add PoA middleware for development networks
            if self.chain_id != 1:  # Not mainnet
                self.w3.middleware_onion.inject(geth_poa_middleware, layer=0)
            
            if not self.w3.isConnected():
                raise ConnectionError("Failed to connect to blockchain")
            
            # Setup accounts
            self._setup_accounts()
            
            logger.info(f"✓ Connected to blockchain at {self.rpc_url}")
            logger.info(f"✓ Chain ID: {self.chain_id}")
            logger.info(f"✓ Latest block: {self.w3.eth.block_number}")
            
        except Exception as e:
            logger.error(f"Blockchain initialization failed: {e}")
            raise
    
    def _setup_accounts(self):
        """Setup blockchain accounts"""
        try:
            accounts = self.w3.eth.accounts
            if accounts:
                self.owner_account = accounts[0]
                logger.info(f"✓ Using account: {self.owner_account}")
            else:
                # For development, create a test account
                logger.warning("No accounts found, using test configuration")
                self.owner_account = "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266"  # Hardhat default
            
            # In production, load private key from secure storage
            self.private_key = os.getenv('BLOCKCHAIN_PRIVATE_KEY')
            if not self.private_key:
                logger.warning("No private key configured, using test key")
                self.private_key = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
            
        except Exception as e:
            logger.error(f"Account setup failed: {e}")
    
    def deploy_contract(self) -> Optional[str]:
        """Deploy TollManager contract"""
        try:
            # Contract bytecode (simplified for demo)
            contract_bytecode = "0x608060405234801561001057600080fd5b50336000806101000a81548173ffffffffffffffffffffffffffffffffffffffff021916908373ffffffffffffffffffffffffffffffffffffffff1602179055506001600181905550610c8c806100686000396000f3fe"
            
            # Build transaction
            contract = self.w3.eth.contract(abi=self.contract_abi, bytecode=contract_bytecode)
            
            nonce = self.w3.eth.get_transaction_count(self.owner_account)
            
            transaction = contract.constructor().buildTransaction({
                'chainId': self.chain_id,
                'gas': 2000000,
                'gasPrice': self.w3.toWei('20', 'gwei'),
                'nonce': nonce,
            })
            
            # Sign and send transaction
            signed_txn = self.w3.eth.account.sign_transaction(transaction, self.private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
            
            # Wait for confirmation
            tx_receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            
            if tx_receipt.status == 1:
                self.contract_address = tx_receipt.contractAddress
                self.contract = self.w3.eth.contract(
                    address=self.contract_address,
                    abi=self.contract_abi
                )
                
                logger.info(f"✓ Contract deployed at: {self.contract_address}")
                BLOCKCHAIN_REQUESTS.labels(method='deploy', status='success').inc()
                
                # Start monitoring
                self._start_monitoring()
                
                return self.contract_address
            else:
                logger.error("Contract deployment failed")
                BLOCKCHAIN_REQUESTS.labels(method='deploy', status='failed').inc()
                return None
                
        except Exception as e:
            logger.error(f"Contract deployment error: {e}")
            BLOCKCHAIN_REQUESTS.labels(method='deploy', status='error').inc()
            return None
    
    def connect_to_contract(self, contract_address: str) -> bool:
        """Connect to existing contract"""
        try:
            self.contract_address = contract_address
            self.contract = self.w3.eth.contract(
                address=Web3.toChecksumAddress(contract_address),
                abi=self.contract_abi
            )
            
            # Test contract connection
            total_tolls = self.contract.functions.getTotalTolls().call()
            
            logger.info(f"✓ Connected to contract: {contract_address}")
            logger.info(f"✓ Total tolls in contract: {total_tolls}")
            
            # Start monitoring
            self._start_monitoring()
            
            BLOCKCHAIN_REQUESTS.labels(method='connect', status='success').inc()
            return True
            
        except Exception as e:
            logger.error(f"Contract connection error: {e}")
            BLOCKCHAIN_REQUESTS.labels(method='connect', status='error').inc()
            return False
    
    def create_toll_record(self, vehicle_address: str, gantry_id: int, amount_eth: float) -> Optional[Dict[str, Any]]:
        """Create toll record on blockchain"""
        if not self.contract:
            logger.error("Contract not connected")
            return None
        
        start_time = time.time()
        
        try:
            vehicle_address = Web3.toChecksumAddress(vehicle_address)
            amount_wei = self.w3.toWei(amount_eth, 'ether')
            
            # Build transaction
            nonce = self.w3.eth.get_transaction_count(self.owner_account)
            
            transaction = self.contract.functions.createToll(
                vehicle_address,
                gantry_id,
                amount_wei
            ).buildTransaction({
                'chainId': self.chain_id,
                'gas': 200000,
                'gasPrice': self.w3.toWei('20', 'gwei'),
                'nonce': nonce,
            })
            
            # Sign and send
            signed_txn = self.w3.eth.account.sign_transaction(transaction, self.private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
            
            # Create transaction record
            toll_tx = TollTransaction(
                tx_hash=tx_hash.hex(),
                vehicle_address=vehicle_address,
                gantry_id=gantry_id,
                amount_wei=amount_wei,
                status=TransactionStatus.PENDING,
                created_at=datetime.utcnow()
            )
            
            self.pending_transactions[tx_hash.hex()] = toll_tx
            PENDING_TRANSACTIONS.set(len(self.pending_transactions))
            
            logger.info(f"✓ Toll creation transaction sent: {tx_hash.hex()}")
            BLOCKCHAIN_REQUESTS.labels(method='create_toll', status='pending').inc()
            
            return {
                'tx_hash': tx_hash.hex(),
                'status': 'pending',
                'vehicle_address': vehicle_address,
                'gantry_id': gantry_id,
                'amount_eth': amount_eth
            }
            
        except Exception as e:
            logger.error(f"Create toll error: {e}")
            BLOCKCHAIN_REQUESTS.labels(method='create_toll', status='error').inc()
            return None
        finally:
            TRANSACTION_DURATION.observe(time.time() - start_time)
    
    def auto_pay_toll(self, vehicle_address: str, gantry_id: int, amount_eth: float) -> Optional[Dict[str, Any]]:
        """Auto-pay toll using vehicle balance"""
        if not self.contract:
            logger.error("Contract not connected")
            return None
        
        start_time = time.time()
        
        try:
            vehicle_address = Web3.toChecksumAddress(vehicle_address)
            amount_wei = self.w3.toWei(amount_eth, 'ether')
            
            # Check vehicle balance first
            balance = self.get_vehicle_balance(vehicle_address)
            if balance < amount_eth:
                logger.warning(f"Insufficient balance for {vehicle_address}: {balance} < {amount_eth}")
                return {
                    'error': 'insufficient_balance',
                    'current_balance': balance,
                    'required_amount': amount_eth
                }
            
            # Build transaction
            nonce = self.w3.eth.get_transaction_count(self.owner_account)
            
            transaction = self.contract.functions.autoPayToll(
                vehicle_address,
                gantry_id,
                amount_wei
            ).buildTransaction({
                'chainId': self.chain_id,
                'gas': 300000,
                'gasPrice': self.w3.toWei('20', 'gwei'),
                'nonce': nonce,
            })
            
            # Sign and send
            signed_txn = self.w3.eth.account.sign_transaction(transaction, self.private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
            
            # Create transaction record
            toll_tx = TollTransaction(
                tx_hash=tx_hash.hex(),
                vehicle_address=vehicle_address,
                gantry_id=gantry_id,
                amount_wei=amount_wei,
                status=TransactionStatus.PENDING,
                created_at=datetime.utcnow()
            )
            
            self.pending_transactions[tx_hash.hex()] = toll_tx
            PENDING_TRANSACTIONS.set(len(self.pending_transactions))
            
            logger.info(f"✓ Auto-pay toll transaction sent: {tx_hash.hex()}")
            BLOCKCHAIN_REQUESTS.labels(method='auto_pay', status='pending').inc()
            
            return {
                'tx_hash': tx_hash.hex(),
                'status': 'pending',
                'vehicle_address': vehicle_address,
                'gantry_id': gantry_id,
                'amount_eth': amount_eth
            }
            
        except Exception as e:
            logger.error(f"Auto-pay toll error: {e}")
            BLOCKCHAIN_REQUESTS.labels(method='auto_pay', status='error').inc()
            return None
        finally:
            TRANSACTION_DURATION.observe(time.time() - start_time)
    
    def get_transaction_status(self, tx_hash: str) -> Optional[Dict[str, Any]]:
        """Get transaction status and details"""
        try:
            # Check if it's a pending transaction
            if tx_hash in self.pending_transactions:
                toll_tx = self.pending_transactions[tx_hash]
                
                try:
                    # Try to get receipt
                    receipt = self.w3.eth.get_transaction_receipt(tx_hash)
                    
                    # Update transaction status
                    toll_tx.status = TransactionStatus.CONFIRMED if receipt.status == 1 else TransactionStatus.FAILED
                    toll_tx.confirmed_at = datetime.utcnow()
                    toll_tx.block_number = receipt.blockNumber
                    toll_tx.gas_used = receipt.gasUsed
                    
                    if receipt.status == 1:
                        # Parse events to get toll ID
                        toll_id = self._parse_toll_events(receipt)
                        
                        # Move to history
                        self.transaction_history.append(toll_tx)
                        del self.pending_transactions[tx_hash]
                        PENDING_TRANSACTIONS.set(len(self.pending_transactions))
                        
                        GAS_USAGE.observe(receipt.gasUsed)
                        BLOCKCHAIN_REQUESTS.labels(method='status_check', status='confirmed').inc()
                        
                        return {
                            'tx_hash': tx_hash,
                            'status': 'confirmed',
                            'toll_id': toll_id,
                            'block_number': receipt.blockNumber,
                            'gas_used': receipt.gasUsed,
                            'confirmed_at': toll_tx.confirmed_at.isoformat()
                        }
                    else:
                        toll_tx.error_message = "Transaction failed"
                        BLOCKCHAIN_REQUESTS.labels(method='status_check', status='failed').inc()
                        
                        return {
                            'tx_hash': tx_hash,
                            'status': 'failed',
                            'error': 'Transaction failed'
                        }
                        
                except Exception:
                    # Transaction still pending
                    return {
                        'tx_hash': tx_hash,
                        'status': 'pending',
                        'created_at': toll_tx.created_at.isoformat()
                    }
            
            # Check transaction history
            for toll_tx in self.transaction_history:
                if toll_tx.tx_hash == tx_hash:
                    return {
                        'tx_hash': tx_hash,
                        'status': toll_tx.status.value,
                        'block_number': toll_tx.block_number,
                        'gas_used': toll_tx.gas_used,
                        'confirmed_at': toll_tx.confirmed_at.isoformat() if toll_tx.confirmed_at else None
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"Status check error: {e}")
            return None
    
    def _parse_toll_events(self, receipt) -> Optional[int]:
        """Parse toll events from transaction receipt"""
        try:
            # Decode logs
            toll_created_logs = self.contract.events.TollCreated().processReceipt(receipt)
            if toll_created_logs:
                return toll_created_logs[0]['args']['tollId']
            return None
        except Exception as e:
            logger.error(f"Event parsing error: {e}")
            return None
    
    def get_vehicle_balance(self, vehicle_address: str) -> float:
        """Get vehicle balance from contract"""
        if not self.contract:
            return 0.0
        
        try:
            vehicle_address = Web3.toChecksumAddress(vehicle_address)
            balance_wei = self.contract.functions.getVehicleBalance(vehicle_address).call()
            return self.w3.fromWei(balance_wei, 'ether')
        except Exception as e:
            logger.error(f"Get balance error: {e}")
            return 0.0
    
    def deposit_balance(self, vehicle_address: str, amount_eth: float) -> Optional[Dict[str, Any]]:
        """Deposit balance to vehicle account"""
        if not self.contract:
            return None
        
        try:
            vehicle_address = Web3.toChecksumAddress(vehicle_address)
            amount_wei = self.w3.toWei(amount_eth, 'ether')
            
            nonce = self.w3.eth.get_transaction_count(self.owner_account)
            
            transaction = self.contract.functions.depositBalance().buildTransaction({
                'chainId': self.chain_id,
                'gas': 100000,
                'gasPrice': self.w3.toWei('20', 'gwei'),
                'nonce': nonce,
                'value': amount_wei
            })
            
            signed_txn = self.w3.eth.account.sign_transaction(transaction, self.private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
            
            logger.info(f"✓ Balance deposit transaction sent: {tx_hash.hex()}")
            
            return {
                'tx_hash': tx_hash.hex(),
                'status': 'pending',
                'amount_eth': amount_eth
            }
            
        except Exception as e:
            logger.error(f"Deposit balance error: {e}")
            return None
    
    def _start_monitoring(self):
        """Start transaction monitoring thread"""
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            return
        
        self.is_monitoring = True
        self.monitoring_thread = threading.Thread(target=self._monitoring_worker, daemon=True)
        self.monitoring_thread.start()
        logger.info("Transaction monitoring started")
    
    def _monitoring_worker(self):
        """Background worker for monitoring transactions and contract state"""
        while self.is_monitoring:
            try:
                # Check pending transactions
                self._check_pending_transactions()
                
                # Update contract metrics
                self._update_contract_metrics()
                
                # Clean up old transactions
                self._cleanup_old_transactions()
                
                time.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                logger.error(f"Monitoring worker error: {e}")
                time.sleep(30)
    
    def _check_pending_transactions(self):
        """Check status of pending transactions"""
        for tx_hash in list(self.pending_transactions.keys()):
            try:
                self.get_transaction_status(tx_hash)
            except Exception as e:
                logger.error(f"Error checking transaction {tx_hash}: {e}")
    
    def _update_contract_metrics(self):
        """Update Prometheus metrics"""
        if not self.contract:
            return
        
        try:
            # Update contract balance
            balance_wei = self.contract.functions.getContractBalance().call()
            balance_eth = self.w3.fromWei(balance_wei, 'ether')
            CONTRACT_BALANCE.set(balance_eth)
            
        except Exception as e:
            logger.error(f"Metrics update error: {e}")
    
    def _cleanup_old_transactions(self):
        """Clean up old transaction records"""
        cutoff_time = datetime.utcnow() - timedelta(hours=24)
        
        # Clean up old pending transactions (mark as timeout)
        for tx_hash, toll_tx in list(self.pending_transactions.items()):
            if toll_tx.created_at < cutoff_time:
                toll_tx.status = TransactionStatus.TIMEOUT
                toll_tx.error_message = "Transaction timeout"
                self.transaction_history.append(toll_tx)
                del self.pending_transactions[tx_hash]
        
        PENDING_TRANSACTIONS.set(len(self.pending_transactions))
        
        # Keep only recent history
        self.transaction_history = [
            tx for tx in self.transaction_history
            if tx.created_at > cutoff_time
        ]
    
    def get_service_stats(self) -> Dict[str, Any]:
        """Get blockchain service statistics"""
        return {
            'connected': self.w3.isConnected() if self.w3 else False,
            'contract_address': self.contract_address,
            'pending_transactions': len(self.pending_transactions),
            'transaction_history_count': len(self.transaction_history),
            'latest_block': self.w3.eth.block_number if self.w3 else 0,
            'monitoring_active': self.is_monitoring
        }
    
    def stop_monitoring(self):
        """Stop transaction monitoring"""
        self.is_monitoring = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)
        logger.info("Transaction monitoring stopped")

# Flask API for enhanced blockchain service
app = Flask(__name__)
CORS(app)

# Initialize blockchain service
blockchain = EnhancedBlockchainService()

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    stats = blockchain.get_service_stats()
    return jsonify({
        'status': 'healthy' if stats['connected'] else 'unhealthy',
        'service': 'enhanced_blockchain',
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        **stats
    })

@app.route('/metrics', methods=['GET'])
def metrics():
    """Prometheus metrics endpoint"""
    from flask import Response
    return Response(generate_latest(), mimetype='text/plain')

@app.route('/deploy', methods=['POST'])
def deploy_contract():
    """Deploy smart contract"""
    address = blockchain.deploy_contract()
    if address:
        return jsonify({'contract_address': address, 'status': 'deployed'})
    else:
        return jsonify({'error': 'Deployment failed'}), 500

@app.route('/connect', methods=['POST'])
def connect_contract():
    """Connect to existing contract"""
    data = request.get_json()
    address = data.get('contract_address')
    
    if blockchain.connect_to_contract(address):
        return jsonify({'status': 'connected', 'contract_address': address})
    else:
        return jsonify({'error': 'Connection failed'}), 500

@app.route('/toll/create', methods=['POST'])
def create_toll():
    """Create toll record"""
    data = request.get_json()
    result = blockchain.create_toll_record(
        data.get('vehicle_address'),
        data.get('gantry_id'),
        data.get('amount')
    )
    
    if result:
        return jsonify(result)
    else:
        return jsonify({'error': 'Failed to create toll'}), 500

@app.route('/toll/autopay', methods=['POST'])
def auto_pay_toll():
    """Auto-pay toll"""
    data = request.get_json()
    result = blockchain.auto_pay_toll(
        data.get('vehicle_address'),
        data.get('gantry_id'),
        data.get('amount')
    )
    
    if result:
        return jsonify(result)
    else:
        return jsonify({'error': 'Failed to auto-pay toll'}), 500

@app.route('/transaction/<tx_hash>/status', methods=['GET'])
def get_transaction_status(tx_hash):
    """Get transaction status"""
    status = blockchain.get_transaction_status(tx_hash)
    if status:
        return jsonify(status)
    else:
        return jsonify({'error': 'Transaction not found'}), 404

@app.route('/balance/<vehicle_address>', methods=['GET'])
def get_balance(vehicle_address):
    """Get vehicle balance"""
    balance = blockchain.get_vehicle_balance(vehicle_address)
    return jsonify({'vehicle_address': vehicle_address, 'balance_eth': balance})

@app.route('/balance/deposit', methods=['POST'])
def deposit_balance():
    """Deposit balance to vehicle account"""
    data = request.get_json()
    result = blockchain.deposit_balance(
        data.get('vehicle_address'),
        data.get('amount')
    )
    
    if result:
        return jsonify(result)
    else:
        return jsonify({'error': 'Failed to deposit balance'}), 500

@app.route('/stats', methods=['GET'])
def get_stats():
    """Get service statistics"""
    return jsonify(blockchain.get_service_stats())

if __name__ == "__main__":
    # Try to connect to existing contract or deploy new one
    contract_address = os.getenv('CONTRACT_ADDRESS', "0x5FbDB2315678afecb367f032d93F642f64180aa3")
    
    if not blockchain.connect_to_contract(contract_address):
        logger.info("Deploying new contract...")
        deployed_address = blockchain.deploy_contract()
        if deployed_address:
            logger.info(f"New contract deployed at: {deployed_address}")
        else:
            logger.error("Failed to deploy contract")
    
    try:
        app.run(host='0.0.0.0', port=5003, debug=False)
    except KeyboardInterrupt:
        blockchain.stop_monitoring()
        logger.info("Blockchain service stopped")