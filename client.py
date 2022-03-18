import os
import threading
from tkinter import *

import grpc
import pyaudio
import cv2

import test_pb2 as chat
import test_pb2_grpc as rpc

import warnings

warnings.filterwarnings("ignore")

address = 'localhost'
port = 9090
FONT = cv2.FONT_HERSHEY_PLAIN


def draw_frame(img, vol, players, status, role, don, name):
    cv2.flip(img, 1)
    cv2.putText(img, vol, (40, 40), FONT, 3, (0, 0, 255), 3)
    if don is not None:
        cv2.putText(img, don, (40, 90), FONT, 3, (0, 0, 255), 3)
    else:
        cv2.putText(img, "Waiting other players", (40, 90), FONT, 3, (0, 0, 255), 3)
    cv2.putText(img, 'Your role:', (40, 140), FONT, 3, (0, 0, 255), 3)
    if role is not None:
        cv2.putText(img, role, (290, 140), FONT, 3, (0, 0, 255), 3)
    cv2.putText(img, 'Players: (Your name is ' + name + ")", (40, 190), FONT, 2, (0, 0, 255), 3)

    for i in range(5):
        cv2.putText(img, str(i) + '.', (40, 240 + 80 * i), FONT, 2, (0, 0, 255), 3)
        cv2.putText(img, 'Status:', (40, 280 + 80 * i), FONT, 2, (0, 0, 255), 3)
        cv2.putText(img, str(i + 5) + '.', (400, 240 + 80 * i), FONT, 2, (0, 0, 255), 3)
        cv2.putText(img, 'Status:', (400, 280 + 80 * i), FONT, 2, (0, 0, 255), 3)

    if players is not None and len(players) > 0:
        for i in range(len(players)):
            cv2.putText(img, players[i], (80 + 360 * (i // 5), 240 + 80 * (i % 5)), FONT, 2, (0, 0, 255), 3)
    if status is not None and len(status) > 0:
        for i in range(len(players)):
            cv2.putText(img, status[players[i]], (160 + 360 * (i // 5), 280 + 80 * (i % 5)), FONT, 2, (0, 0, 255), 3)

    return img


class Client:
    def __init__(self, name, stub):
        self.name = name
        self.stub = stub
        self.status = None
        self.role = None
        self.players = None
        self.don = None
        self.sheriff_choice = ""
        self.voted = True
        self.game = None

        chunk_size = 1024
        audio_format = pyaudio.paInt16
        channels = 1
        rate = 20000

        # initialise microphone recording
        self.p = pyaudio.PyAudio()
        self.playing_stream = self.p.open(format=audio_format, channels=channels, rate=rate,
                                          output=True, frames_per_buffer=chunk_size)
        self.recording_stream = self.p.open(format=audio_format, channels=channels, rate=rate,
                                            input=True, frames_per_buffer=chunk_size)

        self.record_on = True
        self.aux = []
        threading.Thread(target=self.__listen_for_messages).start()
        threading.Thread(target=self.refresh).start()

        while True:
            if self.game is not None and self.game != "online":
                print(self.game)
                os._exit(0)
            img = cv2.imread("bb.png")

            if self.record_on:
                if self.status is not None and self.status[self.name] == "alive":
                    self.record_on = False
                    continue
                img = draw_frame(img, "REC", self.players, self.status, self.role, self.don, self.name)
                if self.role == "sheriff":
                    cv2.putText(img, 'Your last choice mafia? ', (40, 700), FONT, 2, (0, 0, 255), 3)
                    cv2.putText(img, self.sheriff_choice, (200, 700), FONT, 2, (0, 0, 255), 3)
                cv2.imshow('Audio chat :)', img)
                try:
                    n = chat.Note(message=self.recording_stream.read(1024), name=self.name)
                    self.aux.append(n)
                    self.stub.SendNote(self.aux[-1])
                except:
                    pass
            else:
                img = draw_frame(img, "MUTE", self.players, self.status, self.role, self.don, self.name)
                if self.role == "sheriff":
                    cv2.putText(img, 'Your last choice mafia? ', (40, 700), FONT, 2, (0, 0, 255), 3)
                    cv2.putText(img, self.sheriff_choice, (500, 700), FONT, 2, (0, 0, 255), 3)
                cv2.imshow('Audio chat :)', img)

                del self.aux[:]
                self.recording_stream.stop_stream()

            q = cv2.waitKey(1)
            if q == ord('p'):
                self.record_on = False
            if q == ord('c'):
                self.record_on = True
                self.recording_stream.start_stream()
            if q == ord('q'):
                print("Thanks for testing!")
                stub.ServerStream(chat.ServerRequest(name=self.name, actv="exit"))
                os._exit(0)
            if q == ord('n'):
                n = chat.ServerRequest(name=self.name, actv="next_day")
                res = stub.ServerStream(n)
                if res.ans == "NO":
                    print(res.msg)
                else:
                    print(res.ans)
            if 47 < q < 58:
                num = q - 48
                if self.players is not None and num > len(self.players):
                    continue
                if self.don == "day":
                    if self.status[self.players[num]] == 'alive' and self.players[num] != self.name:
                        n = chat.ServerRequest(name=self.players[num], actv="choice")
                        res = stub.ServerStream(n)
                        print("Your vote:", res.ans)
                if self.don == "night(mafia_time)" and self.role == "mafia":
                    if self.status[self.players[num]] == 'alive' and self.players[num] != self.name:
                        n = chat.ServerRequest(name=self.players[num], actv="mafia_choice")
                        res = stub.ServerStream(n)
                        print("Kill:", res.ans)
                if self.don == "night(sheriff_time)" and self.role == "sheriff":
                    if self.status[self.players[num]] == 'alive' and self.players[num] != self.name:
                        n = chat.ServerRequest(name=self.players[num], actv="sheriff_choice")
                        self.sheriff_choice = stub.ServerStream(n).msg
                        print("Sheriff_work:", self.sheriff_choice)
                    else:
                        print("Error")

    def refresh(self):
        while True:
            try:
                n = chat.ServerRequest(name=self.name, actv="refresh")
                res = stub.ServerStream(n).msg
                self.players = eval(res[res.find(':', 0, len(res)) + 1:res.find('\n', 0, len(res))])
                res = res[res.find('\n', 0, len(res)) + 1:]
                self.role = res[res.find(':', 0, len(res)) + 1:res.find('\n', 0, len(res))]
                res = res[res.find('\n', 0, len(res)) + 1:]
                if res[res.find(':', 0, len(res)) + 1:res.find('\n', 0, len(res))] != "":
                    self.status = eval(res[res.find(':', 0, len(res)) + 1:res.find('\n', 0, len(res))])
                res = res[res.find('\n', 0, len(res)) + 1:]
                if res[res.find(':', 0, len(res)) + 1:res.find('\n', 0, len(res))] != "":
                    self.don = res[res.find(':', 0, len(res)) + 1:res.find('\n', 0, len(res))]
                res = res[res.find('\n', 0, len(res)) + 1:]
                if res[res.find(':', 0, len(res)) + 1:res.find('\n', 0, len(res))] != "":
                    self.game = res[res.find(':', 0, len(res)) + 1:res.find('\n', 0, len(res))]
            except:
                pass

    def __listen_for_messages(self):
        for note in self.stub.ChatStream(chat.Notename(name=self.name)):
            try:
                self.playing_stream.write(note.message)
            except:
                pass


if __name__ == '__main__':

    channel = grpc.insecure_channel(address + ':' + str(port))
    stub = rpc.ChatServerStub(channel)

    username = None
    while username is None:
        username = input("What's your username?\n")
        n = chat.ServerRequest(name=username, actv="connect")
        res = stub.ServerStream(n)
        if res.ans == "No":
            print("This username is already taken or game is full :(")
            username = None
        else:
            print("Server > Connect: ", username)

    c = Client(username, stub)
