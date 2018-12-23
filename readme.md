## AS2IPMask:

*	从 [CAIDA](https://www.caida.org/data/routing/routeviews-prefix2as.xml) 获取最新 pfx2as 数据
*	从 [CIDR](http://www.cidr-report.org/as2.0/) 获取ASN注册信息
*	根据配置 ASN, 输出其 IP 地址段 (掩码格式转换为>=16) 及相关注册信息, 保存为 xlsx 格式文件

### 配置

*	配置文件位于 conf 目录下
	*	config.ini: 程序配置文件, 包含 [IP], [ASN] 两 section
		*	IP Sect: 指定获取对应ASN对应IP段: IPv4(4) /IPv6(6)/ 全部(all)
		*	ASN Sect: 输入 ASN, 逗号分隔

###	逻辑
*	从配置文件中读取 ASN, 检查 ASN 是否在 pfx2as 中
	*	若文件中存在该 ASN, 填充 ASN info, 写入 xlsx
	*	若不存在, 记入日志, 不写入结果文件


### 输出

*	全量式输出, 覆盖上一次结果, 输出文件名: AS_IP_mapping.xlsx
*	数据示例  

|	AS Name		|	ASN		|	Server IP	|	Details	|Country Code |  
 :---: | :---:| :---:|:---: | :---:
|7171-W-95TH-STREET|23333|	209.201.98.0/24|7171-W-95TH-STREET - WeightWatchers.com, Inc., US|US|  


### 日志

*	程序运行日志记录在 as2ipmask.log 文件中