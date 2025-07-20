import grpc
from avp_stream.grpc_msg import * 
from threading import Thread
from avp_stream.utils.grpc_utils import * 
import time 
import numpy as np 


YUP2ZUP = np.array([[[1, 0, 0, 0], 
                    [0, 0, -1, 0], 
                    [0, 1, 0, 0],
                    [0, 0, 0, 1]]], dtype = np.float64)


class VisionProStreamer:

    def __init__(self, ip, record = False): 

        # Vision Pro IP 
        self.ip = ip
        self.record = record 
        self.recording = [] 
        self.latest = None 
        self.axis_transform = YUP2ZUP
        self.start_streaming()

    def start_streaming(self): 

        stream_thread = Thread(target = self.stream)
        stream_thread.daemon = True  # 메인 프로세스 종료 시 함께 종료
        stream_thread.start() 
        while self.latest is None: 
            pass 
        print(' == DATA IS FLOWING IN! ==')
        print('Ready to start streaming.') 


    def stream(self): 
        request = handtracking_pb2.HandUpdate()

        while True:  # 무한 재시도 루프
            try:
                print(f"Vision Pro 연결 시도 중... (IP: {self.ip})")
                with grpc.insecure_channel(f"{self.ip}:12345") as channel:
                    stub = handtracking_pb2_grpc.HandTrackingServiceStub(channel)
                    responses = stub.StreamHandUpdates(request)
                    
                    # 첫 번째 응답을 받았을 때만 연결 성공으로 간주
                    first_response = True
                    for response in responses:
                        if first_response:
                            print("Vision Pro 연결 성공!")
                            first_response = False
                            
                        transformations = {
                            "left_wrist": self.axis_transform @  process_matrix(response.left_hand.wristMatrix),
                            "right_wrist": self.axis_transform @  process_matrix(response.right_hand.wristMatrix),
                            "left_fingers":   process_matrices(response.left_hand.skeleton.jointMatrices),
                            "right_fingers":  process_matrices(response.right_hand.skeleton.jointMatrices),
                            "head": rotate_head(self.axis_transform @  process_matrix(response.Head)) , 
                            "left_pinch_distance": get_pinch_distance(response.left_hand.skeleton.jointMatrices),
                            "right_pinch_distance": get_pinch_distance(response.right_hand.skeleton.jointMatrices),
                            # "rgb": response.rgb, # TODO: should figure out how to get the rgb image from vision pro 
                        }
                        transformations["right_wrist_roll"] = get_wrist_roll(transformations["right_wrist"])
                        transformations["left_wrist_roll"] = get_wrist_roll(transformations["left_wrist"])
                        if self.record: 
                            self.recording.append(transformations)
                        self.latest = transformations

            except Exception as e:
                print(f"Vision Pro 연결 오류: {e}")
                print("3초 후 재시도...")
                time.sleep(3)
                continue  # 재시도

    def get_latest(self): 
        return self.latest
        
    def get_recording(self): 
        return self.recording
    

if __name__ == "__main__": 

    streamer = VisionProStreamer(ip = '10.29.230.57')
    while True: 

        latest = streamer.get_latest()
        print(latest)