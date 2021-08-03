from mcstatus import MinecraftServer
import concurrent.futures
import random
import time

def random_address():
	address = ".".join(map(str, (random.randint(0, 255) for _ in range(4)))) + ':25565'
	return address

def query_address(address):
	try:
		server = MinecraftServer.lookup(address)
		status = server.status()
		file = open('servers.txt', 'a')
		file.write(address + '\n')
		file.close()
		print(address + ' ✅')
	except Exception as e:
		print(address + ' ❌')
		pass
	print('')
	return

print('Searching for open servers...')
while True:
	ip_addresses = []
	for i in range(250):
		ip_addresses.append(random_address())

	with concurrent.futures.ThreadPoolExecutor() as executor:
		executor.map(query_address, ip_addresses)