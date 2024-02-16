import zmq
import socket
import uuid
import threading
from datetime import datetime  
import requests

def get_external_ip():
    metadata_server_url = "http://metadata.google.internal/computeMetadata/v1/instance/network-interfaces/0/access-configs/0/external-ip"
    headers = {"Metadata-Flavor": "Google"}

    try:
        response = requests.get(metadata_server_url, headers=headers)
        if response.status_code == 200:
            external_ip = response.text
            return external_ip
        else:
            print("Failed to retrieve external IP:", response.status_code)
            return None
    except Exception as e:
        print("Error occurred while retrieving external IP:", e)
        return None 

def store_string_with_timestamp(input_string, message_store):

    timestamp = datetime.now().strftime("%H:%M:%S")
    entry = f"{timestamp} ; {input_string}"
    message_store.append(f"{entry}")

def get_messages(message_store, timestamp): 
    
    message_printer=""
    for entry in message_store:
        # Extract timestamp from the entry
        entry_timestamp = entry.split(";")[0]

        # Compare timestamps and print messages after the target timestamp
        if entry_timestamp >= timestamp:
            message_printer+=f"< {entry.split(';')[0]}> : {entry.split(';')[1]} \n"

    return message_printer    
    
# Example usage:
message_store = []

clients=[]
context = zmq.Context()

# Get the group's IP
group_ip=get_external_ip() 

# Create a ROUTER socket
group_socket = context.socket(zmq.ROUTER)
group_port=group_socket.bind_to_random_port("tcp://*", min_port=1024, max_port=65535)

# Generate a UUID for the group
group_uuid = str(uuid.uuid1())

#External IP : Message App server
external_ip="34.16.102.214"

# Socket to talk to server
print("Connecting to message app server…")
socket = context.socket(zmq.REQ)
socket.connect(f"tcp://{external_ip}:5555")

# Send the group's IP, server port, and UUID as a string
group_info = f"GROUP:{group_ip}:{group_port}:{group_uuid}"
socket.send_string(group_info)

# Wait for server acknowledgment
message = socket.recv_string()
print(f"{message}")

while True:
    
    # Wait for a message from a client
    client_identity, _, request = group_socket.recv_multipart()

    request_parts = request.split(b";")
    response=f""

    if(request_parts[0]==b"JOIN_GROUP"):

        client_uuid = request_parts[1].decode('utf-8')
   
        print(f"JOIN REQUEST FROM {client_uuid}")
        clients.append(client_uuid)
        # Process the request (you can replace this with your own logic)
        response = f"SUCCESS"
    
    
    elif(request_parts[0]==b"LEAVE_GROUP"):

        client_uuid = request_parts[1].decode('utf-8')
   
        print(f"LEAVE REQUEST FROM {client_uuid}")
        try: 
            clients.remove(client_uuid)
            
        except: 
             print("Client not a member of this group")
             response=f"FAILED (NOT A MEMBER)"    
        else: 
            response = f"SUCCESS"

    elif(request_parts[0]==b"GET_MESSAGE"):

        client_uuid = request_parts[1].decode('utf-8')
        timestamp= request_parts[2].decode('utf-8')
        print(f"MESSAGE REQUEST FROM {client_uuid}")

        if client_uuid in clients: 
            message_printer=get_messages(message_store, timestamp)
            response = f"{message_printer}"
        else: 
            print("Client not a member of this group")
            response=f"FAILED" 
        


    else:

        client_uuid = request_parts[1].decode('utf-8')
        text_message= request_parts[2].decode('utf-8')
        print(f"MESSAGE SEND FROM {client_uuid}")
        
        if client_uuid in clients: 
            store_string_with_timestamp(text_message, message_store)
            response = f"SUCCESS"
        else: 
            print("Client not a member of this group")
            response=f"FAILED" 

    
    # Send the response back to the client using its identity
    group_socket.send_multipart([client_identity, b"", response.encode('utf-8')])     

