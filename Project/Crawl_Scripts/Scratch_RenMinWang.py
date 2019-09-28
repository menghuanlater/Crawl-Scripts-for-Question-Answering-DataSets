#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
-------------------------------------------------
   File Name：     Scratch_RenMinWang
   Description :   针对人民网设计的爬虫
                  1. 爬取各板块数据
                  2. 爬取
   Author :       menghuanlater
   date：          2019/9/26
-------------------------------------------------
   Change Activity:
                   2019/9/26:
-------------------------------------------------
"""
import pymysql
import Config.DataBaseConfig as DBC
import datetime
import re
import requests
from bs4 import BeautifulSoup


# test_url = "http://politics.people.com.cn/n1/2019/0924/c1001-31370343.html"


class Scratch_RenMinWang:
    def __init__(self):
        self.__header = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/76.0.3809.87 Safari/537.36"}
        self.__ignore = ["视频", "图解", "专题"]
        self.__encoding = "gbk"
        self.__db = pymysql.connect(DBC.database_ip, DBC.database_user, DBC.database_password, DBC.database_name)
        self.__cursor = self.__db.cursor()
        self.__cursor.execute("select count(*) from {table_name}".format(table_name=DBC.crawl_table_name))
        result = self.__cursor.fetchone()
        self.__increase_id = int(result[0]) + 1
        self.__p = re.compile("\s*")
        self.__max_index = 10  # 每个子板块，index.html最多搜索到index10.html

    @ staticmethod
    def __clean_publish_time(init_time_str: str):
        return init_time_str.replace("[", "").replace("]", "").replace("【", "").replace("】", "")

    def politics(self):
        """
        设置了请求头反而获取不了数据???
        :return:
        """
        # 时政板块
        all_urls = {"本网原创": "http://politics.people.com.cn/GB/99014/index.html",
                    "高层动态": "http://politics.people.com.cn/GB/1024/index.html",
                    "中央部委": "http://politics.people.com.cn/GB/1027/index.html",
                    "反腐倡廉": "http://politics.people.com.cn/GB/369059/index.html",
                    "时事解读": "http://politics.people.com.cn/GB/389979/index.html"}
        # 使用外扩循环
        for sub_type in all_urls.keys():
            url = all_urls[sub_type]
            html = requests.get(url)
            html.encoding = self.__encoding
            soup = BeautifulSoup(html.text, "html.parser")

            # 换页操作需要将原先尾部的index[0-9].html替换掉
            change_page_list_selector = soup.select(
                "body > div.w1000.ej_content.mt30 > div.fl.w655 > div.ej_list_box.clear > div.page_n.clearfix")
            # 先获取顶层的换页表单
            change_pages_list = ["index.html"]
            for t in change_page_list_selector:
                link = t.find_all("a")
                # print(link)
                for m in link:
                    if m.get("href") is not None and m.text not in ["上一页", "下一页"]:
                        change_pages_list.append(m.get("href"))
            detail_content_page = []
            for t in change_pages_list:
                if t != "index.html":
                    url = all_urls[sub_type].replace("index.html", t)
                    html = requests.get(url)
                    html.encoding = self.__encoding
                    soup = BeautifulSoup(html.text, "html.parser")
                # 包含标题 链接 时间
                current_page_news_list_selector = soup.select(
                    "body > div.w1000.ej_content.mt30 > div.fl.w655 > div.ej_list_box.clear > ul > li")
                for item in current_page_news_list_selector:
                    link = item.find_all("a")[0]
                    title = link.text
                    href = link.get("href")
                    publish_time = item.find_all("em")[0].text
                    flag = False
                    for i in self.__ignore:
                        if i in title:
                            flag = True
                            break
                    if "http" in href:
                        flag = True
                    if flag:
                        continue
                    detail_content_page.append((title, url + href, publish_time))
            for t in detail_content_page:
                content_html = requests.get(t[1])
                content_html.encoding = self.__encoding
                soup = BeautifulSoup(content_html.text, "html.parser")
                content_selector = soup.select("#rwb_zw")
                content = ""
                if len(content_selector) == 0:
                    continue
                for m in content_selector[0].find_all("p"):
                    content += m.text
                if len(re.sub(self.__p, "", content)) < 100:
                    continue
                self.__cursor.execute(
                    "insert into %s(id,url,crawl_time,title,publish_time,passage_text,passage_type,passage_length,source) "
                    "values(%d,'%s','%s','%s','%s','%s','%s',%d,'%s')" %
                    (DBC.crawl_table_name, self.__increase_id, t[1], str(datetime.datetime.now()), t[0].replace("\n", ""), self.__clean_publish_time(t[2]),
                     content, "时政-%s" % sub_type, len(content), "人民网"))
                self.__increase_id += 1
                self.__db.commit()
                print("抓取总量:%d  当前抓取 时政-%s --> %s %s" % (self.__increase_id-1, sub_type, t[0].replace("\n", ""), t[1]))

    def world(self):
        """
        :return: 国际板块-->相对复杂的一个板块
        1. 列表可能比较多, index采用尝试性的，存在则抓，不存在则break --> 只采集到index10.html
        2. 每个子板块可能对应的采集逻辑都不一样

        # 针对性设计selector
        """
        # 这个是采集列表页的选择器表示形式
        selector_list_forms = [
            "body > div.clearfix.w1000_320.m10 > div.fl.p1_left.ej_left > div.ej_bor > ul > li",
            "body > div.wybj.clearfix > div.content.clearfix > div.c_left.fl > dl > dd > h2 > a",
            "body > div.w1000.d2_content.clearfix > div.d2_left.fl > div > b > a",
        ]
        all_subs = {
            "滚动": {
                "url": "http://world.people.com.cn/GB/157278/index.html",
                "selector_form": selector_list_forms[0]
            },
            "国际观察": {
                "url": "http://world.people.com.cn/GB/1030/index.html",
                "selector_form": selector_list_forms[1]
            },
            "时事快报-亚太": {
                "url": "http://world.people.com.cn/GB/1029/42354/index.html",
                "selector_form": selector_list_forms[0]
            },
            "时事快报-美洲": {
                "url":"http://world.people.com.cn/GB/1029/42355/index.html",
                "selector_form": selector_list_forms[0]
            },
            "时事快报-欧洲": {
                "url":"http://world.people.com.cn/GB/1029/42356/index.html",
                "selector_form": selector_list_forms[0]
            },
            "时事快报-中东": {
                "url": "http://world.people.com.cn/GB/1029/42361/index.html",
                "selector_form": selector_list_forms[0]
            },
            "时事快报-非洲": {
                "url": "http://world.people.com.cn/GB/1029/42359/index.html",
                "selector_form": selector_list_forms[0]
            },
            "时事快报-其他": {
                "url": "http://world.people.com.cn/GB/1029/42408/index.html",
                "selector_form": selector_list_forms[0]
            },
            "独家": {
                "url": "http://world.people.com.cn/GB/57507/index.html",
                "selector_form": selector_list_forms[0]
            },
            "外媒关注-社会": {
                "url": "http://world.people.com.cn/GB/107182/395377/index.html",
                "selector_form": selector_list_forms[2]
            },
            "外媒关注-科技": {
                "url": "http://world.people.com.cn/GB/107182/395378/index.html",
                "selector_form": selector_list_forms[2]
            },
            "外媒关注-旅游": {
                "url": "http://world.people.com.cn/GB/107182/395379/index.html",
                "selector_form": selector_list_forms[2]
            },
            "外媒关注-健康": {
                "url": "http://world.people.com.cn/GB/107182/395380/index.html",
                "selector_form": selector_list_forms[2]
            },
            "外媒关注-时尚": {
                "url": "http://world.people.com.cn/GB/107182/395381/index.html",
                "selector_form": selector_list_forms[2]
            },
            "外媒关注-人文": {
                "url": "http://world.people.com.cn/GB/107182/395382/index.html",
                "selector_form": selector_list_forms[2]
            },
            "外媒关注-女性": {
                "url": "http://world.people.com.cn/GB/107182/395383/index.html",
                "selector_form": selector_list_forms[2]
            },
            "外媒关注-奇闻": {
                "url": "http://world.people.com.cn/GB/107182/396907/index.html",
                "selector_form": selector_list_forms[2]
            },
            "各国政局": {
                "ur;": "http://world.people.com.cn/GB/191609/index.html",
                "selector_form": selector_list_forms[0]
            }
        }
        for sub_type in all_subs.keys():


    def __del__(self):
        self.__db.commit()
        self.__cursor.close()
        self.__db.close()


if __name__ == "__main__":
    # print("Hello World Every Body")
    obj = Scratch_RenMinWang()
    obj.politics()
