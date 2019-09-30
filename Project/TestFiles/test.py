#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
-------------------------------------------------
   File Name：     test
   Description :
   Author :       menghuanlater
   date：          2019/9/26
-------------------------------------------------
   Change Activity:
                   2019/9/26:
-------------------------------------------------
"""
import requests
from bs4 import BeautifulSoup


# url = "http://world.people.com.cn/GB/107182/395377/index.html"

url = "http://world.people.com.cn/GB/1030/index.html"

html = requests.get(url)

html.encoding = "gbk"

soup = BeautifulSoup(html.text, "html.parser")

# selector = soup.select("body > div.w1000.d2_content.clearfix > div.d2_left.fl > div > b > a")
selector = soup.select("body > div.wybj.clearfix > div.content.clearfix > div.c_left.fl > dl > dd > h2 > a")

for t in selector:
    print(t.get("href"))

