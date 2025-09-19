// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract TollManager {
    address public owner;
    uint256 public nextTollId;
    
    struct TollRecord {
        address vehicle;
        uint256 gantryId;
        uint256 timestamp;
        uint256 amount;
        bool paid;
    }
    
    mapping(uint256 => TollRecord) public tollRecords;
    mapping(address => uint256) public vehicleBalances;
    
    event TollCreated(uint256 indexed tollId, address indexed vehicle, uint256 amount);
    event TollPaid(uint256 indexed tollId, address indexed payer);
    
    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner");
        _;
    }
    
    constructor() {
        owner = msg.sender;
        nextTollId = 1;
    }
    
    function depositBalance() external payable {
        vehicleBalances[msg.sender] += msg.value;
    }
    
    function createToll(address vehicle, uint256 gantryId, uint256 amount) external onlyOwner {
        tollRecords[nextTollId] = TollRecord(vehicle, gantryId, block.timestamp, amount, false);
        emit TollCreated(nextTollId, vehicle, amount);
        nextTollId++;
    }
    
    function payToll(uint256 tollId) external payable {
        require(msg.value >= tollRecords[tollId].amount, "Insufficient payment");
        tollRecords[tollId].paid = true;
        payable(owner).transfer(msg.value);
        emit TollPaid(tollId, msg.sender);
    }
    
    function autoPayToll(address vehicle, uint256 gantryId, uint256 amount) external onlyOwner returns (uint256) {
        tollRecords[nextTollId] = TollRecord(vehicle, gantryId, block.timestamp, amount, false);
        uint256 tollId = nextTollId;
        nextTollId++;
        
        if (vehicleBalances[vehicle] >= amount) {
            vehicleBalances[vehicle] -= amount;
            tollRecords[tollId].paid = true;
            payable(owner).transfer(amount);
            emit TollPaid(tollId, vehicle);
        }
        
        emit TollCreated(tollId, vehicle, amount);
        return tollId;
    }
}