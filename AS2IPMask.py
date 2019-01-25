#!/usr/bin/python
# coding=utf-8
# Author: BaiyangLi

import os
import re
import sys
import ssl
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

asn_info = {}

socket.setdefaulttimeout(30)
ssl._create_default_https_context = ssl._create_unverified_context

localtime = time.strftime("%Y%m%d", time.localtime())

dir_path = os.path.realpath(sys.argv[0])
dir_path = dir_path.replace(dir_path.split(os.sep)[-1], "")

download_file = ""
pfx2as_log = "pfx2as-creation.log"

log_name = dir_path + "as2ipmask.log"
log_format = "%(asctime)s [%(levelname)s] %(message)s"
logging.basicConfig(level=logging.DEBUG, filemode='a', format=log_format, filename=log_name)


def _callback_func(num, block_size, total_size):
	percent = float(num * block_size)/float(total_size) * 100.0

	if((percent - 100) >= 0):
		sys.stdout.write("\r>> downloading %s %.1f%%\n" % (download_file, 100))
	else:
		sys.stdout.write("\r>> downloading %s %.1f%%" % (download_file, percent))
		sys.stdout.flush()


def tail(filename, n):
	return deque(open(filename), n)


def read_pfx2as_file(filename, asn_ipmask):
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


def download_pfx2as_file(log_url, prefix_url, del_filename):
	print(">> check pfx2as_file version")

	global download_file
	latest_file = ""

	try:
		urllib.request.urlretrieve(log_url, dir_path+pfx2as_log)

	except Exception as e:
		print(str(e))
		logging.error(str(e))
		logging.error("Can not check pfx2as file version, program exit.")
		sys.exit()

	latest = tail(dir_path+pfx2as_log, 1)

	try:
		suffix_url = latest[0].split()[2]
		download_file = dir_path + suffix_url.split('/')[2]
		latest_file = download_file.replace(".gz", "")

	except Exception as e:
		print(str(e))
		logging.error(str(e))
		logging.error("Can not check pfx2as file version, program exit.")
		sys.exit()

	if os.path.isfile(latest_file):
		pass
	else:
		if glob.glob(del_filename):
			for path in glob.glob(del_filename):
				os.remove(path)
			print(">> old routeviews files have been removed")

		try:
			urllib.request.urlretrieve(prefix_url+suffix_url, download_file, _callback_func)

		except Exception as e:
			print()
			print(str(e))
			logging.error(str(e))
			sys.exit()

		else:
			unzip = gzip.GzipFile(mode="rb", fileobj=open(download_file, 'rb'))
			open(latest_file, "wb").write(unzip.read())

	return latest_file


def read_asn_info(filename):
	print(">> processing file: " + filename)

	global asn_info
	asn_info.clear()

	with open(filename, "r", encoding="ISO-8859-1") as input_file:
		infile_line = input_file.readline().strip('\n')
		pattern = re.compile(r'<a href="/cgi-bin/as-report\?as=.*">AS(.*)</a>(.*)')

		while(infile_line):
			result = pattern.findall(infile_line)
			if(result):
				key = result[0][0].strip()
				value = result[0][1].strip()
				asn_info[key] = value

			infile_line = input_file.readline().strip('\n')


def download_asn_info():
	global download_file

	asn_info_file = ""
	download_file = dir_path + "asn_info"
	del_asn_info = dir_path + "asn_info_*"
	asn_info_latest = download_file + "_" + localtime

	asn_info_url = "https://www.cidr-report.org/as2.0/autnums.html"

	if os.path.isfile(asn_info_latest):
		asn_info_file = asn_info_latest
	
	else:
		try:
			urllib.request.urlretrieve(asn_info_url, download_file, _callback_func)
			asn_info_file = download_file

		except Exception as e:		#	if download fails
			print()
			print(str(e))
			logging.error(str(e))

			if(glob.glob(del_asn_info)):
				logging.error("Failed to download the latest ASN_INFO File, use the previous version.")
				asn_info_file = glob.glob(del_asn_info)[0]

			else:
				logging.error("Failed to download the latest ASN_INFO File and no previous version exists. No ASN_INFO records in xlsx file.")
				asn_info_file = ""
			
			os.remove(download_file)

	try:
		if(asn_info_file):
			read_asn_info(asn_info_file)

	except Exception as e:		#	if reading latest file fails
		print(str(e))
		logging.error(str(e))

		if(glob.glob(del_asn_info)):
			logging.error("Failed to read the latest ASN_INFO File, use the previous version.")
			asn_info_file = glob.glob(del_asn_info)[0]
			read_asn_info(asn_info_file)

		else:
			logging.error("Failed to read the latest ASN_INFO File and no previous version exists. No ASN_INFO records in xlsx file.")

	else:
		if(asn_info_file == download_file):
			if glob.glob(del_asn_info):
				for path in glob.glob(del_asn_info):
					os.remove(path)
				print(">> old asn_info file has been removed")

			os.rename(asn_info_file, asn_info_latest)


