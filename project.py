import asyncio
import sys
import re
import aiohttp
import json
import time
import logging

list_server_name = ['Goloman', 'Hands', 'Holiday', 'Wilkes', 'Welsh']


dic_server_port = {'Goloman': 17385,
					'Hands': 17386,
					'Holiday': 17387,
					'Wilkes': 17388,
					'Welsh': 17389}

server_communicable = { 'Goloman': ['Hands', 'Holiday', 'Wilkes'],
						'Hands': ['Goloman', 'Wilkes'],
						'Holiday': ['Goloman', 'Welsh', 'Wilkes'],
						'Wilkes': ['Goloman', 'Hands', 'Holiday'],
						'Welsh': ['Holiday']}

logger = logging.getLogger('__INFO__')
logger.setLevel(logging.DEBUG)

class Server:
	class Protocol(asyncio.Protocol):
		def __init__(self, server):
			self.server = server
			self.tcp = None


		def connection_made(self, tcp):
			self.tcp = tcp

		def data_received(self, data):
			#print("entering data_received def")
			message = data.decode()
			logger.info('Data received: {!r}'.format(message))
			self.parse_message(message)

		def errorMessage(self, message):
			# divide = message.split()
			# if (len(divide) >= 10):
			# 	new_divide = divide[:-5]
			# else:
			# 	new_divide = divide[0:4]
			# new_message = ' '.join(new_divide)
			self.tcp.write(('? ' + message).encode())


		def parse_message(self, message):
			#print("entering parse_message def")
			divide = message.split()
			#print("Split message: %r" % divide)
			# when len(divide) == 9, it is an iamat message
			# when len(divide) == 4, it is a whatsat message
			if (len(divide) != 10) and (len(divide) != 4):
				#print('error here')
				self.errorMessage(message)
			else:
				if (divide[0] == 'IAMAT'):
					self.iamatInfo(divide, message)
					#logger.info("this is a IAMAT message")
				elif (divide[0] == 'WHATSAT'):

					self.whatsatInfo(divide, message)
					#logger.info("this is a WHATSAT message")
				else:
					logger.error('This is an invalid message')
					self.errorMessage(message)




		def iamatInfo(self, divide, message):
			#print("entering iamatInfo def")
			client_name = divide[1]
			location = divide[2]

			# check if the string contains characters other than +- and digits

			location_check = re.findall(r'[^ \-+\d.]', location)

			#print(location_check2)
			# if yes, report
			if(len(location_check) != 0):
				logger.error('invalid location format 1')
				self.errorMessage(message)
			else:
				location_pair = re.findall(r'([+-][\d.]+)([+-][\d.]+)', location)



            #print(location_pair)
				if len(location_pair) != 1: 
					logger.error('invalid location format')
					self.errorMessage(message)
				elif location != ''.join(location_pair[0]):
					logger.error('invalid location format')
					self.errorMessage(message)

				else:
					try:
						latitude = float(location_pair[0][0])
						longitude = float(location_pair[0][1])
						# print("latitude: ")
						# print(latitude)
						# print("longitude")
						# print(longitude)

						if latitude > 90 or latitude < -90 or longitude > 180 or longitude < -180:
							logger.error('invalid location, latitude or longitude out of range')
							self.errorMessage(message)
						else:
							self.server.info[client_name] = [latitude, longitude]
							#print("dictionary")
							#print(self.server.info[client_name])

							time_check = re.findall(r'[^ \d.]', divide[3])

							if (len(time_check) != 0):
								logger.error('invalid time format')
								self.errorMessage(message)
							else:
								time = float(divide[3])
								if time < 0:
									logger.error('invalid time format')
									self.errorMessage(message)
								else:
									self.server.info[client_name].append(time)
									#print("final dictionary")
									#print(self.server.info)


									if(len(divide) == 4):
										message = message + '0 0 0 0 0 ' + self.server.name 
										self.server.info[client_name].append(self.server.name)

										#print(self.server.info[client_name])
									else:
										self.server.info[client_name].append(divide[-1])



									self.firstline(client_name, latitude, longitude)
									asyncio.ensure_future(self.floodingAlgorithm(client_name, message))
					except ValueError:
						logger.error('invalid location format')
						self.errorMessage(message)

		def update(self, client_name, divide):
			#print(divide)
			#print("entering update def")
			#print("status is updating...")
			# if the message is sent from other server
			server_name = self.server.name
			#print("the server: " + server_name + " is being updated.")
			pos = list_server_name.index(server_name)
			divide[pos+4] = '1'
			#print("after updating, the new message is:" + ' '.join(divide))
			return' '.join(divide)


		def whatsatInfo(self, divide, message):
			
			#print("entering whatsatInfo def")
			#print(message)
			#print(divide)
			client_name = divide[1]
			try:
				radius = float(divide[2])
				no_client = int(divide[3])
			except ValueError:
				logger.error('invalid radius or number_of_client format')
				self.errorMessage(message)
			if radius < 0 or radius > 50 or no_client > 20 or no_client < 0:
				logger.error('radius or number_of_client out of range')
				self.errorMessage(message)
			else:
				asyncio.ensure_future(self.GoogleAPI(client_name, radius, no_client, message))


		def firstline(self, client_name, latitude, longitude):

			output = []
			output.append('AT')

			#print(self.server.info[client_name])
			output.append(self.server.info[client_name][-1])

			ts = time.time()
			timestamp = self.server.info[client_name][2]
			timeDifference = ts - timestamp
			output.append(str(timeDifference))

			latitude_str = str(latitude)
			longitude_str = str(longitude)
			if latitude >= 0:
				latitude_str = '+' + latitude_str
			if longitude >= 0:
				longitude_str = '+' +longitude_str
			output.append(latitude_str + longitude_str)
			output.append(str(timestamp))
			
			firstline = ' '.join(output)
			#print(firstline)

			self.tcp.write((firstline +'\n').encode())


		async def GoogleAPI(self, client_name, radius, no_client, message):
			#print("entering GoogleAPI def")
			#print(client_name)

			APIkey = 'AIzaSyACxAqsVqyYztWCKxNC2LiJHmMvPzN7gM4'
			#print("access dictionary under GoogleAPI: ")
			#print(self.server.info[client_name])
			try:
				latitude = self.server.info[client_name][0]
				longitude = self.server.info[client_name][1]
				#print("it runs here 2")
				#print(latitude, longitude)
				params = {'key' : APIkey, 'location' : str(latitude) + ',' + str(longitude), 'radius' : str(radius)}
				async with aiohttp.ClientSession() as session:
					async with session.get('https://maps.googleapis.com/maps/api/place/nearbysearch/json', params = params) as resp:
						waitingObject = await resp.json()
						divide = message.split()
						self.firstline(client_name, latitude, longitude)
						#print("it runs here 3")
						#print(json.dumps(waitingObject))
						waitingObject['results'] = waitingObject['results'][:no_client]
						self.tcp.write(json.dumps(waitingObject).encode())
						self.tcp.write(('\n\n').encode())
			except KeyError:
				logger.error('unable to access information')
				self.tcp.write(('? ' + message).encode())


		async def floodingAlgorithm(self, client_name, message):
			#print("entering floodingAlgorithm def")

			#print("the current message entering the floodingAlgorithm is: " + message + " and the client name is: " + client_name)
			#print("the current server is:" + self.server.name)
			# if a message is updated on all servers
				
			divide = message.split()
			#print(message)
			if(len(self.server.info[client_name]) !=4):
				self.server.info[client_name].append(divide[-1])
			message = self.update(client_name, divide)
			logger.info('message received')
			

			message_content = divide[:3]
			#print(message_content)
			update_status = divide[4:9]
			#print(update_status)
			if update_status == ['1', '1', '1', '1', '1']:
				return
			talkable = server_communicable[self.server.name]


			
			for e in talkable:
				pos = list_server_name.index(e)
				#print(e, pos)

				# if the corresponding server is not updated
				if update_status[pos] == '0':
					# then open the connection and update
					try:
						reader, writer = await asyncio.open_connection('127.0.0.1', dic_server_port[e], loop = self.server.loop)
						#print('From ' + self.server.name + ' to ' + e +' sending message: ' + message)
						#writer.write(('From ' + self.server.name + ' to ' + e +' sending message: ' + message).encode())
						divide[pos + 4] = '1'
						message = ' '.join(divide)
						writer.write(message.encode())
						writer.close()
					except OSError:
						logger.error("server " + e + " fails")


	def __init__(self, name, loop):
		self.name = name
		self.loop = loop
		self.coro = loop.create_server(lambda: self.Protocol(self), '127.0.0.1', port = dic_server_port[name])
		#self.info = {client_name : [latitude, longitude, time, [update_list]]}
		self.info = {}



def main():
	if len(sys.argv) != 2:
		print("invalid argument length.")
		exit(1)
	else:
		name = sys.argv[1]
		if name not in list_server_name:
			print("invalid server name.")
			exit(1)
		else:
			loop = asyncio.get_event_loop()
			server_object = Server(name, loop)
			fh = logging.FileHandler(name+'.log')
			fh.setLevel(logging.DEBUG)

			ch = logging.StreamHandler()
			ch.setLevel(logging.ERROR)
			# create formatter and add it to the handlers
			formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
			fh.setFormatter(formatter)
			ch.setFormatter(formatter)
			# add the handlers to the logger
			logger.addHandler(fh)
			logger.addHandler(ch)


			logger.info('Server ' + name + ' is working...')
			server = loop.run_until_complete(server_object.coro)

# Serve requests until Ctrl+C is pressed
			print('Serving on {}'.format(server.sockets[0].getsockname()))

			try:
				loop.run_forever()
			except KeyboardInterrupt:
				pass
			logger.info('Server ' + name + 'shuts down')
			loop.close()


if __name__ == "__main__":
	main()