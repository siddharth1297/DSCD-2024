import pika
import sys

class Youtuber:
    def __init__(self, youtuber_name, video_name):
        self.youtuber_name = youtuber_name
        self.video_name = video_name

    def publish_video(self):
        connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
        channel = connection.channel()
        channel.queue_declare(queue='youtuber_requests')

        message = {"youtuber": self.youtuber_name, "videoName": self.video_name}
        channel.basic_publish(exchange='', routing_key='youtuber_requests', body=str(message))
        print("SUCCESS: Video published to YouTube Server")
        connection.close()

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python Youtuber.py <YoutuberName> <VideoName>")
    else:
        youtuber_name = sys.argv[1]
        video_name = sys.argv[2:]
        video_name=' '.join(video_name)
             
        youtuber = Youtuber(youtuber_name, video_name)
        youtuber.publish_video()
