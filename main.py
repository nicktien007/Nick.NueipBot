import requests
import json
from datetime import datetime, timedelta
from time import sleep
import pync


class Checker:
    def __init__(self) -> None:
        super().__init__()
        self.save_day = self.get_today()
        self.date_formatter = "%Y-%m-%d %H:%M:%S"
        self.has_clocked_out = False

    def run(self):
        print(f'現在時間:{self.get_today2()}')

        if self.save_day == self.get_today() \
                and not self.has_clocked_out:
            self.main()
            return

        if self.save_day == self.get_today() \
                and self.has_clocked_out:
            return

        self.new_day()

    def new_day(self):
        print("call new_day")
        self.save_day = self.get_today()
        self.has_clocked_out = False

    def main(self):
        data = self.get_response()
        d = json.loads(data)

        if self.not_login(d):
            print("尚未登錄")
            return

        sd = self.get_sd(d)
        ed = self.get_ed(d)

        self.show_info(ed, sd)

        if self.is_holiday(d):
            print("今天是例假日")
            return

        if self.is_time_off(d):
            print("今天有請特休")
            return

        # 尚未打上班卡
        if sd is None:
            print("尚未打上班卡!!")
            return

        sd_f = self.to_sd_f(sd)

        if datetime.today() < self.get_off_work_time(sd_f):
            print("還沒到下班時間!!")
            return

        # 有上班卡，沒下班卡，要用現在時間檢查
        if ed is None \
                and not self.has_clocked_out:
            ed_f = self.to_ed_f(ed)
            off_work_time = self.get_off_work_time(sd_f)
            if ed_f > off_work_time:
                pync.notify('嗶嗶嗶~~~!!快點打卡!!')
                return

        # 已經打上班卡、下班卡，檢查打卡時間是否在下班時間之後
        if ed is not None \
                and sd is not None \
                and not self.has_clocked_out:
            ed_f = self.to_ed_f(ed)
            off_work_time = self.get_off_work_time(sd_f)
            if off_work_time > ed_f:
                pync.notify('嗶嗶嗶~~~!!快點打卡!!')
                return

        pync.notify(f'已經打下班卡了({ed})~~~SAFE!!!!!')
        self.has_clocked_out = True

    def show_info(self, ed, sd):
        sd_f = self.to_sd_f(sd)
        ed_f = self.to_ed_f(ed)
        off_work_time = self.get_off_work_time(sd_f)
        print(f'上班卡:{sd}')
        print(f'下班卡:{ed}')
        print(f'預計下班:{off_work_time}')
        print(f'今日工時:{self.get_working_hours(ed_f, sd_f)}')
        print('===============')

    def get_working_hours(self, ed_f, sd_f):
        now = datetime.now()

        if now > datetime(now.year,now.month,now.day,13,30):
            return (ed_f - sd_f) - timedelta(hours=1)

        return ed_f - sd_f

    def get_response(self):
        url = "https://cloud.nueip.com/attendance_record/ajax"
        payload = {'action': 'attendance',
                   'loadInBatch': '1',
                   'loadBatchGroupNum': '6000',
                   'loadBatchNumber': '1',
                   'work_status': '1,4'}
        now_date = self.save_day
        headers = {
            'authority': 'cloud.nueip.com',
            'x-requested-with': 'XMLHttpRequest',
            'sec-ch-ua-mobile': '?0',
            'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'origin': 'https://cloud.nueip.com',
            'sec-fetch-site': 'same-origin',
            'sec-fetch-mode': 'cors',
            'sec-fetch-dest': 'empty',
            'referer': 'https://cloud.nueip.com/attendance_record',
            'accept-language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7,zh-CN;q=0.6',
            'cookie': 'deptShiftWorkModel_timeoffview=0; PHPSESSID=tp515kd5g3r9vaghep3icj5ki6; GCLB=CPuegpy5haOtxgE; '
                      'sideBar=show; language=tc; autopopTlayer=null; showByBelongDate_42=1; Search_42_FLayer=4907; '
                      'Search_42_SLayer=4907_16925; Search_42_TLayer=4907_16925_131467; '
                      f'Search_42_date_start={now_date}; '
                      f'Search_42_date_end={now_date}; '
                      'Search_42_showByBelongDate=1; PHPSESSID=5l31jmtcttunt60amfasr9jfa5; GCLB=CPyp_taelY3QEg'
        }
        response = requests.request("POST", url, headers=headers, data=payload)
        data = response.text
        return data

    def get_off_work_time(self, sd_f):
        return sd_f + timedelta(hours=9)

    def to_sd_f(self, sd):
        if sd is None:
            return datetime.strptime(self.get_today2(), self.date_formatter)
        return datetime.strptime(sd, self.date_formatter)

    def to_ed_f(self, ed):
        if ed is None:
            return datetime.strptime(self.get_today2(), self.date_formatter)
        return datetime.strptime(ed, self.date_formatter)

    def get_today(self):
        return datetime.today().strftime('%Y-%m-%d')

    def get_today2(self):
        return datetime.today().strftime(self.date_formatter)

    def get_sd(self, d):
        data_id = list(d["data"][self.save_day].keys())[0]
        section1 = d["data"][self.save_day][data_id]["section1"]

        if section1 is None:
            return None

        sd_section_id = list(section1.keys())[0]

        return section1[sd_section_id]["work_time"]

    def get_ed(self, d):
        data_id = list(d["data"][self.save_day].keys())[0]
        section2 = d["data"][self.save_day][data_id]["section2"]

        if section2 is None:
            return None

        ed_section_id = list(section2.keys())[-1]

        return section2[ed_section_id]["work_time"]

    def is_holiday(self, d):
        data_id = list(d["data"][self.save_day].keys())[0]
        holiday = d["data"][self.save_day][data_id]["holiday"]

        if holiday is None:
            return False

        return holiday

    def is_time_off(self, d):
        data_id = list(d["data"][self.save_day].keys())[0]
        time_off = d["data"][self.save_day][data_id]["timeoff"]

        if time_off is None:
            return False

        return time_off

    def not_login(self, d):
        if "message" in dict(d):
            return True
            # return d["message"] == "請重新登入系統"
        return False


if __name__ == '__main__':
    c = Checker()
    while True:
        c.run()
        # sleep(10)
        sleep(300)
