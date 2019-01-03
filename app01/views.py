from django.http import HttpResponse
from django.shortcuts import render
import requests
import time
import re
import json

CTIME = None
QRCODE = None
TIP = 1
ticket_dict = {}
PASS_TICKET = None


# Create your views here.
def login(request):
    global CTIME
    CTIME = time.time()
    response = requests.get(
        url='https://login.wx.qq.com/jslogin?appid=wx782c26e4c19acffb&fun=new&lang=zh_CN&_=%s' % CTIME
    )
    qrcode = re.findall('uuid = "(.*)";', response.text)
    global QRCODE
    QRCODE = qrcode[0]
    return render(request, 'login.html', {'qrcode': QRCODE})


def check_login(request):
    global TIP
    ret = {'code': 408, 'data': None}
    res = requests.get(
        url='https://login.wx.qq.com/cgi-bin/mmwebwx-bin/login?loginicon=true&uuid=%s&tip=%s&r=-320772887&_=%s' % (
            QRCODE, TIP, CTIME)
    )
    # print(res.text)
    if "window.code=408" in res.text:
        print("没有扫码")
        return HttpResponse(json.dumps(ret))
    elif "window.code=201" in res.text:
        ret['code'] = 201
        avatar = re.findall("window.userAvatar = '(.*)'", res.text)[0]
        ret['data'] = avatar
        TIP = 0
        return HttpResponse(json.dumps(ret))
    elif "window.code=200" in res.text:
        """
        用户点击确认登录
        window.redirect_uri="https://wx.qq.com/cgi-bin/mmwebwx-bin/webwxnewloginpage?ticket=AaFJ2MOUTAaT9VGxBy6vmnsw@qrticket_0&uuid=4akM6jv03w==&lang=zh_CN&scan=1546510946";
        """
        redirect_uri = re.findall('window.redirect_uri="(.*)";', res.text)[0]
        redirect_uri = redirect_uri + "&fun=new&version=v2"

        # 获取pass_ticket
        res2 = requests.get(url=redirect_uri)
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(res2.text, "html.parser")
        for tag in soup.find('error').children:
            ticket_dict[tag.name] = tag.get_text()

        # 获取用户信息
        get_user_info_data = {
            'BaseRequest':{
                'DeviceID': "e207610113916566",
                'Sid': ticket_dict['wxsid'],
                'Skey': ticket_dict['skey'],
                'Uin': ticket_dict['wxuin']
            }
        }
        get_user_info_url = "https://wx.qq.com/cgi-bin/mmwebwx-bin/webwxinit?r=-327493815&lang=zh_CN&pass_ticket=" + \
                            ticket_dict['pass_ticket']
        init_res = requests.post(
            url=get_user_info_url,
            json=get_user_info_data,
        )
        init_res.encoding = 'utf-8'
        print(init_res.text)
        user_init_dict = json.loads(init_res.text)

        contact_list = user_init_dict['ContactList']
        for item in contact_list:
            print(item['RemarkName'], item['PYQuanPin'], item['NickName'])

        ret['code'] = 200
        return HttpResponse(json.dumps(ret))

