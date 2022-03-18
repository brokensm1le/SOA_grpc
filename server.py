import os
from concurrent import futures
import random

import grpc

import test_pb2 as chat
import test_pb2_grpc as rpc


class ChatServer(rpc.ChatServerServicer):
    def __init__(self):
        self.Status = None
        self.Roles = None
        self.chats = []
        self.names = []
        self.vote_nd = []
        self.vote_kill = []
        self.don = None
        self.mafia_victum = None
        self.game = None
        self.count_alive = 0

    def ChatStream(self, request: chat.Notename, context):
        """
        This is a response-stream type call. This means the server can keep sending messages
        Every client opens this connection and waits for server to send new messages
        :param request:
        :param context:
        :return:
        """
        lastindex = len(self.chats)
        while True:
            if len(self.chats) < lastindex:
                lastindex = len(self.chats)

            while len(self.chats) > lastindex:
                n = self.chats[lastindex]
                lastindex += 1
                if n.name != request.name:
                    yield n

    def SendNote(self, request: chat.Note, context):
        """
        This method is called when a clients sends a Note to the server.
        :param request:
        :param context:
        :return:
        """
        if self.don != "night":
            self.chats.append(request)
        return chat.Empty()

    def ServerStream(self, request, context):
        if request.actv == "connect":
            if request.name not in self.names:
                self.names.append(request.name)
                print("Connecting:", request.name)
                print("Players", ', '.join(map(str, self.names)))
                if len(self.names) == 4:
                    self.Game_start()
                return chat.ServerResponse(ans="OK")
            else:
                return chat.ServerResponse(ans="No")
        elif request.actv == 'players':
            msg = ', '.join(map(str, self.names))
            return chat.ServerResponse(ans="OK", msg=msg)
        elif request.actv == 'exit':
            self.names.remove(request.name)
            print("Disconnect: ", request.name)
            return chat.ServerResponse(ans="OK")
        elif request.actv == 'refresh':
            res = "Players:" + str(self.names) + "\n"
            res += "Role:"
            if self.Roles != None:
                res += self.Roles[request.name]
            res += "\n"
            res += "Status:"
            if self.Status != None:
                res += str(self.Status)
            res += "\n"
            res += "Don:"
            if self.don != None:
                res += self.don
            res += "\n"
            res += "Game:"
            if self.game != None:
                res += self.game
            res += "\n"
            return chat.ServerResponse(ans="OK", msg=res)
        elif request.actv == 'next_day':
            if self.don[:3] != "day":
                return chat.ServerResponse(ans="NO", msg="Now, isn't day")
            if request.name not in self.vote_nd:
                self.vote_nd.append(request.name)
                if len(self.names) == len(self.vote_nd):
                    self.don = "night(mafia_time)"
                    self.chats.clear()
                return chat.ServerResponse(ans="OK")
        elif request.actv == 'choice':
            if self.don == "day":
                self.vote_kill.append(request.name)
                print("COUNT ALIVE", self.vote_kill)
                if len(self.vote_kill) == self.count_alive:
                    vk_set = set(self.vote_kill)
                    print(vk_set)
                    mc = None
                    qty_mc = 0
                    flag = True
                    for item in vk_set:
                        qty = self.vote_kill.count(item)
                        if qty > qty_mc:
                            qty_mc = qty
                            mc = item
                            flag = True
                        elif qty == qty_mc:
                            flag = False
                    print(flag, mc)
                    if flag:
                        self.Status[mc] = "kill"
                        self.count_alive -= 1
                        if self.Roles[mc] == "mafia":
                            self.Game_close("civilian_win")
                    self.don = "night(mafia_time)"

                return chat.ServerResponse(ans="OK", msg=request.name)
        elif request.actv == 'mafia_choice':
            if self.don == 'night(mafia_time)':
                self.mafia_victum = request.name
                self.don = 'night(sheriff_time)'
                self.count_alive -= 1
                return chat.ServerResponse(ans="OK")
        elif request.actv == 'sheriff_choice':
            if self.don == 'night(sheriff_time)':
                self.don = 'day'
                self.Status[self.mafia_victum] = "killed"
                print("COUNT ALIVE",self.count_alive )
                if self.count_alive == 2:
                    self.Game_close("mafia_win")
                if self.Roles[request.name] == "mafia":
                    return chat.ServerResponse(ans="OK", msg="Yes")
                else:
                    return chat.ServerResponse(ans="OK", msg="No")

    def Game_start(self):
        self.count_alive = len(self.names)
        self.Roles = dict.fromkeys(self.names, "civilian")
        print(len(self.names))
        j, k = random.sample((0, len(self.names) - 1), 2)
        print(k, j, self.names, self.names[j], self.names[k])
        self.Roles[self.names[j]] = "mafia"
        self.Roles[self.names[k]] = "sheriff"
        self.Status = dict.fromkeys(self.names, "alive")
        self.don = "day0"
        self.game = "online"
        print(self.Roles)
        print(self.Status)

    def Game_close(self, result):
        self.game = result

if __name__ == '__main__':
    port = 9090
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=15))
    rpc.add_ChatServerServicer_to_server(ChatServer(), server)
    print('Starting server. Listening...')
    server.add_insecure_port('[::]:' + str(port))
    server.start()
    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        server.stop(None)
        print('\nServer is closed.')
        os._exit(0)
