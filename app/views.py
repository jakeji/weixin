#coding=utf-8
from __future__ import unicode_literals
from django.shortcuts import render
import re,datetime
 
from django.http.response import HttpResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
 
from wechat_sdk import WechatBasic
from wechat_sdk.exceptions import ParseError
from wechat_sdk.messages import TextMessage
import urllib,urllib2
import json
import pymssql

WECHAT_TOKEN = 'weixin'
AppID = 'wx6541cb163ddebd36'
AppSecret ='19f09a599f6d6c267c7e82614a685de9'
 
# 实例化 WechatBasic
wechat_instance = WechatBasic(
    token=WECHAT_TOKEN,
    appid=AppID,
    appsecret=AppSecret
)

def text_reply(msg):
    info=msg.encode('utf-8')
    url='http://www.tuling123.com/openapi/api'
    data={ u"key":"b1fda7370b5f4d41bb0830dffd53d7cd",
           "info":info,
           }
    dd=urllib.urlencode(data)
    url2=urllib2.Request(url,dd)
    response=urllib2.urlopen(url2)
    apicontent=response.read()
    s=json.loads(apicontent,encoding='utf-8')
    if s['code']==100000:
        return s['text']
    return 'error'


class MSSQL:
    def __init__(self,host,user,pwd,db):
        self.host=host
        self.user=user
        self.pwd=pwd
        self.db=db

    def __GetConnect(self):
        if not self.db:
            raise(NameError,"no database information!")
        self.conn=pymssql.connect(host=self.host,user=self.user,password=self.pwd,database=self.db,port='1433',charset="utf8")
        cur=self.conn.cursor()
        if not cur:
            raise(NameError,"连接数据库失败!")
        else:
            return cur
    def ExecQuery(self,sql):
        cur=self.__GetConnect()
        cur.execute(sql)
        resList=cur.fetchall()
        self.conn.close()
        return resList
    def ExeNonQuery(self,sql):
        cur=self.__GetConnect()
        cur.execute(sql)
        self.conn.commit()
        self.conn.close()
def get_realdata():        
    ms=MSSQL("192.168.5.110","sa","95335jk","TancyGPRS")
    resList=ms.ExecQuery("select DeviceID,RecordID from dbo.RealtimeData")
    #m_str=u"手机号码     采集时间         总量         温度      压力        余量\n"
    m_str=''
    for (DeviceID,RecordID) in resList:
        m_sql="select collectTime,stdTotal,T,P,Margin from dbo.HistoryRecord where DeviceID=%d and ID=%d"%(DeviceID,RecordID)
        recordList=ms.ExecQuery(m_sql)
        m_strtime=recordList[0][0].strftime("%Y-%m-%d %H:%M:%S")
        m_list=u"   总量: %d\n   温度: %2.2f\n   压力: %2.2f\n   余量: %d\n"%(recordList[0][1],recordList[0][2],recordList[0][3],recordList[0][4])
        m_sql="select DtuId from dbo.GatherParam where DeviceID=%d"%DeviceID
        dtulist=ms.ExecQuery(m_sql)
        #dtunum="%d"%dtulist[0][0]
        #print dtunum,m_strtime,m_str
        m_str+=u"   手机号码: %s\n   采集时间: %s\n%s"%(dtulist[0][0],m_strtime,m_list) 
        m_str+=u'<a href="http://www.sohu.com?a=%s">  \t 日记录</a>'%dtulist[0][0]
        m_str+=u'<a href="http://www.baidu.com?a=%s">   月记录</a>\n'%dtulist[0][0]   
     #print "%s"%dtulist[0][0],m_strtime,m_list
    return m_str
def get_order(pid):
    ms=MSSQL("192.168.5.110","sa","95335jk","TancyGPRS1")
    m_sql="select PID from dbo.TreeView where ID=%d AND  Category=1"%pid
    recordList=ms.ExecQuery(m_sql)
    if len(recordList)>0:
        PID=recordList[0]
        #print PID
        m_sql="select Name,ID from dbo.TreeView where ID=%d AND Category=0"%PID
        #print m_sql
        recordList=ms.ExecQuery(m_sql)
        if len(recordList)>0:
            name=recordList[0]
            return name[0]
    return u'无'
