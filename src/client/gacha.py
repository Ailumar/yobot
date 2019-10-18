# coding=utf-8
import os
import pickle
import random
import re
import sqlite3
import sys
import time

import json5
import requests


class Gacha():
    URL = "http://api.yobot.xyz/v2/pool/?type=json5"

    def __init__(self, baseinfo):
        """
        baseinfo=[群号，QQ号, 群名片]（字符串）
        """
        self.__qqid = int(baseinfo[1])
        self.__nickname = baseinfo[2]
        self.__path = os.path.dirname(sys.argv[0])
        self.txt_list = []

    def __del__(self):
        pass

    def load(self):
        if not os.path.exists(os.path.join(self.__path, "pool.json5")):
            res = requests.get(self.URL)
            assert res.status_code == 200, "服务器不可用"
            with open(os.path.join(self.__path, "pool.json5"), "w", encoding="utf-8") as f:
                f.write(res.text)
            try:
                self.__pool = json5.loads(res.text)
            except:
                self.txt_list.append("服务器响应错误")
                return 1
        else:
            with open(os.path.join(self.__path, "pool.json5"), "r", encoding="utf-8") as f:
                try:
                    self.__pool = json5.load(f)
                except:
                    self.txt_list.append("卡池文件解析错误，请检查卡池文件语法，或者“#重置卡池”")
                    return 2
        return 0

    def result(self):
        prop = 0.
        result_list = []
        for p in self.__pool["pool"].values():
            prop += p["prop"]
        for i in range(10):
            resu = random.random() * prop
            for p in self.__pool["pool"].values():
                resu -= p["prop"]
                if resu < 0:
                    if i == 9 and p.get("guarantee", None) != None:
                        p = self.__pool["pool"][p["guarantee"]]
                    result_list.append(p.get("prefix", "") +
                                       random.choice(p["pool"]))
                    break
        return result_list

    def gacha(self):
        self.check_ver()
        db_exists = os.path.exists(os.path.join(self.__path, "collections.db"))
        db_conn = sqlite3.connect(os.path.join(self.__path, "collections.db"))
        db = db_conn.cursor()
        if not db_exists:
            db.execute(
                '''CREATE TABLE Colle(
                qqid INT PRIMARY KEY,
                colle BLOB,
                times SMALLINT,
                last_day CHARACTER(4),
                day_times TINYINT)''')
        today = time.strftime("%m%d")
        sql_info = list(db.execute(
            "SELECT colle,times,last_day,day_times FROM Colle WHERE qqid=?", (self.__qqid,)))
        mem_exists = (len(sql_info) == 1)
        if mem_exists:
            info = pickle.loads(sql_info[0][0])
            times, last_day, day_times = sql_info[0][1:]
        else:
            info = {}
            times, last_day, day_times = 0, "", 0
        try:
            day_limit = self.__pool["settings"]["每日抽卡次数"]
        except:
            self.txt_list.append("卡池信息错误")
            return 1
        if today != last_day:
            last_day = today
            day_times = 0
        if day_limit != 0 and day_times >= day_limit:
            self.txt_list.append("你今天已经抽了{}次了，明天再来吧".format(day_times))
            return 2
        try:
            result = self.result()
        except:
            self.txt_list.append("卡池信息错误")
            return 1
        times += 1
        day_times += 1
        self.txt_list.append("{}第{}抽：".format(self.__nickname, times))
        for char in result:
            if char in info:
                info[char] += 1
                self.txt_list.append("{}({})".format(char, info[char]))
            else:
                info[char] = 1
                self.txt_list.append("{}(new)".format(char))
        sql_info = pickle.dumps(info)
        if mem_exists:
            db.execute("UPDATE Colle SET colle=?, times=?, last_day=?, day_times=? WHERE qqid=?",
                       (sql_info, times, last_day, day_times, self.__qqid))
        else:
            db.execute("INSERT INTO Colle (qqid,colle,times,last_day,day_times) VALUES(?,?,?,?,?)",
                       (self.__qqid, sql_info, times, last_day, day_times))
        db_conn.commit()
        db_conn.close()
        return 0

    def setting(self):
        ld = self.load()
        if ld == 0:
            masters = self.__pool.get("settings", {}).get("master", [])
            if masters != [] and self.__qqid not in masters:
                self.txt_list.append("对不起，你没有权限")
                return
        elif ld == 1:
            return
        if os.path.exists(os.path.join(self.__path, "pool.json5")):
            os.system("start notepad " + os.path.join(
                os.path.join(self.__path, "pool.json5")))
            self.txt_list.append("请在本机的运行电脑上修改卡池，修改完毕后保存即可")
        else:
            self.txt_list.append("卡池文件丢失，下次抽卡时重新下载")

    def del_pool(self):
        ld = self.load()
        if ld == 0:
            masters = self.__pool.get("settings", {}).get("master", [])
            if masters != [] and self.__qqid not in masters:
                self.txt_list.append("对不起，你没有权限")
                return
        if os.path.exists(os.path.join(self.__path, "pool.json5")):
            os.remove(os.path.join(self.__path, "pool.json5"))
        self.txt_list.append("卡池已重置")

    def show_colle(self, cmd=None):
        if not os.path.exists(os.path.join(self.__path, "collections.db")):
            self.txt_list.append("没有仓库")
            return 1
        moreqq_list = []
        if cmd != None:
            pattern = r"(?<=\[CQ:at,qq=)\d+(?=\])"
            moreqq_list = [int(x) for x in re.findall(pattern, cmd)]
        db_conn = sqlite3.connect(os.path.join(self.__path, "collections.db"))
        db = db_conn.cursor()
        sql_info = list(db.execute(
            "SELECT colle FROM Colle WHERE qqid=?", (self.__qqid,)))
        if len(sql_info) != 1:
            self.txt_list.append(self.__nickname + "的仓库为空")
            db_conn.close()
            return 2
        colle = pickle.loads(sql_info[0][0])
        more_colle = []
        for other_qq in moreqq_list:
            sql_info = list(db.execute(
                "SELECT colle FROM Colle WHERE qqid=?", (other_qq,)))
            if len(sql_info) != 1:
                self.txt_list.append("[CQ:at,qq={}]的仓库为空".format(other_qq))
                db_conn.close()
                return 2
            more_colle.append(pickle.loads(sql_info[0][0]))
        if not os.path.exists(os.path.join(self.__path, "temp")):
            os.mkdir(os.path.join(self.__path, "temp"))
        colle_file = os.path.join(
            self.__path, "temp",
            str(self.__qqid)+time.strftime("_%Y%m%d_%H%M%S", time.localtime())+".csv")
        showed_colle = set(colle)
        for item in more_colle:
            showed_colle = showed_colle.union(item)
        with open(colle_file, "w", encoding="utf-8-sig") as f:
            f.write("角色,"+self.__nickname)
            for memb in moreqq_list:
                f.write(",")
                # 使用老李api
                res = requests.get("http://laoliapi.cn/king/qq.php?qq=" + str(memb))
                if res.status_code == 200:
                    f.write(json5.loads(res.text).get("name", str(memb)))
                else:
                    f.write(str(memb))
            f.write("\n")
            for char in sorted(showed_colle):
                f.write(char + "," + str(colle.get(char, 0)))
                for item in more_colle:
                    f.write("," + str(item.get(char, 0)))
                f.write("\n")
        f = open(colle_file, 'rb')
        files = {'file': f}
        response = requests.post(
            'http://api.yobot.xyz/v2/reports/', files=files)
        f.close()
        p = response.text
        self.txt_list.append(self.__nickname + "的仓库：" + p)
        db_conn.close()
        return 0

    def check_ver(self):
        auto_update = self.__pool.get("settings", {}).get("联网更新卡池", False)
        if not auto_update:
            return
        f = open(os.path.join(self.__path, "version.json"),
                 "r+", encoding="utf-8")
        ver = json5.load(f)
        now = int(time.time())
        if ver.get("pool_checktime", 0) < now:
            res = requests.get(self.URL)
            if res.status_code == 200:
                online_ver = json5.loads(res.text)
                if self.__pool["info"]["name"] != online_ver["info"]["name"]:
                    self.__pool = online_ver
                    with open(os.path.join(self.__path, "pool.json5"), "w", encoding="utf-8") as pf:
                        pf.write(res.text)
                    self.txt_list.append("卡池已自动更新，目前卡池：" +
                                         self.__pool["info"]["name"])
                ver["pool_checktime"] = now + 80000
                f.seek(0)
                f.truncate()
                json5.dump(ver, f, indent=2,
                           quote_keys=True, trailing_commas=False)
        f.close()

    @staticmethod
    def match(cmd):
        if cmd == "十连" or cmd == "十连抽":
            return 1
        elif cmd == "十连设置" or cmd == "抽卡设置" or cmd == "卡池设置":
            return 2
        elif cmd == "重置卡池" or cmd == "删除卡池" or cmd == "更新卡池":
            return 3
        elif cmd.startswith("仓库"):
            return 4
        else:
            return 0

    def gc(self, func_num, cmd=None):
        if func_num == 2:
            self.setting()
        elif func_num == 3:
            self.del_pool()
        elif func_num == 4:
            self.show_colle(cmd)
        elif self.load() == 0:
            if func_num == 1:
                self.gacha()
