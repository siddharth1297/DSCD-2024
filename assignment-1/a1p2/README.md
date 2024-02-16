
# Part 2 : Messaging App using zeromq 

## Author: Arjun Temura 

## **Simulates a zeromq based messaging service where multiple clients simultaneously interact within groups to exchange text messages. A single message appserver manages the groups available to the clients.**
 
1) Message app server: message_server.py (on gcloud vm)  
    
2) Group server: group.py (on gcloud vm) 
   
3) Client server: client.py (on localhost) 
   
### **Install Dependencies:** 
```

$ ./install.sh 

```
### **Run:** 
```

$ python3 message_server.py
$ python3 group.py 
$ python3 client.py

```
