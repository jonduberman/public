def generate_us_proxy():

	from bs4 import BeautifulSoup
	import requests
	from random import randrange
	from operator import itemgetter

	url='https://sslproxies.org/'

	header = {
		'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_2) AppleWebKit/601.3.9 (KHTML, like Gecko) Version/9.0.2 Safari/601.3.9'
	}
	response=requests.get(url,headers=header)

	soup=BeautifulSoup(response.content, 'lxml')

	table = soup.find("div", class_="table-responsive fpl-list")

	us_proxy_index_list = []
	for item in range(0,len(table.findAll('td'))):
		if table.findAll('td')[item].get_text().strip().upper() == 'UNITED STATES':
			us_proxy_index = item - 3
			us_ip_index = item - 2
			us_proxy_index_list.append(us_proxy_index)
			us_proxy_index_list.append(us_ip_index)

	all_td = table.findAll('td')
	getter = itemgetter(*us_proxy_index_list) #need to use this method to get the indexes of the us proxies to slice a list with a list
	us_proxies = list(getter(all_td)) #slicing the list of the "td" html class elements with the list of indexes of US proxies


	def get_proxies():
		#must define an empty list named proxies before calling function
		for us_proxy in range(0,len(us_proxies),2):
			try:
				proxies.append({'ip' : us_proxies[us_proxy].get_text().strip(), 'port' : us_proxies[us_proxy + 1].get_text().strip()})
			except:
				print('')
		#return proxies

	proxies = []

	get_proxies()

	rnd=randrange(len(proxies))
	randomIP=proxies[rnd]['ip']
	randomPort=proxies[rnd]['port']
	return randomIP, randomPort