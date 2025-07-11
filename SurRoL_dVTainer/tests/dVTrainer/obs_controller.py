import time
import logging
from obswebsocket import obsws, requests, events
import os
# logging.basicConfig(level=logging.DEBUG)

class OBSController:
    def __init__(self, host, port, password):
        self.host = host
        self.port = port
        self.password = password
        self.ws = None

    def on_event(self, message):
        print("[OBS Controller:  Got message: {}]".format(message))

    def on_switch(self, message):
        print("[OBS Controller: You changed the scene to {}]".format(message.getSceneName()))


    def connect(self):
        try:
            self.ws = obsws(self.host, self.port, self.password)
            # self.ws.register(self.on_event)
            self.ws.register(self.on_switch, events.SwitchScenes)
            self.ws.register(self.on_switch, events.CurrentProgramSceneChanged)
            self.ws.connect()
            print("[OBS Controller: Connected!]")
        except Exception as e:
            print(f"[OBS Controller: Error while connecting: {e}]")

    def set_record_directory(self, directory):
        try:
            response = self.ws.call(requests.SetRecordDirectory(recordDirectory=directory))
            if response.status:
                print(f"[OBS Controller: Recording directory set to {directory}.]")
            else:
                print(f"[OBS Controller: Failed to set recording directory: {response}]")
        except Exception as e:
            print(f"[OBS Controller: Error setting recording directory: {e}]")


    def start_virtualcam(self):
        try:
            self.ws.call(requests.StartVirtualCam())
            print("[OBS Controller: Started Virtual Camera!]")
        except Exception as e:
            print(f"[OBS Controller: Error while starting virtual camera: {e}]")

    def stop_virtualcam(self):
        try:
            self.ws.call(requests.StopVirtualCam())
            print("[OBS Controller: Stopped Virtual Camera!]")
        except Exception as e:
            print(f"[OBS Controller: Error while stopping virtual camera: {e}]")

    def start_recording(self):
        try:
            self.ws.call(requests.StartRecord())
            print("[OBS Controller: Started Recording!]")
        except Exception as e:
            print(f"[OBS Controller: Error while starting recording: {e}]")

    def stop_recording(self):
        try:
            self.ws.call(requests.StopRecord())
            print("[OBS Controller: Stopped Recording!]")
        except Exception as e:
            print(f"[OBS Controller: Error while stopping recording: {e}]")

    def disconnect(self):
        try:
            self.ws.disconnect()
            print("[OBS Controller: Disconnected!]")
        except Exception as e:
            print(f"[OBS Controller: Error while disconnecting: {e}]")


# if __name__ == "__main__":
#     print( os.getcwd())
#     host = "localhost"
#     port = 4455
#     password = "rYIh2EvZGlDxDV0L"

#     obs_controller = OBSController(host, port, password)
#     obs_controller.connect()

#     obs_controller.set_record_directory("./home/videos")
#     # Add logic here for start_recording, stop_recording, and disconnect as needed
