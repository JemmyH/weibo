# _*_ coding:utf-8 _*_
# !/usr/bin/python3.6
# author:JemmyH

"""
alter table weibo_list convert to character set utf8mb4 collate utf8mb4_bin;
alter table comment convert to character set utf8mb4 collate utf8mb4_bin;
"""
import requests
import json
import urllib.parse
import pymysql

header = {
    'Referer': 'https://m.weibo.cn/p/searchall?containerid=100103type%3D1%26q%3D%E5%88%98%E4%BA%A6%E8%8F%B2',
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.99 Safari/537.36'
}


class Get_info_by_username():
    def __init__(self):
        self.conn = pymysql.Connect(host='127.0.0.1', port=3306, user='hujiaming', passwd='123456', db='weibo',
                                    charset='utf8mb4')
        self.cursor = self.conn.cursor()

    def run(self):
        user = input("请输入用户名：")
        value = {
            'containerid': '100103type=1&q={0}'.format(user),
            'page_type': 'searchall'
        }
        res = json.loads(requests.get(
            "https://m.weibo.cn/api/container/getIndex?{0}".format(urllib.parse.urlencode(value)),
            headers=header).text)
        # print(res)
        for i in res['data']['cards']:
            for j in i['card_group']:
                if j['card_type'] == 10:
                    name = j['desc1']
                    fans = j['desc2']
                    index_url = j['scheme']
                    uid = j['buttons'][0]['params']['uid']
                    print(j['desc1'], j['desc2'], j['scheme'], j['buttons'][0]['params']['uid'])
        if name and uid:
            info = self.get_detail_info(name, uid)
            print("详细信息:")
            print(info)
            weibo_values = self.get_weibo_list(uid, info['weibo_number'])

    def get_all_comments(self, weibo_id):
        first_maxid, first_maxid_type = self.get_comment_first_maxid(weibo_id)
        i = 0
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
        if 'data' in res:
            max_id = res['data']['max_id']
            max_id_type = res['data']['max_id_type']
        if max_id:
            return max_id, max_id_type

    def get_weibo_list(self, uid, weibo_number):
        if weibo_number // 10 == weibo_number / 10:
            page_num = weibo_number // 10
        else:
            page_num = weibo_number // 10 + 1
        # print(page_num)
        for i in range(1, page_num + 1):
            url = "https://m.weibo.cn/api/container/getIndex?uid={3}&luicode=10000011&lfid={0}&page={1}&type=uid&value={2}&containerid={4}".format(
                100103, i, uid, uid, 1076033261134763)
            res = json.loads(requests.get(url).text)
            # print(res)
            weibo_values = []
            if res['data']['cards']:
                for i in res['data']['cards']:
                    if i['card_type'] == 9:
                        # print(i['mblog']['id'], i['mblog']['text'], i['mblog']['created_at'],
                        #       i['mblog']['reposts_count'],
                        #       i['mblog']['comments_count'], i['mblog']['attitudes_count'], i['scheme'])
                        weibo_value = {
                            'id': i['mblog']['id'],
                            'text': i['mblog']['text'],
                            'create_time': i['mblog']['created_at'],
                            'reposts_count': i['mblog']['reposts_count'],
                            'comments_count': i['mblog']['comments_count'],
                            'attitudes_count': i['mblog']['attitudes_count'],
                            'scheme': i['scheme']
                        }
                        print(weibo_value)
                        sql = "insert into weibo_list(weibo_id,user_id,create_time,description,repost_count,comment_count,attitude_count) values({0},{1},'{2}','{3}',{4},{5},{6});".format(
                            i['mblog']['id'], uid, i['mblog']['created_at'],
                            pymysql.escape_string(i['mblog']['text']),
                            i['mblog']['reposts_count'], i['mblog']['comments_count'], i['mblog']['attitudes_count'])
                        self.cursor.execute(sql)
                        self.get_all_comments(weibo_value['id'])
                        weibo_values.append(weibo_value)

        return weibo_values

    def get_detail_info(self, username, uid):
        value = {
            'luicode': '10000011',
            'uid': uid,
            'lfid': '100103type=1',
            'q': username,
            'type': 'uid',
            'value': uid,
        }
        res = json.loads(requests.get(
            "https://m.weibo.cn/api/container/getIndex?{0}".format(urllib.parse.urlencode(value), headers=header)).text)
        # print(res['data'])
        follow_count = res['data']['userInfo']['follow_count']
        follower_count = res['data']['userInfo']['followers_count']
        nick_name = res['data']['userInfo']['screen_name']
        cover_image_url = res['data']['userInfo']['profile_image_url']
        description = res['data']['userInfo']['description']
        weibo_number = res['data']['userInfo']['statuses_count']
        # print("详细信息：",follow_count, follower_count, nick_name, cover_image_url, description, weibo_number)
        info = {
            'follow_count': follow_count,
            'follower_count': follower_count,
            'nick_name': nick_name,
            'cover_image_url': cover_image_url,
            'description': description,
            'weibo_number': weibo_number
        }
        sql = "insert into user(user_name,weibo_number,id,follow_count,follower_count,description) values('{0}',{1},{2},{3},{4},'{5}');".format(
            nick_name, weibo_number, uid, follow_count, follower_count, description)
        self.cursor.execute(sql)
        return info

    def get_weibo_detail(self, weibo_id):
        res = json.loads(requests.get("https://m.weibo.cn/statuses/show?id={0}".format(weibo_id)).text)
        if res['data']:
            data = res['data']
            value = {
                'weibo_id': data['id'],
                'create_at': data['create_at'],
                'text': data['text'],
                'reposts_count': data['reposts_count'],
                'commnt_count': data['comment_count'],
                'attitudes_count': data['attitudes_count'],
                'comments_count': data['comments_count'],
                'pics': [i['large']['url'] for i in data['pics']]
            }
            print(value)

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
                sql = "insert into comment(comment_id,weibo_id,create_time,comment_text,like_count,pic_url) values({0},{1},'{2}','{3}',{4},'{5}');".format(
                    comment['comment_id'], weibo_id, comment['create_at'], pymysql.escape_string(comment['text']),
                    comment['like_count'], comment['pics'])
                self.cursor.execute(sql)
            return max_id, max_id_type

    def close(self):
        self.conn.commit()
        self.cursor.close()
        self.conn.close()


if __name__ == '__main__':
    test = Get_info_by_username()
    test.run()
    test.close()