def get_status(tt):
    dd=datetime.datetime.now()
    if type(tt)!=datetime.datetime:
        return u"未知"
    if (dd-tt).days>=1:
        return u"下线"
    return u"在线"
def get_info(ss):
    ss=ss.strip()
    sql=''
    if re.match(r'A16\d{7,10}',ss):
        sql="select Name,DevicePhone,FtlNumber,ID,PID from dbo.FtlDevice where FtlNumber='"+ ss+"'"
    if re.match(r'1\d{10}',ss):
        sql="select Name,DevicePhone,FtlNumber,ID,PID from dbo.FtlDevice where DevicePhone="+ ss
    if len(sql)>0:
        ms=MSSQL("192.168.5.110","sa","95335jk","TancyGPRS1")
        recodList=ms.ExecQuery(sql)
        if len(recodList)>0:
            Name,DevicePhone,FtlNumber,ID,PID=recodList[0]
            sql="select DeviceId from dbo.GatherParam where DtuId=%s"%DevicePhone
            recodList=ms.ExecQuery(sql)
            if len(recodList)==0:
                return u'没有记录'                
            DeviceID=recodList[0]
            sql="select RecordID from dbo.RealtimeData where DeviceID=%d"%DeviceID
            #print DevicePhone,FtlNumber,PID
            recodList=ms.ExecQuery(sql)
            if len(recodList)>0:
                RecordID=recodList[0]
                sql="select CollectTime,OperTotal,StdTotal,T,P from dbo.HistoryRecord where ID=%d"%RecordID
                recodList=ms.ExecQuery(sql)
                if len(recodList)>0:
                    CollectTime,OperTotal,StdTotal,T,P=recodList[0]
                    m_flag=get_status(CollectTime)
                    m_name=get_order(PID)
                    return  u" 所属: %s\n 单位：%s\n 电话：%s\n 编号：%s \n 工况：%0.2f\n 标况：%0.2f\n 温度：%0.2f\n 压力：%0.2f\n 采集时间：%s\n 状态: %s\n "%(m_name,Name,DevicePhone,FtlNumber,OperTotal,StdTotal,T,P,CollectTime.strftime("%Y-%m-%d %H:%M:%S"),m_flag)
    return u'没有记录'
def get_day_report(ss):
    ss=ss.strip()
    sql=''
    m_num,m_date=ss.split()
    #print m_num
    #if  re.match(r'A16\d{12}',m_num)==None or re.match(r'1\d{10}',m_num)==None:
    #  return 'input error'
    try:
        dt=datetime.datetime.strptime(m_date,'%Y-%d-%m')
    except TypeError:
        return 'date error'
    if re.match(r'A16\d{12}',m_num):
        sql="select Name,DevicePhone,FtlNumber,ID,PID from dbo.FtlDevice where FtlNumber='"+m_num+"'"
    if re.match(r'1\d{10}',m_num):
        sql="select Name,DevicePhone,FtlNumber,ID,PID from dbo.FtlDevice where DevicePhone="+ m_num
    ms=MSSQL("192.168.5.110","sa","95335jk","TancyGPRS1")
    #print sql
    if len(sql)==0:
        return "input error"
    recodList=ms.ExecQuery(sql)
    if len(recodList)==0:
        return '没有记录'
    Name,DevicePhone,FtlNumber,ID,PID=recodList[0]
    sql="select DeviceId from dbo.GatherParam where DtuId=%s"%DevicePhone
    recodList=ms.ExecQuery(sql)
    if len(recodList)==0:
        return u'没有记录'                
    DeviceID=recodList[0]
    #print DeviceID
    sql="select CountTime,StartGas,EndGas,Total from dbo.DayReport where DeviceID=%d "%DeviceID+"AND CountTime='%s'"%m_date
    #print sql
    recodList=ms.ExecQuery(sql)
    if len(recodList)==0:
        return 'no data'
    m_name=get_order(PID)
    CountTime,StartGas,EndGas,Total=recodList[0]
    if StartGas==None or EndGas==None or EndGas==None:
        return u'没有记录'
    return  u" 所属: %s\n 单位：%s\n 电话：%s\n 编号：%s \n 开始量：%0.2f\n 结束量：%0.2f\n 总量：%0.2f\n 时间：%s"%(m_name,Name,DevicePhone,FtlNumber,StartGas,EndGas,Total,m_date)

