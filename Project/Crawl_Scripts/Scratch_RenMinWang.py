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
import redis
import Config.DataBaseConfig as DBC
import datetime
import time
import re
import requests
from bs4 import BeautifulSoup


# test_url = "http://politics.people.com.cn/n1/2019/0924/c1001-31370343.html"


class Scratch_RenMinWang:
    def __init__(self):
        # self.__header = {
        #     "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/76.0.3809.87 Safari/537.36"}
        self.__ignore = ["视频", "图解", "专题"]
        self.__encoding = "gbk"
        self.__db = pymysql.connect(DBC.database_ip, DBC.database_user, DBC.database_password, DBC.database_name)
        self.__cursor = self.__db.cursor()
        self.__cursor.execute("select count(*) from {table_name}".format(table_name=DBC.crawl_table_name))
        result = self.__cursor.fetchone()
        self.__increase_id = int(result[0]) + 1
        self.__p = re.compile("\s*")
        self.__max_index = 10  # 每个子板块，index.html最多搜索到index10.html
        self.__no_time_str = "1999-9-19 09:09:09"  # 随便设的一个时间，当时间不存在的时候，以此字符串填充
        self.__normal_status_code = 200  # url正确打开的response代码

        # 连接redis
        self.__redis = redis.Redis(host=DBC.redis_ip, port=DBC.redis_port, db=DBC.redis_db, password=DBC.redis_password)

    @staticmethod
    def __sleep():
        time.sleep(0.1)  # 休眠0.1s

    @staticmethod
    def __clean_publish_time(init_time_str: str):
        s = init_time_str.replace("[", "").replace("]", "").replace("【", "").replace("】", "").replace("：", ":")
        return s.strip()

    # 时政
    def politics(self):
        """
        设置了请求头反而获取不了数据???
        :return:
        """
        # 时政板块
        domain = "http://politics.people.com.cn"
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
                    detail_content_page.append((title, domain + href, publish_time))
            for t in detail_content_page:
                content_html = requests.get(t[1])
                if self.__redis.get(t[1]) is not None:
                    continue
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
                try:
                    self.__cursor.execute(
                        "insert into %s(id,url,crawl_time,title,publish_time,passage_text,passage_type,passage_length,source) "
                        "values(%d,'%s','%s','%s','%s','%s','%s',%d,'%s')" %
                        (DBC.crawl_table_name, self.__increase_id, t[1], str(datetime.datetime.now()),
                         t[0].replace("\n", ""), self.__clean_publish_time(t[2]),
                         content, "时政-%s" % sub_type, len(content), "人民网"))
                    self.__redis.set(t[1], 1)
                    self.__sleep()
                except Exception:
                    continue
                self.__increase_id += 1
                self.__db.commit()
                print(
                    "抓取总量:%d  当前抓取 时政-%s --> %s %s" % (self.__increase_id - 1, sub_type, t[0].replace("\n", ""), t[1]))

    # 国际
    def world(self):
        """
        :return: 国际板块-->相对复杂的一个板块
        1. 列表可能比较多, index采用尝试性的，存在则抓，不存在则break --> 只采集到index10.html
        2. 每个子板块可能对应的采集逻辑都不一样

        # 针对性设计selector
        """
        domain = "http://world.people.com.cn"
        # 这个是采集列表页的选择器表示形式
        selector_list_forms = [
            "body > div.clearfix.w1000_320.m10 > div.fl.p1_left.ej_left > div.ej_bor > ul > li",  # <a> <i>
            "body > div.wybj.clearfix > div.content.clearfix > div.c_left.fl > dl > dd > h2",  # <a> no-time
            "body > div.w1000.d2_content.clearfix > div.d2_left.fl > div > b",  # <a> no-time
        ]
        all_subs = {
            "滚动": {
                "url": "http://world.people.com.cn/GB/157278/index.html",
                "selector_form": selector_list_forms[0],
                "time_flag": True,
                "time_element": "i"
            },
            "国际观察": {
                "url": "http://world.people.com.cn/GB/1030/index.html",
                "selector_form": selector_list_forms[1],
                "time_flag": False
            },
            "时事快报-亚太": {
                "url": "http://world.people.com.cn/GB/1029/42354/index.html",
                "selector_form": selector_list_forms[0],
                "time_flag": True,
                "time_element": "i"
            },
            "时事快报-美洲": {
                "url": "http://world.people.com.cn/GB/1029/42355/index.html",
                "selector_form": selector_list_forms[0],
                "time_flag": True,
                "time_element": "i"
            },
            "时事快报-欧洲": {
                "url": "http://world.people.com.cn/GB/1029/42356/index.html",
                "selector_form": selector_list_forms[0],
                "time_flag": True,
                "time_element": "i"
            },
            "时事快报-中东": {
                "url": "http://world.people.com.cn/GB/1029/42361/index.html",
                "selector_form": selector_list_forms[0],
                "time_flag": True,
                "time_element": "i"
            },
            "时事快报-非洲": {
                "url": "http://world.people.com.cn/GB/1029/42359/index.html",
                "selector_form": selector_list_forms[0],
                "time_flag": True,
                "time_element": "i"
            },
            "时事快报-其他": {
                "url": "http://world.people.com.cn/GB/1029/42408/index.html",
                "selector_form": selector_list_forms[0],
                "time_flag": True,
                "time_element": "i"
            },
            "独家": {
                "url": "http://world.people.com.cn/GB/57507/index.html",
                "selector_form": selector_list_forms[0],
                "time_flag": True,
                "time_element": "i"
            },
            "外媒关注-社会": {
                "url": "http://world.people.com.cn/GB/107182/395377/index.html",
                "selector_form": selector_list_forms[2],
                "time_flag": False
            },
            "外媒关注-科技": {
                "url": "http://world.people.com.cn/GB/107182/395378/index.html",
                "selector_form": selector_list_forms[2],
                "time_flag": False
            },
            "外媒关注-旅游": {
                "url": "http://world.people.com.cn/GB/107182/395379/index.html",
                "selector_form": selector_list_forms[2],
                "time_flag": False
            },
            "外媒关注-健康": {
                "url": "http://world.people.com.cn/GB/107182/395380/index.html",
                "selector_form": selector_list_forms[2],
                "time_flag": False
            },
            "外媒关注-时尚": {
                "url": "http://world.people.com.cn/GB/107182/395381/index.html",
                "selector_form": selector_list_forms[2],
                "time_flag": False
            },
            "外媒关注-人文": {
                "url": "http://world.people.com.cn/GB/107182/395382/index.html",
                "selector_form": selector_list_forms[2],
                "time_flag": False
            },
            "外媒关注-女性": {
                "url": "http://world.people.com.cn/GB/107182/395383/index.html",
                "selector_form": selector_list_forms[2],
                "time_flag": False
            },
            "外媒关注-奇闻": {
                "url": "http://world.people.com.cn/GB/107182/396907/index.html",
                "selector_form": selector_list_forms[2],
                "time_flag": False
            },
            "各国政局": {
                "url": "http://world.people.com.cn/GB/191609/index.html",
                "selector_form": selector_list_forms[0],
                "time_flag": True,
                "time_element": "i"
            }
        }
        self.__general_function(domain, all_subs, "国际")

    # 财经
    def finance(self):
        """
        财经板块
        """
        domain = "http://finance.people.com.cn"
        selector_list_forms = [
            "body > div.width980.ej_content > div.ej_left > ul > li",  # no time
            "body > div.topbg > div.p2.w1000.clearfix > div.left > div > ul > li > strong"  # no time
        ]
        all_subs = {
            "滚动新闻": {
                "url": "http://finance.people.com.cn/GB/70846/index.html",
                "selector_form": selector_list_forms[0],
                "time_flag": False
            },
            "部委快讯": {
                "url": "http://finance.people.com.cn/GB/153179/153522/index.html",
                "selector_form": selector_list_forms[0],
                "time_flag": False
            },
            "原创独家": {
                "url": "http://finance.people.com.cn/GB/414330/index.html",
                "selector_form": selector_list_forms[0],
                "time_flag": False
            },
            "人民财评": {
                "url": "http://finance.people.com.cn/GB/226375/402602/index.html",
                "selector_form": selector_list_forms[1],
                "time_flag": False
            }
        }
        self.__general_function(domain, all_subs, "财经")

    # 中国台湾
    def Chinese_taiwan(self):
        domain = "http://tw.people.com.cn"
        selector_list_forms = [
            "body > div > div.fl.p2j_list > div > ul > li",  # a i
        ]
        all_subs = {
            "滚动新闻": {
                "url": "http://tw.people.com.cn/GB/104510/index.html",
                "selector_form": selector_list_forms[0],
                "time_flag": True,
                "time_element": "i"
            },
            "岛内要闻": {
                "url": "http://tw.people.com.cn/GB/14812/14875/index.html",
                "selector_form": selector_list_forms[0],
                "time_flag": True,
                "time_element": "i"
            },
            "社会万象": {
                "url": "http://tw.people.com.cn/GB/14812/14874/index.html",
                "selector_form": selector_list_forms[0],
                "time_flag": True,
                "time_element": "i"
            },
            "台湾文娱": {
                "url": "http://tw.people.com.cn/GB/71483/index.html",
                "selector_form": selector_list_forms[0],
                "time_flag": True,
                "time_element": "i"
            },
            "涉台新闻": {
                "url": "http://tw.people.com.cn/GB/14810/index.html",
                "selector_form": selector_list_forms[0],
                "time_flag": True,
                "time_element": "i"
            },
            "两岸交流": {
                "url": "http://tw.people.com.cn/GB/14813/index.html",
                "selector_form": selector_list_forms[0],
                "time_flag": True,
                "time_element": "i"
            },
            "史海珍文": {
                "url": "http://tw.people.com.cn/GB/157509/index.html",
                "selector_form": selector_list_forms[0],
                "time_flag": True,
                "time_element": "i"
            }
        }
        self.__general_function(domain, all_subs, "中国台湾")

    def __general_function(self, domain: str, all_subs: dict, big_type_name: str):
        for sub_type in all_subs.keys():
            for i in range(self.__max_index):
                if i != 0:
                    list_url = all_subs[sub_type]["url"].replace("index", "index%d" % (i + 1))
                else:
                    list_url = all_subs[sub_type]["url"]
                while True:
                    try:
                        html = requests.get(list_url)
                        break
                    except Exception as e:
                        print(e)
                        time.sleep(1)
                        continue
                html.encoding = self.__encoding
                # 检查链接是否存在回应,不存在这个循环可以结束，返回上层
                if html.status_code != self.__normal_status_code:
                    continue
                soup = BeautifulSoup(html.text, "html.parser")
                selector = soup.select(all_subs[sub_type]["selector_form"])
                for list_item in selector:
                    if all_subs[sub_type]["time_flag"]:
                        a = list_item.find_all(all_subs[sub_type]["time_element"])[0]
                        publish_time = self.__clean_publish_time(a.get_text())
                    else:
                        publish_time = self.__no_time_str
                    link = list_item.find_all("a")
                    if len(link) == 0:
                        continue
                    else:
                        link = link[0]
                    title = link.get_text()
                    text_url = domain + link.get("href")
                    # 检查是否是合理的html，图解|视频|超链接专题均忽略
                    flag = False
                    for i in self.__ignore:
                        if i in title:
                            flag = True
                            break
                    if "http" in link.get("href"):
                        flag = True
                    if flag:
                        continue
                    # 检查是否重复
                    if self.__redis.get(text_url) is not None:
                        continue
                    while True:
                        try:
                            text_html = requests.get(text_url)
                            break
                        except Exception as e:
                            print(e)
                            time.sleep(1)
                            continue
                    text_html.encoding = self.__encoding
                    soup = BeautifulSoup(text_html.text, "html.parser")
                    text_selector = soup.select("#rwb_zw")
                    if len(text_selector) == 0:
                        continue
                    content = ""
                    for p in text_selector[0].find_all("p"):
                        content += p.get_text()
                    if len(re.sub(self.__p, "", content)) < 100:
                        continue
                    # 部分网页可能存在某些字符让写入sql出现问题
                    # 唯一性约束问题,防止url重复
                    try:
                        self.__cursor.execute(
                            "insert into %s(id,url,crawl_time,title,publish_time,passage_text,passage_type,passage_length,source) "
                            "values(%d,'%s','%s','%s','%s','%s','%s',%d,'%s')" %
                            (DBC.crawl_table_name, self.__increase_id, text_url, str(datetime.datetime.now()),
                             title.replace("\n", ""), publish_time,
                             content, "%s-%s" % (big_type_name, sub_type), len(content), "人民网"))
                        self.__redis.set(text_url, 1)
                        self.__sleep()
                    except Exception:
                        print("出现重复或者异常字符,跳过. url:%s" % text_url)
                        continue
                    self.__increase_id += 1
                    self.__db.commit()
                    print("抓取总量:%d  当前抓取 %s-%s --> %s %s" % (
                        self.__increase_id - 1, big_type_name, sub_type, title.replace("\n", ""), text_url))

    def __del__(self):
        self.__db.commit()
        self.__cursor.close()
        self.__db.close()
        self.__redis.close()


if __name__ == "__main__":
    # print("Hello World Every Body")
    obj = Scratch_RenMinWang()
    # obj.politics()
    # obj.world()
    # obj.finance()
    obj.Chinese_taiwan()
