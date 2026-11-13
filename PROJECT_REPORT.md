# PharmaVerify: Blockchain-Based Medicine Authenticity and Expiry Tracking

## Abstract
PharmaVerify is a web application prototype for searching medicine batch records and checking recorded expiry dates. An administrator can register medicine details. The app creates SHA-256 record hashes and logs registration and verification actions in a hash-linked audit chain. A sample Solidity contract illustrates a possible blockchain extension.

## Problem Statement
Medicine batch information can be difficult to track when records are scattered or manually maintained. A digital lookup and auditable event log can make batch details easier to review.

## Objectives
- Register and search medicine batch records.
- Verify whether a batch exists in the demo database.
- Calculate Valid, Expiring Soon (within 90 days), or Expired status.
- Demonstrate a tamper-evident hash-linked audit log.
- Include a sample Solidity contract for a future blockchain integration.

## Modules
1. Admin login
2. Medicine registration
3. Medicine directory and search
4. Batch verification
5. Expiry tracking
6. Audit-chain integrity check

## Technology Stack
Frontend: HTML, CSS, Bootstrap. Backend: Python Flask. Database: SQLite. Hashing: SHA-256. Blockchain example: Solidity smart contract.

## Algorithm
1. Admin logs in.
2. Admin enters medicine details and batch number.
3. App validates required fields and date order.
4. App stores the record and computes a SHA-256 record hash.
5. App adds an audit event linked to the previous event hash.
6. User submits a batch number.
7. App finds the record and computes expiry status.
8. Verification outcome is added to the audit log.

## Test Cases
- Existing batch number: show matching record.
- Unknown batch: show not found.
- Expired date: show Expired.
- Expiry within 90 days: show Expiring Soon.
- Duplicate batch number: reject.
- Untampered audit chain: integrity check passes.

## How blockchain is used
The current web application uses a local hash-linked audit chain to demonstrate tamper evidence. The included Solidity contract can store batch and record hashes if deployed to an EVM blockchain. The contract is not deployed and the Flask app is not connected to it in this version. Therefore, this is a blockchain-inspired educational prototype, not a live decentralized blockchain system.

## Limitations and Future Scope
Demo records are fictional. A record cannot prove medicine authenticity without trusted manufacturer verification. Future work includes deploying the smart contract to a test network, Web3 integration, verified manufacturer roles, QR-code support, and expiry notifications.

## Conclusion
PharmaVerify demonstrates medicine batch search, expiry status calculation and an integrity-checked audit log as a foundation for a future pharmaceutical traceability DApp.
