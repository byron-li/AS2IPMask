#!/usr/bin/python
# coding: utf-8
# Author: BaiyangLi

import os
import re
import sys
import glob
import datetime
from six.moves import urllib
from netaddr import IPNetwork
from openpyxl import Workbook

current_time = datetime.datetime.now()
new_file_time = current_time + datetime.timedelta(days =- 2)
new_file_year = new_file_time.strftime('%Y')
new_file_month = new_file_time.strftime('%m')
new_file_date = new_file_time.strftime('%Y%m%d')

url_prefix = "http://data.caida.org/datasets/routing/routeviews-prefix2as/"
url = url_prefix + new_file_year + "/" + new_file_month + "/"

asn_dict = {}
infile_name = ""
outfile_name = "AS_IP_mapping.xlsx"
del_file="routeviews-rv2-*-*.pfx2as*"


def download_file():
	for path in glob.glob("./" + del_file):
		os.remove(path)
		print(">> old routeviews as_file has been removed")

	try:
		response = urllib.request.urlopen(url)
	except Exception as e:
		print(str(e))
		sys.exit()
	else:
		global infile_name
		file_list = re.findall(r'(routeviews-rv2-.+?\.pfx2as\.gz)', str(response.read()))
		for file in file_list:
			if new_file_date in file:
				infile_name = file
				break

	try:
		download_command = "wget " + url + infile_name
		output = os.popen(download_command, 'r')
		print(output.read())

		# urllib.request.urlretrieve(url + infile_name, infile_name, _recall_func)

	except Exception as e:
		print(str(e))
		sys.exit()
	else:
		unzip_command  = "gzip -d " + infile_name
		os.system(unzip_command)
		infile_name = infile_name.replace(".gz", "")
		

def read_source_file():
	print(">> processing file: " + infile_name)
	global asn_dict
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
	print(">> saving to excel")
	as_count = 1
	title = ['Rule Name','AS No.','Server IP']
	wb = Workbook()
	ws = wb.active
	ws.append(title)

	for as_num in asn_dict:
		for ip_mask in asn_dict[as_num]:
			row = []
			row.append(str(as_count))
			row.append(as_num)
			row.append(ip_mask)
			ws.append(row)
		as_count += 1

	wb.save(outfile_name)


def main():
	download_file()
	read_source_file()
	write_to_excel()

if __name__ == '__main__':
	main()