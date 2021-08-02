from mcstatus import MinecraftServer
import random

def random_address():
	address = ".".join(map(str, (random.randint(0, 255) for _ in range(4)))) + ':25565'
	return address

print('Searching for open servers...')
while True:
	# get a random ip address
	address = random_address()
	print(address)
	try:
		server = MinecraftServer.lookup(address)
		status = server.status()
		print(status)
		print(address)
		print('')
		file = open('servers.txt', 'a')
		file.write(address + '\n')
		file.close()
	except Exception as e:
		print(e)
		pass
	print('')

