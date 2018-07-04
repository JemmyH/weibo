import pymysql
class Get_info_by_keyword():
    def __init__(self):
        self.conn = pymysql.Connect(host='127.0.0.1', port=3306, user='hujiaming', passwd='123456', db='weibo',
                                    charset='utf8mb4')
        self.cursor = self.conn.cursor()
        # self.sql = "insert into keywords(id,keyword,weibo_count) values(1,'test',20)"
        self.sql = "select id from keywords"
        res = self.cursor.execute(self.sql)
        print(len(self.cursor.fetchall()))
        # for i in self.cursor.fetchall():
        #     print(i)
        # self.conn.commit()

if __name__ == '__main__':
    a = Get_info_by_keyword()