def lookup_asn_info(asn):
	asn_item_info = {}
	asn_item_info["as_name"] = ""
	asn_item_info["details"] = ""
	asn_item_info["country_code"] = ""

	if asn in asn_info.keys():
		asn_item_info["details"] = asn_info[asn]
		asn_info_list1 = asn_info[asn].split(" - ")
		asn_info_list2 = asn_info[asn].split(", ")

		if(len(asn_info_list1) > 1):
			asn_item_info["as_name"] = asn_info_list1[0]
		else:
			if(len(asn_info_list2) > 1):
				asn_item_info["as_name"] = asn_info_list2[0]

		if(len(asn_info_list2) > 1):
			asn_item_info["country_code"] = asn_info_list2[-1]

	return asn_item_info


def write_to_excel(conf_list, asn_ipmask, outfile_name, del_filename):
	if glob.glob(del_filename):
		for path in glob.glob(del_filename):
			os.remove(path)
		print(">> old as_ip_mapping xlsx file has been removed")

	print(">> saving configuration to excel")

	title = ['AS Name', 'ASN', 'Server IP', 'Details', 'Country Code']
	wb = Workbook(write_only=True)
	ws = wb.create_sheet()
	ws.append(title)

	if((len(conf_list) == 1) & (conf_list[0].strip().lower() == "all")):
		for asn in asn_ipmask.keys():
			an_asn_info = lookup_asn_info(asn)

			for ip_mask in asn_ipmask[asn]:
				row = []
				row.append(an_asn_info["as_name"])
				row.append(asn)
				row.append(ip_mask)
				row.append(an_asn_info["details"])
				row.append(an_asn_info["country_code"])
				ws.append(row)

	else:
		for asn in conf_list:
			asn = asn.strip()

			if(asn):
				if asn in asn_ipmask.keys():
					an_asn_info = lookup_asn_info(asn)

					for ip_mask in asn_ipmask[asn]:
						row = []
						row.append(an_asn_info["as_name"])
						row.append(asn)
						row.append(ip_mask)
						row.append(an_asn_info["details"])
						row.append(an_asn_info["country_code"])
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

	del_v4_file = dir_path + "routeviews-rv2-*-*.pfx2as*"
	del_v6_file = dir_path + "routeviews-rv6-*-*.pfx2as*"

	del_v4_xlsx = dir_path + "AS_IP_mapping_v4_*.xlsx"
	del_v6_xlsx = dir_path + "AS_IP_mapping_v6_*.xlsx"

	cfg = ConfigParser()
	
	out_file_v4 = dir_path + "AS_IP_mapping_v4_" + localtime + ".xlsx"
	out_file_v6 = dir_path + "AS_IP_mapping_v6_" + localtime + ".xlsx"
	pfx2as_file_v4 = ""
	pfx2as_file_v6 = ""
	
	asn_ipmask_v4 = {}
	asn_ipmask_v6 = {}
	asn_conf = []
	
	try:
		cfg.read(dir_path + "conf" + os.sep + "config.ini")
		ip_ver = cfg.get("IP", "IPVERSION")
		asn_conf = cfg.get("ASN", "ASNUMBER").split(",")

	except Exception as e:
		print(str(e) + ", check config.ini.")
		logging.error(str(e) + ", check config.ini.")
		sys.exit()

	download_asn_info()

	if(ip_ver == "4"):
		pfx2as_file_v4 = download_pfx2as_file(log_v4_url, prefix_v4_url, del_v4_file)
		read_pfx2as_file(pfx2as_file_v4, asn_ipmask_v4)
		write_to_excel(asn_conf, asn_ipmask_v4, out_file_v4, del_v4_xlsx)

	elif(ip_ver == "6"):
		pfx2as_file_v6 = download_pfx2as_file(log_v6_url, prefix_v6_url, del_v6_file)
		read_pfx2as_file(pfx2as_file_v6, asn_ipmask_v6)
		write_to_excel(asn_conf, asn_ipmask_v6, out_file_v6, del_v6_xlsx)

	elif(ip_ver.lower() == "all"):
		pfx2as_file_v4 = download_pfx2as_file(log_v4_url, prefix_v4_url, del_v4_file)
		pfx2as_file_v6 = download_pfx2as_file(log_v6_url, prefix_v6_url, del_v6_file)
		read_pfx2as_file(pfx2as_file_v4, asn_ipmask_v4)
		read_pfx2as_file(pfx2as_file_v6, asn_ipmask_v6)
		write_to_excel(asn_conf, asn_ipmask_v4, out_file_v4, del_v4_xlsx)
		write_to_excel(asn_conf, asn_ipmask_v6, out_file_v6, del_v6_xlsx)

	else:
		print("IP version value error, check config.ini.")
		logging.error("IP version value error, check config.ini.")
		sys.exit()

	os.system("pause")


if __name__ == '__main__':
	main()