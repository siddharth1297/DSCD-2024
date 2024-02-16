import zmq
import socket
import uuid
import os 

context = zmq.Context()

# Generate a UUID for the client
client_uuid = str(uuid.uuid1())

#External IP : Message App server
external_ip = "34.16.102.214"


print(f"Hello client! Choose from the options below")

while(True):
    print("*"*30)
    print("1. Get List of Active Group Servers")
    print("2. Join a Group")
    print("3. Leave a Group")
    print("4. Get Messages in a group")
    print("5. Send Messages to a group")
    print("6. Exit")
    
    choice=int(input("Enter your choice: (1/2/3/4/5)"))
    print("*"*30)

    if(choice == 1):
        # Socket to talk to client
        print("Connecting to message app server…")
        socket = context.socket(zmq.REQ)
        socket.connect(f"tcp://{external_ip}:5555")

        # Send the client's UUID as a string
        client_info = f"CLIENT;{client_uuid}"
        socket.send_string(client_info)

        # Wait for client acknowledgment
        message = socket.recv_string()
        print(f"\n{message}")
     
    elif (choice ==2):
        group_ip_port=input("Enter Group IP:Port = ")
        
        group_ip=group_ip_port.split(":")[0]
        group_port=group_ip_port.split(":")[1]
        
        
        socket = context.socket(zmq.REQ)

        # To uniquely identify each client connecting to the group server 
        current_pid = os.getpid()
        client_identity = f"Client{current_pid}".encode('utf-8')
        socket.setsockopt(zmq.IDENTITY, client_identity)
        
        socket.connect(f"tcp://{group_ip}:{group_port}")
        # Send the client's UUID as a string
        client_info = f"JOIN_GROUP;{client_uuid}"
        socket.send_string(client_info)

        # Wait for client acknowledgment
        message = socket.recv_string()
        print(f"\n{message}")


    elif (choice == 3):

        group_ip_port=input("Enter Group IP:Port = ")
        # group_port=input("Enter Group Port: ")
        group_ip=group_ip_port.split(":")[0]
        group_port=group_ip_port.split(":")[1]
        
        socket = context.socket(zmq.REQ)
        current_pid = os.getpid()
        client_identity = f"Client{current_pid}".encode('utf-8')
        socket.setsockopt(zmq.IDENTITY, client_identity)
        
        socket.connect(f"tcp://{group_ip}:{group_port}")
        # Send the client's UUID as a string
        client_info = f"LEAVE_GROUP;{client_uuid}"
        socket.send_string(client_info)
    
        # Wait for client acknowledgment
        message = socket.recv_string()
        print(f"\n{message}")

    elif (choice == 4):

        group_ip_port=input("Enter Group IP:Port = ")
        # group_port=input("Enter Group Port: ")
        group_ip=group_ip_port.split(":")[0]
        group_port=group_ip_port.split(":")[1]

        timestamp_input=input("Enter Timestamp after which messages need to be printed: ")
        # group_ip, group_port=group_ip_port.split[:]
        if timestamp_input.strip():  # strip removes leading/trailing whitespaces
            timestamp = timestamp_input
        else:
            timestamp = "00:00:00"
            
        socket = context.socket(zmq.REQ)
        current_pid = os.getpid()
        client_identity = f"Client{current_pid}".encode('utf-8')
        socket.setsockopt(zmq.IDENTITY, client_identity)
        
        socket.connect(f"tcp://{group_ip}:{group_port}")
        # Send the client's UUID as a string
        client_info = f"GET_MESSAGE;{client_uuid};{timestamp}"
        socket.send_string(client_info)
    
        # Wait for client acknowledgment
        message = socket.recv_string()
        print(f"\n{message}")

    elif (choice == 5):

        group_ip_port=input("Enter Group IP:Port = ")
        # group_port=input("Enter Group Port: ")
        group_ip=group_ip_port.split(":")[0]
        group_port=group_ip_port.split(":")[1]

        text_message=input("Enter your message: ")
        
        # group_ip, group_port=group_ip_port.split[:]
        
        socket = context.socket(zmq.REQ)
        current_pid = os.getpid()
        client_identity = f"Client{current_pid}".encode('utf-8')
        socket.setsockopt(zmq.IDENTITY, client_identity)
        
        socket.connect(f"tcp://{group_ip}:{group_port}")
        # Send the client's UUID as a string
        client_info = f"SEND_MESSAGE;{client_uuid};{text_message}"
        socket.send_string(client_info)
    
        # Wait for client acknowledgment
        message = socket.recv_string()
        print(f"\n{message}")
        
    elif (choice == 6):
        break 
    else: 
        print("You entered the wrong key! Please try again.")    

print("Bye!")



