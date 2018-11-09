#!/usr/bin/python
# coding: utf-8
# Author: BaiyangLi

import os
import re
import sys
import gzip
import glob
import socket
import logging
from collections import deque
from six.moves import urllib
from netaddr import IPNetwork
from openpyxl import Workbook
from configparser import ConfigParser


creation_log = "pfx2as-creation.log"

prefix_v4_url = "http://data.caida.org/datasets/routing/routeviews-prefix2as/"
prefix_v6_url = "http://data.caida.org/datasets/routing/routeviews6-prefix2as/"

log_v4_url = prefix_v4_url + creation_log
log_v6_url = prefix_v6_url + creation_log

asn_dict = {}
conf_dict = {}

conf_name = "as.conf"
infile_name = ""
outfile_name = "AS_IP_mapping.xlsx"

del_v4_file = "routeviews-rv2-*-*.pfx2as*"
del_v6_file = "routeviews-rv6-*-*.pfx2as*"

log_name = "as2ipmask.log"
log_format = "%(asctime)s [%(levelname)s] %(message)s"
logging.basicConfig(level=logging.DEBUG, filemode='a', format=log_format, filename=log_name)

socket.setdefaulttimeout(90)


def _callback_func(num, block_size, total_size):
	percent = float(num * block_size)/float(total_size) * 100.0

	if((percent - 100) >= 0):
		sys.stdout.write("\r>> downloading %s %.1f%%\n" % (infile_name, 100))
	else:
		sys.stdout.write("\r>> downloading %s %.1f%%" % (infile_name, percent))
		sys.stdout.flush()


def tail(filename, n):
	return deque(open(filename), n)


def read_conf_file():
	global conf_dict
	print(">> reading config file")

	try:
		with open("./conf/as.conf", "r") as conf_file:
			conf_header = conf_file.readline().strip('\n')
			conf_header = "".join(conf_header.split(','))
			conf_header = "".join(conf_header.split())

			if(conf_header == "RuleNameASN"):
				conf_line = conf_file.readline().strip('\n')

				while(conf_line):
					conf_line = "".join(conf_line.split())
					line_list = conf_line.split(',')
					
					rule_name = line_list[0]
					asn = line_list[1]
					try:
						int(asn)
					except ValueError as e:
						print(str(e))
						logging.error("ASN format error: " + str(e))
						sys.exit()
					else:
						if rule_name in conf_dict.keys():
							if asn in conf_dict[rule_name]:
								pass
							else:
								conf_dict[rule_name].append(asn)
						else:
							conf_dict[rule_name] = []
							conf_dict[rule_name].append(asn)
					
					conf_line = conf_file.readline().strip('\n')

			else:
				print("as.conf file header format error, please check and reopen.")
				logging.error("as.conf file header format error, check as.conf.")
				sys.exit()

	except IOError as e:
		print(e)
		logging.error(str(e))
		sys.exit()


def download_file(log_url, prefix_url, del_filename):
	global infile_name
	print(">> check pfx2as_file version")

	try:
		urllib.request.urlretrieve(log_url, creation_log)

	except Exception as e:
		print(str(e))
		logging.error(str(e))
		sys.exit()

	d = tail(creation_log, 1)
	suffix_url = d[0].split()[2]

	infile_name = suffix_url.split('/')[2]
	unzipped_name = infile_name.replace(".gz", "")

	if os.path.isfile(unzipped_name):
		infile_name = unzipped_name
	else:
		if glob.glob("./" + del_filename):
			for path in glob.glob("./" + del_filename):
				os.remove(path)
			print(">> old routeviews as_file has been removed")

		try:
			urllib.request.urlretrieve(prefix_url + suffix_url, infile_name, _callback_func)

		except Exception as e:
			print()
			print(str(e))
			logging.error(str(e))
			sys.exit()

		else:
			unzip = gzip.GzipFile(mode="rb", fileobj=open(infile_name, 'rb'))
			infile_name = unzipped_name
			open(infile_name, "wb").write(unzip.read())


def read_pfx2as_file():
	global asn_dict
	print(">> processing file: " + infile_name)

	with open(infile_name, "r") as input_file:
		infile_line = input_file.readline().strip('\n')

		while(infile_line):
			as_list = []
			sub_ip_list = []
			line_list = infile_line.split()
			
			ip = line_list[0]
			mask = line_list[1]
			asn = line_list[2]

			if(int(mask) < 16):
				ip_mask = IPNetwork(ip + "/" + mask)
				sub_ip_list = list(ip_mask.subnet(16))
			else:
				sub_ip_list.append(ip + "/" + mask)

			if ',' in asn or '_' in asn:
				as_list = re.split('[,_]', asn)
			else:
				as_list.append(asn)

			for as_num in as_list:
				for sub_ip_mask in sub_ip_list:
					if as_num in asn_dict.keys():
						if str(sub_ip_mask) in asn_dict[as_num]:
							pass
						else:
							asn_dict[as_num].append(str(sub_ip_mask))
					else:
						asn_dict[as_num] = []
						asn_dict[as_num].append(str(sub_ip_mask))
			
			infile_line = input_file.readline().strip('\n')


def write_to_excel():
	print(">> saving configuration to excel")
	as_count = 1
	title = ['Rule Name','ASN','Server IP']
	wb = Workbook()
	ws = wb.active
	ws.append(title)

	for rule_name in conf_dict:
		for asn in conf_dict[rule_name]:
			if asn in asn_dict.keys():
				for ip_mask in asn_dict[asn]:
					row = []
					row.append(rule_name)
					row.append(asn)
					row.append(ip_mask)
					ws.append(row)
			else:
				print("Warning: AS_num is not in CAIDA file, Your configuration may not take effect!")
				logging.warning("ASN " + str(asn) + " is not in CAIDA file, Your configuration may not take effect!")

	try:
		wb.save(outfile_name)

	except Exception as e:
		print(str(e))
		logging.error(str(e))
		sys.exit()


def main():
	cfg = ConfigParser()

	try:
		cfg.read("./conf/config.ini")
		option = cfg.get("ip", "ip_version")

	except Exception as e:
		print(str(e) + ", check config.ini.")
		logging.error(str(e) + ", check config.ini.")
		sys.exit()

	read_conf_file()

	if(option == "4"):
		download_file(log_v4_url, prefix_v4_url, del_v4_file)
		read_pfx2as_file()

	elif(option == "6"):
		download_file(log_v6_url, prefix_v6_url, del_v6_file)
		read_pfx2as_file()

	elif(option.lower() == "all"):
		download_file(log_v4_url, prefix_v4_url, del_v4_file)
		read_pfx2as_file()
		download_file(log_v6_url, prefix_v6_url, del_v6_file)
		read_pfx2as_file()

	else:
		print("IP version value error, check config.ini.")
		logging.error("IP version value error, check config.ini.")
		sys.exit()

	write_to_excel()
	os.system("pause")

if __name__ == '__main__':
	main()
