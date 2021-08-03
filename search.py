from mcstatus import MinecraftServer
import concurrent.futures
import random
import time

def random_address():
	address = ".".join(map(str, (random.randint(0, 255) for _ in range(4)))) + ':25565'
	return address

def query_address(address):
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
	return

print('Searching for open servers...')
while True:
	ip_addresses = []
	for i in range(1000):
		ip_addresses.append(random_address())

	with concurrent.futures.ThreadPoolExecutor() as executor:
		executor.map(query_address, ip_addresses)