from django.http import HttpResponse
from django.shortcuts import render
import requests
import time
import re
import json

CTIME = None
QRCODE = None
TIP = 1
TICKET_DICT = {}
PASS_TICKET = None
USER_INIT_DICT = {}
ALL_COOKIE_DICT = {}


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
    """
    监听用户是否扫码
    如果扫码, 监听用户是否点击确认
    :param request:
    :return:
    """
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
        ALL_COOKIE_DICT.update(res.cookies.get_dict())

        redirect_uri = re.findall('window.redirect_uri="(.*)";', res.text)[0]
        redirect_uri = redirect_uri + "&fun=new&version=v2"
        # 获取pass_ticket
        pass_res = requests.get(url=redirect_uri)
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(pass_res.text, "html.parser")
        for tag in soup.find('error').children:
            TICKET_DICT[tag.name] = tag.get_text()
        ALL_COOKIE_DICT.update(pass_res.cookies.get_dict())
        ret['code'] = 200
        return HttpResponse(json.dumps(ret))


def user(request):
    """
    个人主页
    :param request:
    :return:
    """
    # 获取用户信息
    get_user_info_data = {
        'BaseRequest': {
            'DeviceID': "e207610113916566",
            'Sid': TICKET_DICT['wxsid'],
            'Skey': TICKET_DICT['skey'],
            'Uin': TICKET_DICT['wxuin']
        }
    }
    get_user_info_url = "https://wx.qq.com/cgi-bin/mmwebwx-bin/webwxinit?r=-327493815&lang=zh_CN&pass_ticket=" + \
                        TICKET_DICT['pass_ticket']
    init_res = requests.post(
        url=get_user_info_url,
        json=get_user_info_data,
    )
    init_res.encoding = 'utf-8'
    user_init_dict = json.loads(init_res.text)
    USER_INIT_DICT.update(user_init_dict)
    ALL_COOKIE_DICT.update(init_res.cookies.get_dict())

    return render(request, 'user.html', {'user_init_dict': user_init_dict})


def contact_list(request):
    """
    获取所有联系人,并在页面中显示
    https://wx.qq.com/cgi-bin/mmwebwx-bin/webwxgetcontact?pass_ticket=Lia4OH0LTiHewUzBdCg5NJV9Ql72yT%252BflXafRGmqBocHhunaI%252BXe7GS8Yx2mr%252BO4&r=1546572514683&seq=0&skey=@crypt_ef969a2_1cb8610f5a4d128dd851877c7fb0c57a
    :param request:
    :return:
    """
    ctime = str(time.time())
    base_url = "https://wx.qq.com/cgi-bin/mmwebwx-bin/webwxgetcontact?pass_ticket=%s&r=%s&seq=0&skey=%s"
    url = base_url % (TICKET_DICT['pass_ticket'], ctime, TICKET_DICT['skey'])
    response = requests.get(url=url, cookies=ALL_COOKIE_DICT)
    response.encoding = 'utf-8'
    contact_list_dict = json.loads(response.text)
    for item in contact_list_dict['MemberList']:
        print(item['NickName'], item['UserName'])
    return render(request, 'contact-list.html', {'contact_list_dict': contact_list_dict})


def send_msg(request):
    """
    发送消息
    :param request:
    :return:
    https://wx.qq.com/cgi-bin/mmwebwx-bin/webwxsendmsg?lang=zh_CN&pass_ticket=3l5M72HLY4nADGAIPOSJWpgV0Zx4mfB7Vm5DHvE9vU4uXkaExzGB5xzibRyDkUpi

    """
    to_user = request.GET.get('toUser')
    msg = request.GET.get('msg')

    url = "https://wx.qq.com/cgi-bin/mmwebwx-bin/webwxsendmsg?lang=zh_CN&pass_ticket=%s" % (TICKET_DICT['pass_ticket'],)
    ctime = str(time.time() * 1000)
    post_dict = {
        'BaseRequest': {
            'DeviceID': "e207610113916566",
            'Sid': TICKET_DICT['wxsid'],
            'Skey': TICKET_DICT['skey'],
            'Uin': TICKET_DICT['wxuin']
        },
        'Msg': {
            'ClientMsgId': ctime,
            'Content': msg,
            'FromUserName': USER_INIT_DICT['User']['UserName'],
            'LocalID': ctime,
            'ToUserName': to_user.strip(),
            'Type': 1
        },
        "Scene": 0
    }
    response = requests.post(url=url, data=bytes(json.dumps(post_dict, ensure_ascii=False), encoding='utf-8'))
    print(response.text)
    return HttpResponse('ok')


def get_msg(request):
    """
    获取消息
    :param request:
    :return:
    """
    # 1. 长轮询检查消息是否到来, 从初始化信息中获取synckey
    # 2. 如果有消息到来
    #    获取消息
    #    获取synckey
    print('start...')
    synckey_list = USER_INIT_DICT['SyncKey']['List']
    sync_list = []
    for item in synckey_list:
        temp = "%s_%s" % (item['Key'], item['Val'],)
        sync_list.append(temp)
    synckey = "|".join(sync_list)

    res = requests.get(
        url="https://webpush.wx.qq.com/cgi-bin/mmwebwx-bin/synccheck",
        params={
            'r': time.time(),
            'skey': TICKET_DICT['skey'],
            'sid': TICKET_DICT['wxsid'],
            'uin': TICKET_DICT['wxuin'],
            'deviceid': "e402310790089148",
            'synckey': synckey
        },
        cookies=ALL_COOKIE_DICT
    )
    print(res.text)
    if 'retcode:"0",selector:"2"' in res.text:
        post_dict = {
            'BaseRequest': {
                'DeviceID': "e402310790089148",
                'Sid': TICKET_DICT['wxsid'],
                'Uin': TICKET_DICT['wxuin'],
                'Skey': TICKET_DICT['skey'],
            },
            "SyncKey": USER_INIT_DICT['SyncKey'],
            'rr': 1
        }

        msg_res = requests.post(
            url='https://wx.qq.com/cgi-bin/mmwebwx-bin/webwxsync',
            params={
                'skey': TICKET_DICT['skey'],
                'sid': TICKET_DICT['wxsid'],
                'pass_ticket': TICKET_DICT['pass_ticket'],
                'lang': 'zh_CN'
            },
            json=post_dict
        )
        msg_res.encoding = 'utf-8'
        msg_dict = json.loads(msg_res.text)
        for msg_info in msg_dict['AddMsgList']:
            print(msg_info['Content'])

        USER_INIT_DICT['SyncKey'] = msg_dict['SyncKey']

    print('end....')
    return HttpResponse('ok')
