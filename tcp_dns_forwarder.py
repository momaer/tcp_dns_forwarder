#!/usr/bin/python

import socket
import SocketServer
import struct
import pylru

local_addr = "127.0.0.1"
dns = "8.8.8.8"
special_domains = ['wanmei.com', 'actself.me']
special_dns = "10.255.243.81"
cache = None

class ThreadingUDPServer(SocketServer.ThreadingMixIn, SocketServer.UDPServer):
    pass

class ThreadedUDPRequestHandler(SocketServer.BaseRequestHandler):

    daemon_threads = True
    allow_reuse_address = True

    def handle(self):
        data = self.request[0]
        socket = self.request[1]
        client_address = self.client_address
        transfer(data, client_address, socket)

def transfer(data, addr, socket):
    query_type = struct.unpack("!h", data[-4:-2])[0]
    query_domain = byte_to_domain( data[12:-4] )

    #print "type:%d, domain:%s" % (query_type, query_domain)

    response = query_from_dns(data)
    if response is None:
        print "dns query failed."
    else:
        socket.sendto(response[2:], addr)

def query_from_dns(data):
    response = None
    
    global cache
    key = data[2:].encode('hex')
    if key in cache:
        response = cache[key]
        return response[0:2] + data[0:2] + response[4:]

    query_domain = byte_to_domain( data[12:-4] )

    special = False

    for i in special_domains:
        if query_domain.rfind(i) != -1:
            #print "special domain"
            special = True
            break

    if special is False:
        length = struct.pack("!h", len(data))
        send_data = length + data
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(3)
        try:
            s.connect( (dns, 53) )
            s.sendall(send_data)
            response = s.recv(1024)
           
            cache[key] = response

            return response
        except socket.timeout:
            print "query time out."
            return None
        except socket.error:
            return None
        finally:
            s.close()
    else:
        #use udp instead of tcp
        length = struct.pack("!h", len(data))
        send_data = length + data
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(3)
        try:
            s.connect( (special_dns, 53) )
            s.sendall(send_data)
            response = s.recv(1024)

            cache[key] = response

            return response
        except socket.timeout:
            print "query time out."
            return None
        except socket.error:
            return None
        finally:
            s.close()

def byte_to_domain(data):
    domain = ''
    i = 0
    length = struct.unpack("!B", data[0:1])[0]

    while length != 0:
        i += 1
        domain += data[i : i+length]
        i += length
        length = struct.unpack("!B", data[i : i+1])[0]
        if length != 0:
            domain += '.'

    return domain

def main():
    print "local_addr:%s dns:%s" % (local_addr, dns)

    size = 1024
    global cache
    cache = pylru.lrucache(size)

    server = ThreadingUDPServer((local_addr, 53), ThreadedUDPRequestHandler)
    server.serve_forever()

if __name__ == "__main__":
    main()
