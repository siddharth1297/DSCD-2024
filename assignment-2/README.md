# [Assignment-2: Distributed key-value store using Raft]( https://docs.google.com/document/u/1/d/e/2PACX-1vSy3psit4UbAQci5vZhj-NhRQCIm5eBRdCDIXnnAe_cNPouWomX6P95MSuZdoSMd_rV0ugUJvJaVnGY/pub)

## Setup Instruction

### Install Rrequirements

$ python3 -m pip install -r requirements.txt

## Run

Set the configuration config in config.yaml file.

Run

$ python3 main.py -h

## Design and Implementation

## Architecture

Every Raft cluster has a peer KV server.
The client connects to the KV server, which serves three RPCs Put, Get, GetLeader.
The Following is the path for the operations:

GetLeader RPC,
    Calls the get_leader_id method of the raft module.

For Put and Get RPC, the node must be leader and has the lease. If not, the it sends back the leader details with error message.

Get(key) RPC:
    Calls the read_from_raft method of the raft cluster
    If it returns true, then the key must be in the data store. So read it from store and return
Put(key, value) RPC:
    Calls the write_to_raft method of the raft cluster.
    If it returns true, then the data is replicated and applied to the cluster. The subsequent read always returns this or futher value.

### Lease

Lease can only be hold by the node which can send appendEntries to majority of the nodes.

1. Wheneever a candidate gets majority number of votes, it becomes the leader.
It doesn't send the establishment of the authority immediately, rather waits for the maximum remaining lease interval.

2. Once the last lease times out, then the leader appends NO-OP to its log and broadcast the heartbeat message along with is NO-OP entry(Now it is no more a heartbeat message rather an appendEntry) in the log and with the remaining lease time(~10S in this case).

3. If it gets majority, on any appendEntry message(i.e both heartbeat and appendEntry), it renews the lease.

## TODO

### Test the following

Make deep copy of the command, before calling the appendEntry from the KVServer.
Log index with different term.
Wriiten to log, but because of timeout, client gets FAIL message while setting a key.
