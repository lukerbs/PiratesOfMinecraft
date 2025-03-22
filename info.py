from mcstatus import JavaServer

file = open("servers.txt", "r")
count = 0

ips = []
while True:
    count += 1
    line = file.readline()
    if not line:
        break
    ips.append(line.strip())

for ip in ips:
    try:
        server = JavaServer.lookup(ip)
        status = server.status()
        print(ip)
        print("Players online:", status.players.online)
        print("Version:", status.version.name)
        print("")
    except:
        pass
