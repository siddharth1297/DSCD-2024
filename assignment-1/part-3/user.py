import pika
import sys

class User:
    def __init__(self, user_name, subscribe_action=None, youtuber_name=None):
        self.user_name = user_name
        self.subscribe_action = subscribe_action
        self.youtuber_name = youtuber_name

    def update_subscription(self):
        connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
        channel = connection.channel()
        channel.queue_declare(queue='user_requests')

        message = {"user": self.user_name, "youtuber": self.youtuber_name, "subscribe": self.subscribe_action == 's'}
        channel.basic_publish(exchange='', routing_key='user_requests', body=str(message))

        print("SUCCESS: Subscription/Unsubscription updated")
        

    def receive_notifications(self, ch, method, properties, body):
        message = eval(body)
        print(f"New Notification: {message['youtuber']} uploaded {message['videoName']}")



    def start_receiving_notifications(self):
        connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
        channel = connection.channel()
        channel.queue_declare(queue=self.user_name)

        channel.basic_consume(queue=self.user_name, on_message_callback=self.receive_notifications, auto_ack=True)
        print(f"{self.user_name} is logged in. Waiting for notifications. To exit press CTRL+C")
        channel.start_consuming()



if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python User.py <UserName> [s/u <YouTuberName>]")
    else:
        user_name = sys.argv[1]
        user = User(user_name)

        if len(sys.argv) == 4:
            action = sys.argv[2]
            youtuber_name = sys.argv[3]
            user.subscribe_action = action
            user.youtuber_name = youtuber_name
            user.update_subscription()
        
        user.start_receiving_notifications()
