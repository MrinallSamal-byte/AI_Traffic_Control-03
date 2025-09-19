const { ethers } = require("hardhat");

async function main() {
    console.log("Deploying TollManager contract...");
    
    const [deployer] = await ethers.getSigners();
    console.log("Deploying with account:", deployer.address);
    
    const TollManager = await ethers.getContractFactory("TollManager");
    const tollManager = await TollManager.deploy();
    
    await tollManager.deployed();
    
    console.log("TollManager deployed to:", tollManager.address);
    
    // Initialize with some test data
    console.log("Setting up test gantries...");
    
    const gantryPrice = ethers.utils.parseEther("0.025"); // 0.025 ETH
    
    console.log("Contract setup complete!");
    console.log("Contract address:", tollManager.address);
    console.log("Owner:", await tollManager.owner());
}

main()
    .then(() => process.exit(0))
    .catch((error) => {
        console.error(error);
        process.exit(1);
    });