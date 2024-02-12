import zmq

context = zmq.Context()

# List to store group information
groups = []

# Socket to talk to groups
socket = context.socket(zmq.REP)
socket.bind("tcp://*:5555")

def format_group_list(groups): 
    groups_string=""
    for i in range(len(groups)):
       groups_string+=f"Group Server {i+1}: {groups[i]['ip']}:{groups[i]['port']} \n"
    
    return groups_string    

#start here
print("Message App Server is up and running............\n")
while True:
    # Wait for the next request from the group
    message = socket.recv_string()
    
    if message.startswith("GROUP"):
        # Extract group IP, group port, and UUID
        _,group_ip, group_port, group_uuid = message.split(':')

        # Process the group information
        print(f"JOIN REQUEST FROM {group_ip}:{group_port} with UUID {group_uuid}")

        # Store the group information in the list
        groups.append({
            'ip': group_ip,
            'port': int(group_port),
            'uuid': group_uuid
        })

        # Send acknowledgment back to the group
        socket.send_string("SUCCESS")

    else: 
        
        # Extract client IP, client port, and UUID
        _,client_uuid = message.split(';')

        # Process the client information
        print(f"GROUP LIST REQUEST FROM UUID {client_uuid}")
        
        socket.send_string(format_group_list(groups)) 
        

    
        


    
