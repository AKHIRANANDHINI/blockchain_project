// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// Educational example only. Does not store patient or personal information.
contract PharmaVerify {
    address public owner;
    struct Record { bytes32 recordHash; address registeredBy; uint256 registeredAt; bool exists; }
    mapping(bytes32 => Record) private records;
    event MedicineRegistered(bytes32 indexed batchHash, bytes32 recordHash, address indexed registrar);
    modifier onlyOwner() { require(msg.sender == owner, "Only owner"); _; }
    constructor() { owner = msg.sender; }
    function registerMedicine(bytes32 batchHash, bytes32 recordHash) external onlyOwner {
        require(!records[batchHash].exists, "Batch already registered");
        records[batchHash] = Record(recordHash, msg.sender, block.timestamp, true);
        emit MedicineRegistered(batchHash, recordHash, msg.sender);
    }
    function verifyMedicine(bytes32 batchHash, bytes32 expectedHash) external view returns (bool) {
        Record memory r = records[batchHash];
        return r.exists && r.recordHash == expectedHash;
    }
    function getRecord(bytes32 batchHash) external view returns (bytes32,address,uint256,bool) {
        Record memory r = records[batchHash];
        return (r.recordHash,r.registeredBy,r.registeredAt,r.exists);
    }
}
