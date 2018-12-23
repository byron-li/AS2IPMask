#!/usr/bin/python
# coding=utf-8
# Author: BaiyangLi

import os
import re
import sys
import time
import gzip
import glob
import socket
import logging
from collections import deque
from six.moves import urllib
from netaddr import IPNetwork
from openpyxl import Workbook
from configparser import ConfigParser


download_file = ""
pfx2as_log = "pfx2as-creation.log"

asn_ipmask = {}
asn_info = {}

log_name = "as2ipmask.log"
log_format = "%(asctime)s [%(levelname)s] %(message)s"
logging.basicConfig(level=logging.DEBUG, filemode='a', format=log_format, filename=log_name)

socket.setdefaulttimeout(30)


def _callback_func(num, block_size, total_size):
	percent = float(num * block_size)/float(total_size) * 100.0

	if((percent - 100) >= 0):
		sys.stdout.write("\r>> downloading %s %.1f%%\n" % (download_file, 100))
	else:
		sys.stdout.write("\r>> downloading %s %.1f%%" % (download_file, percent))
		sys.stdout.flush()


def tail(filename, n):
	return deque(open(filename), n)


def download_pfx2as_file(log_url, prefix_url, del_filename):
	print(">> check pfx2as_file version")

	global download_file
	latest_file = ""

	try:
		urllib.request.urlretrieve(log_url, pfx2as_log)

	except Exception as e:
		print(str(e))
		logging.error(str(e))
		logging.error("Can not check pfx2as file version, program exit.")
		sys.exit()

	latest = tail(pfx2as_log, 1)
	suffix_url = latest[0].split()[2]

	download_file = suffix_url.split('/')[2]
	latest_file = download_file.replace(".gz", "")

	if os.path.isfile(latest_file):
		pass
	else:
		if glob.glob(del_filename):
			for path in glob.glob(del_filename):
				os.remove(path)
			print(">> old routeviews files have been removed")

		try:
			urllib.request.urlretrieve(prefix_url + suffix_url, download_file, _callback_func)

		except Exception as e:
			print()
			print(str(e))
			logging.error(str(e))
			sys.exit()

		else:
			unzip = gzip.GzipFile(mode="rb", fileobj=open(download_file, 'rb'))
			open(latest_file, "wb").write(unzip.read())

	read_pfx2as_file(latest_file)


def read_pfx2as_file(filename):
	global asn_ipmask
	print(">> processing file: " + filename)

	with open(filename, "r") as input_file:
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
					if as_num in asn_ipmask.keys():
						if str(sub_ip_mask) in asn_ipmask[as_num]:
							pass
						else:
							asn_ipmask[as_num].append(str(sub_ip_mask))
					else:
						asn_ipmask[as_num] = []
						asn_ipmask[as_num].append(str(sub_ip_mask))
			
			infile_line = input_file.readline().strip('\n')


def download_asn_info():
	global asn_info
	global download_file

	download_file = "asn_info"
	del_asn_info = "asn_info_*"
	asn_info_url = "https://www.cidr-report.org/as2.0/autnums.html"
	asn_info_file = download_file + "_" + time.strftime("%Y%m%d", time.localtime())

	if os.path.isfile(asn_info_file):
		pass
	
	else:
		try:
			urllib.request.urlretrieve(asn_info_url, download_file, _callback_func)

		except Exception as e:
			print()
			print(str(e))
			logging.error(str(e))

			if(glob.glob(del_asn_info)):
				logging.error("Failed to download the latest ASN_INFO File, use the previous version.")
				asn_info_file = glob.glob(del_asn_info)[0]

			else:
				logging.error("Failed to download the latest ASN_INFO File and no previous version exists. No ASN_INFO records in xlsx file.")
				asn_info_file = ""

		else:
			if glob.glob(del_asn_info):
				for path in glob.glob(del_asn_info):
					os.remove(path)
			print(">> old asn_info file has been removed")
			os.rename(download_file, asn_info_file)

	if(asn_info_file):
		with open(asn_info_file, "r", encoding = "ISO-8859-1") as input_file:
			infile_line = input_file.readline().strip('\n')
			pattern = re.compile(r'<a href="/cgi-bin/as-report\?as=.*">AS(.*)</a>(.*)')

			while(infile_line):
				result = pattern.findall(infile_line)
				if(result):
					key = result[0][0].strip()
					value = result[0][1].strip()
					asn_info[key] = value

				infile_line = input_file.readline().strip('\n')


def write_to_excel(conf_list):
	print(">> saving configuration to excel")

	outfile_name = "AS_IP_mapping.xlsx"
	title = ['AS Name', 'ASN', 'Server IP', 'Details', 'Country Code']
	wb = Workbook()
	ws = wb.active
	ws.append(title)

	for asn in conf_list:
		asn = asn.strip()

		if(asn):
			if asn in asn_ipmask.keys():
				as_name = ""
				details = ""
				country_code = ""

				if asn in asn_info.keys():
					details = asn_info[asn]
					asn_info_list1 = details.split(" - ")
					asn_info_list2 = details.split(", ")

					if(len(asn_info_list1) > 1):
						as_name = asn_info_list1[0]
					else:
						as_name = asn_info_list2[0]

					country_code = asn_info_list2[-1]

				for ip_mask in asn_ipmask[asn]:
					row = []
					row.append(as_name)
					row.append(asn)
					row.append(ip_mask)
					row.append(details)
					row.append(country_code)
					ws.append(row)
					
			else:
				print("Warning: AS" + str(asn) + " is not in CAIDA file, Your configuration may not take effect!")
				logging.warning("AS" + str(asn) + " is not in CAIDA file, Your configuration may not take effect!")
		else:
			continue

	try:
		wb.save(outfile_name)

	except Exception as e:
		print(str(e))
		logging.error(str(e))
		sys.exit()


def main():
	print(">> reading config file")

	prefix_v4_url = "http://data.caida.org/datasets/routing/routeviews-prefix2as/"
	prefix_v6_url = "http://data.caida.org/datasets/routing/routeviews6-prefix2as/"

	log_v4_url = prefix_v4_url + pfx2as_log
	log_v6_url = prefix_v6_url + pfx2as_log

	del_v4_file = "routeviews-rv2-*-*.pfx2as*"
	del_v6_file = "routeviews-rv6-*-*.pfx2as*"

	cfg = ConfigParser()
	asn_conf = []
	
	try:
		cfg.read("./conf/config.ini")
		ip_ver = cfg.get("IP", "IPVERSION")
		asn_conf = cfg.get("ASN", "ASNUMBER").split(",")

	except Exception as e:
		print(str(e) + ", check config.ini.")
		logging.error(str(e) + ", check config.ini.")
		sys.exit()

	if(ip_ver == "4"):
		download_pfx2as_file(log_v4_url, prefix_v4_url, del_v4_file)

	elif(ip_ver == "6"):
		download_pfx2as_file(log_v6_url, prefix_v6_url, del_v6_file)

	elif(ip_ver.lower() == "all"):
		download_pfx2as_file(log_v4_url, prefix_v4_url, del_v4_file)
		download_pfx2as_file(log_v6_url, prefix_v6_url, del_v6_file)

	else:
		print("IP version value error, check config.ini.")
		logging.error("IP version value error, check config.ini.")
		sys.exit()

	download_asn_info()
	write_to_excel(asn_conf)
	os.system("pause")

if __name__ == '__main__':
	main()