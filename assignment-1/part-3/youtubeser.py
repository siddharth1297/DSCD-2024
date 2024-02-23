import pika

R_MQ='10.128.0.8'
class YouTubeServer:
    def __init__(self):
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(R_MQ))
        self.channel = self.connection.channel()
        self.channel.queue_declare(queue='user_requests')
        self.channel.queue_declare(queue='youtuber_requests')
        self.subscriptions = {}

    def consume_user_requests(self, ch, method, properties, body):
        message = eval(body)
        user = message['user']
        youtuber = message.get('youtuber', None)
        subscribe_action = 'subscribed' if message.get('subscribe', False) else 'unsubscribed'

        if youtuber:
            print(f"{user} {subscribe_action} to {youtuber}")
            if subscribe_action == 'subscribed':
                if user not in self.subscriptions:
                    self.subscriptions[user] = set()
                self.subscriptions[user].add(youtuber)
            elif subscribe_action == 'unsubscribed':  
                if user in self.subscriptions:  
                    self.subscriptions[user].discard(youtuber)  

        else:
            print("user log in")
            

    def consume_youtuber_requests(self, ch, method, properties, body):
        message = eval(body)
        youtuber = message['youtuber']
        video_name = message['videoName']
        print(f"{youtuber} uploaded {video_name}")

        # Notify subscribed users about the new video
        for user, subscribed_youtubers in self.subscriptions.items():
            if youtuber in subscribed_youtubers:
                notification_message = {"youtuber": youtuber, "videoName": video_name}
                user_reply_queue=f"{user}"
                self.channel.basic_publish(exchange='', routing_key=user_reply_queue, body=str(notification_message))
                print(f"Notification sent to {user}: {youtuber} uploaded a new video")



    def start_consuming(self):
        self.channel.basic_consume(queue='user_requests', on_message_callback=self.consume_user_requests, auto_ack=True)
        self.channel.basic_consume(queue='youtuber_requests', on_message_callback=self.consume_youtuber_requests, auto_ack=True)
        print("YouTube Server is running. Waiting for messages. To exit press CTRL+C")
        self.channel.start_consuming()

if __name__ == '__main__':
    youtube_server = YouTubeServer()
    youtube_server.start_consuming()
