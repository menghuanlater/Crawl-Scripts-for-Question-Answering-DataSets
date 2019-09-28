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


class Douban:
    def __init__(self):
        self.URL = "https://movie.douban.com/top250"
        self.startNum = [25*i for i in range(0, 10)]
        self.header = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/76.0.3809.87 Safari/537.36"}

    def getTop250(self):
        for start in self.startNum:
            html = requests.get(url=self.URL, params={"start": str(start)}, headers=self.header)
            soup = BeautifulSoup(html.content, "html.parser")
            movie_name = soup.select("#content > div > div.article > ol > li > div > div.info > div.hd")
            print(movie_name[0].get_text())

    def __del__(self):
        pass


if __name__ == "__main__":
    cls = Douban()
    cls.getTop250()
