# _*_ coding:utf-8 _*_
# !/usr/bin/python3.6
# author:JemmyH
import requests
import json
import urllib.parse
import pymysql
import random
from get_info_by_username.username_model import Get_info_by_username

header = {
    'Referer': 'https://m.weibo.cn/p/searchall?containerid=100103type%3D1%26q%3D%E5%88%98%E4%BA%A6%E8%8F%B2',
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.99 Safari/537.36'
}


class Get_info_by_keyword():
    def __init__(self):
        self.conn = pymysql.Connect(host='127.0.0.1', port=3306, user='hujiaming', passwd='123456', db='weibo',
                                    charset='utf8mb4')
        self.cursor = self.conn.cursor()

    def run(self):
        keyword = input("请输入关键字：")
        page_num = int(input("请输入想要浏览的页数(一页有十条微博)："))
        keyword_id = random.randint(1, 10000)
        while True:
            self.cursor.execute("select id from keywords where id={0}".format(keyword_id))
            if len(self.cursor.fetchall()) == 0:
                break
            else:
                keyword_id = random.randint(1, 10000)
        sql = "insert into keywords(id,keyword,weibo_count) values({2},'{0}',{1})".format(keyword, 10 * page_num,
                                                                                          keyword_id)
        self.cursor.execute(sql)
        self.conn.commit()
        for i in range(1, page_num + 1):
            value = {
                'containerid': '100103type=1&q={0}'.format(keyword),
                'page_type': 'searchall',
                'page': i
            }
            res = json.loads(requests.get(
                "https://m.weibo.cn/api/container/getIndex?{0}".format(urllib.parse.urlencode(value)),
                headers=header).text)
            print(res)
            if 'data' in res:
                data = res['data']['cards']
                for i in data:
                    for j in i['card_group']:
                        if j['card_type'] == 9:
                            weibo_id = j['mblog']['id']
                            self.get_weibo_detail(weibo_id, keyword_id)

    def get_weibo_detail(self, weibo_id, keyword_id):
        res = json.loads(requests.get("https://m.weibo.cn/statuses/show?id={0}".format(weibo_id)).text)
        if 'data' in res:
            data = res['data']

            def has_pic(i):
                if 'pic' in i:
                    return i['pic']['large']['url']
                else:
                    return "none"

            value = {
                'weibo_id': data['id'],
                'create_at': data['created_at'],
                'text': data['text'],
                'reposts_count': data['reposts_count'],
                'attitudes_count': data['attitudes_count'],
                'comments_count': data['comments_count'],
                'pics': has_pic(data)
            }
            print(value)
            self.cursor.execute(
                "select weibo_id from weibo_list_for_keyword where weibo_id={0}".format(value['weibo_id']))
            sql = "insert into weibo_list_for_keyword(weibo_id, keyword_id, create_time, description,repost_count,comment_count,attitude_count) values({0},{1},'{2}','{3}',{4},{5},{6});".format(
                value['weibo_id'], keyword_id, value['create_at'], pymysql.escape_string(value['text']),
                value['reposts_count'], value['comments_count'], value['attitudes_count'])
            self.cursor.execute(sql)
            self.conn.commit()
            self.get_all_comments(value['weibo_id'])

    def get_comment_first_maxid(self, weibo_id):
        res = json.loads(
            requests.get(
                "https://m.weibo.cn/comments/hotflow?id={0}&mid={1}&max_id_type=0".format(weibo_id, weibo_id),
                headers=header).text)

        def has_pic(i):
            if 'pic' in i:
                return i['pic']['large']['url']
            if 'data' in res:
                for i in res['data']['data']:
                    # 这是每一条评论的信息
                    comment = {
                        'create_at': i['created_at'],
                        'comment_id': i['id'],
                        'text': (i['text'].split("<span")[0]) if len(i['text'].split("<span")[0]) > 0 else
                        i['text'].split("<span")[1],
                        'like_count': i['like_count'],
                        'pics': has_pic(i)
                    }
                    print(comment)
                    sql = "insert into comment(comment_id,weibo_id,create_time,comment_text,like_count,pic_url) values({0},{1},'{2}','{3}',{4},'{5}');".format(
                        comment['comment_id'], weibo_id, comment['create_at'], pymysql.escape_string(comment['text']),
                        comment['like_count'], comment['pics'])
                    self.cursor.execute(sql)
                    self.conn.commit()

        if 'data' in res:
            max_id = res['data']['max_id']
            max_id_type = res['data']['max_id_type']
            if max_id:
                return max_id, max_id_type
        else:
            return 1, 1

    def get_all_comments(self, weibo_id):
        first_maxid, first_maxid_type = self.get_comment_first_maxid(weibo_id)
        i = 0
        if first_maxid != 1 and first_maxid_type != 1:
            while True:
                if i == 0:
                    id, id_type = self.get_comment_for_weibo(weibo_id, first_maxid, first_maxid_type)
                    i = 1
                if not id:
                    break
                else:
                    try:
                        id, id_type = self.get_comment_for_weibo(weibo_id, id, id_type)
                    except Exception as e:
                        return

    def get_comment_for_weibo(self, weibo_id, max_id, id_type):
        res = json.loads(
            requests.get(
                "https://m.weibo.cn/comments/hotflow?id={0}&mid={1}&max_id={2}&max_id_type={3}".format(weibo_id,
                                                                                                       weibo_id,
                                                                                                       max_id, id_type),
                headers=header).text)
        if 'data' in res:
            max_id = res['data']['max_id']
            max_id_type = res['data']['max_id_type']

            def has_pic(i):
                if 'pic' in i:
                    return i['pic']['large']['url']

            for i in res['data']['data']:
                # 这是每一条评论的信息
                comment = {
                    'create_at': i['created_at'],
                    'comment_id': i['id'],
                    'text': i['text'],
                    'like_count': i['like_count'],
                    'pics': has_pic(i)
                }
                print(comment)
                sql = "insert into comment_for_keyword(comment_id,weibo_id,create_time,comment_text,like_count,pic_url) values({0},{1},'{2}','{3}',{4},'{5}');".format(
                    comment['comment_id'], weibo_id, comment['create_at'], pymysql.escape_string(comment['text']),
                    comment['like_count'], comment['pics'])
                self.cursor.execute(sql)
                self.conn.commit()
            return max_id, max_id_type

    def close(self):
        self.conn.commit()
        self.cursor.close()
        self.conn.close()


if __name__ == '__main__':
    test = Get_info_by_keyword()
    test.run()
    test.close()