class MenuManager:
    def __init__(self):
        self.appid='wx6541cb163ddebd36'
        self.appsecret='19f09a599f6d6c267c7e82614a685de9'
        self.accessUrl = "https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid="+self.appid+"&secret="+self.appsecret
        self.delMenuUrl = "https://api.weixin.qq.com/cgi-bin/menu/delete?access_token="
        self.createUrl = "https://api.weixin.qq.com/cgi-bin/menu/create?access_token="
        self.getMenuUri="https://api.weixin.qq.com/cgi-bin/menu/get?access_token="
    def getAccessToken(self):
        f = urllib.urlopen(self.accessUrl)
        accessT = f.read().decode("utf-8")
        jsonT = json.loads(accessT)
        return jsonT["access_token"]
    def delMenu(self, accessToken):
        html = urllib.urlopen(self.delMenuUrl + accessToken)
        result = json.loads(html.read().decode("utf-8"))
        return result["errcode"]
    def createMenu(self, accessToken):
        menu = '''{
                 "button":[
                     {    
          "type":"click",
          "name":"今日歌曲",
          "key":"V1001_TODAY_MUSIC"
      },
      {
           "type":"view",
           "name":"歌手简介",
           "url":"http://www.qq.com/"
      },
      {
           "name":"菜单",
           "sub_button":[
            {"type":"click","name":"hello word","key":"V1001_HELLO_WORLD"},{"type":"click","name":"赞一下我们","key":"V1001_GOOD"}]}]}'''
        html = urllib.urlopen(self.createUrl + accessToken, menu.encode("utf-8"))
        result = json.loads(html.read().decode("utf-8"))
        return result["errcode"]
    def getMenu(self,accessToken):
        html = urllib.urlopen(self.getMenuUri + accessToken)
        print(html.read().decode("utf-8"))
@csrf_exempt

def index(request):
    #printrequest
    if request.method == 'GET':
        
        # 检验合法性
        # 从 request 中提取基本信息 (signature, timestamp, nonce, xml)
        signature = request.GET.get('signature')
        timestamp = request.GET.get('timestamp')
        nonce = request.GET.get('nonce')
 
        if not wechat_instance.check_signature(
                signature=signature, timestamp=timestamp, nonce=nonce):
            return HttpResponseBadRequest('Verify Failed')
        #getMenu()
        return HttpResponse(
            request.GET.get('echostr', ''), content_type="text/plain")
 
 
    # 解析本次请求的 XML 数据
    try:
        # request
        wechat_instance.parse_data(data=request.body)
        
    except ParseError:
        return HttpResponseBadRequest('Invalid XML Data')
 
    # 获取解析好的微信请求信息
    message = wechat_instance.get_message()
 
    # 关注事件以及不匹配时的默认回复
    response = wechat_instance.response_text(
        content = (
            '感谢您的关注！\n回复【实时数据，手机号码，仪表出厂编号】查看TRC-III实时数据（株洲中油）以及新奥TFC的实时数据，以前的培训资料请在历史记录里查找。还可以回复任意内容开始聊天'
           
            ))
    if isinstance(message, TextMessage):
        # 当前会话内容
        content = message.content.strip()
        #print content
        if content == '功能':
            reply_text = (                  
                    ' 回复任意词语，查天气，陪聊天，讲故事，无所不能！\n'
                    
                )
        elif re.match(r'A16\d{12}$',content)or re.match(r'1\d{10}$',content):
            reply_text =get_info(content)
        elif content.endswith('实时数据'):
            reply_text =get_realdata()
        elif len(content.split())==2:
            #print content
            reply_text=get_day_report(content)
        else:
            reply_text=text_reply(content)
        
 
        response = wechat_instance.response_text(content=reply_text)
 
    return HttpResponse(response, content_type="application/xml")
# Create your views here.
