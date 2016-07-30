#encoding=utf8
#email: jinzhu.wang@baifendian.com
from models import *
from user_auth.models import *
from Aries.settings import REST_BASE_URI
import logging
import hashlib
import subprocess
from django.contrib.auth.models import User
import traceback
import datetime,time
import os,sys,json
#from Aries.settings import HDFS_URL,HADOOP_RUN_SCRIPT,WEBHDFS_USER
from django.conf import settings
# use webhdfs rest api
from hdfs.function import HDFS
from django.http import HttpResponse
from tools import *
reload(sys)
sys.setdefaultencoding('utf-8')
hdfs_logger = logging.getLogger("hdfs_log")
StatusCode={"GET_SUCCESS":200,
             "GET_FAILED":500,
             "PUT_SUCCESS":200,
             "PUT_FAILED":500,
             "POST_SUCCESS":200,
             "POST_FAILED":500,
             "DELETE_SUCCESS":200,
             "DELETE_FAILED":500   
            }

def packageResponse(result):
    response = HttpResponse(content_type='application/json')
    response.write(json.dumps(result))
    response["Access-Control-Allow-Origin"] = "*"
    response["Access-Control-Allow-Methods"] = "POST,GET,PUT, DELETE"
    return response

def deleteshare(request,path):
    share_id = request.GET.get("share_id","")
    result  = {}
    try:
        dataShare = DataShare.objects.get(id=share_id)
        dataShare.delete()
        result["code"] = StatusCode["DELETE_SUCCESS"]
        result["data"] = "删除成功"
    except Exception,e:
        hdfs_logger.error(e)
        result["code"] = StatusCode["DELETE_FAILED"]
        result["data"] = "删除失败"
    return result

#创建分享文件（夹）
def postshare(request,path):
    result = {}
    path = os.path.realpath("/%s/%s" %(os.path.sep,path))
    space_name = request.GET.get("space_name","")
    proxy_link = hashlib.md5("%s%s%s" %(space_name,path,int(time.time()))).hexdigest()
    proxy_link = "{0}/{1}/{2}".format(settings.SHARE_PROXY_BASE_URI,"HDFS/ShowShare",proxy_link)
    hdfs_logger.info("proxy_link:{0}".format(proxy_link))
    try:
        share_user = getUser(request).username
        share_type = request.GET.get("permission", "private")
        if share_type != "public":
            share_type = "private"
        share_validity = int(request.GET.get("Validity", "10"))
        datashare = DataShare.objects.create(source_path=path,proxy_path=proxy_link, share_type=share_type, share_user=share_user, share_validity=share_validity,space_name=space_name)
        datashare.save()
        if datashare:
            result["code"]=StatusCode["GET_SUCCESS"]
            result["data"] = proxy_link
            result["proxy_link"] = proxy_link
        else:
            result["code"]=StatusCode["GET_FAILED"]
            result["data"] = "分享失败"
            result["proxy_link"] = ""
    except:
        hdfs_logger.debug(traceback.format_exc())
        result["code"]=StatusCode["GET_FAILED"]
        result["data"] = "分享失败"
    return result

#显示分享文件（夹）的信息
def getshare(request,path):
    result = {}
    space_name = request.GET.get("space_name")
    hdfs_logger.info("space_name:{0}".format(space_name))
    if space_name:
        try:
            sharelist = DataShare.objects.filter(space_name=space_name)
            result["code"] = StatusCode["GET_SUCCESS"]
            result["data"] = "OK"
            totalList = [
                            {
                                'id':share.id,
                                'source_path':share.source_path,
                                'proxy_path':share.proxy_path,
                                'share_time':share.share_time.strftime("%Y-%m-%d %H:%M:%S"),
                                'share_validity':share.share_validity,
                                'share_user':share.share_user,
                                'is_validity': 1 if time.mktime((share.share_time+datetime.timedelta(days=share.share_validity)).timetuple())> \
                                                    time.mktime(datetime.datetime.now().timetuple()) else 0,
                                'desc':share.desc
                            } for share in sharelist
                        ]
            data = {"totalList":totalList,"totalPageNum":len(totalList),"currentPage":1}
            result["data"] = data
        except:
            hdfs_logger.info(traceback.format_exc())
            result["code"]=StatusCode["GET_FAILED"]
            result["data"] = "FAILED"
    else:
        hdfs_logger.error("space_name is not exist!")
        result["code"]=StatusCode["OK"]
        result["data"] = {"totalList":[],"totalPageNum":0,"currentPage":1}
    return result

def share(request, path):
    if request.method == "POST":
        result = postshare(request, path)
    elif request.method == "DELETE":
        result = deleteshare(request,path)
    else:
        result = getshare(request, path)
    return result

#获取删除的文件（夹）信息
def get_delete(request, path):
    nowuser = getUser(request)
    result = {}
    try:
        fileOperateType = FileOperatorType.objects.get(name='delete')
        dataoperate = DataOperator.objects.filter(o_user=nowuser, o_type=fileOperateType)
        data = []
        for dp in dataoperate:
            if time.mktime((dp.o_time+datetime.timedelta(days=1)).timetuple())>time.mktime(datetime.datetime.now().timetuple()):
                dp_dict = {}
                dp_dict[u"id"] = dp.id
                dp_dict[u"source_path"] = dp.source_path
                dp_dict[u"o_time"] = datetime.datetime.strftime(dp.o_time,'%Y-%m-%d %H:%M:%S')
                data.append(dp_dict)
        result["data"] = data
        result["code"] = StatusCode["GET_SUCCESS"]
        result["data"] = "OK"
    except:
        hdfs_logger.debug(traceback.format_exc())
        result["code"] = StatusCode["GET_FAILED"]
        result["data"] = "FAILED"
    return result


#删除文件（夹）
def de_delete(request, path):
    #pass
    ac_logger.info("-----:%s" %request.GET)
    space_name = request.GET.get("spaceName",'')
    spaces = getObjByAttr(Space,"name",space_name)
    space = spaces[0]
    space_path = space.address
    exec_user = space.exec_user 
    isTrash = request.GET.get("isTrash",0)
    if isTrash != 0:
        space_path = trashPath(space_path)
    path = os.path.realpath("%s%s%s" %(os.path.sep,space_path,path))
    ac_logger.info("path:%s" %path)
    op="DELETE"
    result={}
    nowuser = getUser(request)
    exitCode,data = run_hadoop(user_name=exec_user,operator="rmr",args=[path])
    ac_logger.info("data:%s" %data)
    if exitCode != 0:
        result["code"] = StatusCode["DELETE_FAILED"]
        result["data"] = data
    else:
        o_type = FileOperatorType.objects.get(name='delete')
        fileopt = DataOperator.objects.create(source_path=path, target_path="-", o_type=o_type, o_user=nowuser.username)
        fileopt.save()
        result["code"] = StatusCode["DELETE_SUCCESS"]
        result["data"] = "删除成功!"
    return result
   

#删除文件（夹）
def delete(request, path):
    if request.method == "DELETE":
        result = de_delete(request, path)
    elif request.method == "GET":
        result = get_delete(request, path)
    else:
        result={}
        result["code"] = StatusCode["GET_FAILED"]
        result["data"] = "FAILED"
    return result

#回复文件（夹）
def recovery(request, path):
    result={}
    try:
        dataoperate = DataOperator.objects.get(source_path='/'+path)
        target_path = dataoperate.target_path
        cmd = 'sh %s %s mv %s %s'%(settings.HADOOP_RUN_SCRIPT,settings.WEBHDFS_USER,target_path,'/'+path)
        operate = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        operate.wait()
        if operate.returncode != 0:
            result["code"] = StatusCode["PUT_FAILED"]
            result["data"] = operate.stdout.readline()
            result['data']=""
            return result
        result["code"] = StatusCode["PUT_SUCCESS"]
        result["data"] = "OK"
        dataoperate.delete()
    except:
        hdfs_logger.debug(traceback.format_exc())
        result["code"] = StatusCode["PUT_FAILED"]
        result["data"] = "FAILED"
    return result

#配额回收
def capacityRecovery(request, space_name):
    result={}
    try:
        space = Space.objects.get(space_name=space_name)
        space.capacity = 0
        space.is_active = 0
        space.save()
        result["code"] = StatusCode["DELETE_SUCCESS"]
        result["data"] = "OK"
    except:
        hdfs_logger.debug(traceback.format_exc())
        result["code"] = StatusCode["DELETE_FAILED"]
        result["data"] = "FAILED"
    return result

#申请扩容
def upSet(request, path):
    result = {}
    t = getUser(request)
    try:
        body_data = json.loads(request.body)
        capacity_value = int(body_data['capacity'])
        if capacity_value > 0:
            space = Space.objects.get(address='/'+path, is_active=1)
            space.capacity = capacity_value
            space.save()
        result["code"] = StatusCode["PUT_SUCCESS"]
        result["data"] = "OK"
    except:
        hdfs_logger.debug(traceback.format_exc())
        result["code"] = StatusCode["PUT_FAILED"]
        result["data"] = "FAILED"
    return result


#===========================这里准备换成使用调用shell脚本的方式=========================================
#获取已使用容量和总容量
def sumSpace(request, path):
    result={}
    space_name = request.GET.get("space_name","")
    exec_user,space_path = getSpaceExecUserPath(space_name)
    try:
        cmd = 'sh %s %s du  %s'%(settings.HADOOP_RUN_SCRIPT,settings.WEBHDFS_USER,'/'+path)
        operate = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        operate.wait()
        if operate.returncode != 0:
            result["code"] = StatusCode["PUT_FAILED"]
            result["data"] = operate.stdout.readline()
            result['data']=""
            return result
        aready_used = int(operate.read())
        total = int(Space.objects.get(address = '/'+path).capacity)
        available = total - aready_used
        data={}
        data['remianing_capacity'] = available
        data['used_capacity'] = aready_used
        data['total_capacity'] = total
        result["code"] = StatusCode["PUT_SUCCESS"]
        result["data"] = "OK"
        result['data'] = data
    except:
        hdfs_logger.debug(traceback.format_exc())
        result["code"] = StatusCode["PUT_SUCCESS"]
        result["data"] = "OK"
    return result

#===========================这里准备换成使用调用shell脚本的方式==========================================
#移动文件夹
def renameDir(request, path):
    space_name = request.GET.get("space_name","")
    isTrash = request.GET.get("isTrash",0)
    exec_user,space_path = getSpaceExecUserPath(space_name)
    if isTrash != 0:
        space_path = trashPath(space_path)
    destination = request.GET.get('destination','')
    path = os.path.realpath("%s%s%s" % (os.path.sep,space_path,path))
    destination = os.path.realpath("%s%s%s" % (os.path.sep,space_path,destination))
    hdfs_logger.info("path:{0},destination:{1}".format(path,destination))
    result = {}
    if len(destination)>0:
        try:  
            exitCode,data = run_hadoop(user_name=exec_user,operator="mv",args=[path,destination])        
            if exitCode == 0:
                nowuser = getUser(request)
                o_type = FileOperatorType.objects.get(name='mv')
                fileopt = DataOperator.objects.create(source_path=path, target_path=destination, o_type=o_type, o_user=nowuser)
                result["code"] = StatusCode["PUT_SUCCESS"]
                result["data"] = "move finished!"
            else:
                result["code"] = StatusCode["PUT_SUCCESS"]
                result["data"] = "rename failed"
        except:
            hdfs_logger.debug(traceback.format_exc())
            result["code"] = StatusCode["PUT_FAILED"]
            result["data"] = "FAILED"
    else:
        hdfs_logger.info("用户%s的请求：目的路径不明确!"%(getUser(request)))
        result["code"] = StatusCode["PUT_FAILED"]
        result["data"] = "FAILED"

    return result

def list_status(request, path):
    path = os.path.realpath("%s%s" % (os.path.sep, path))
    hdfs = HDFS()
    return hdfs.list_status(path, request)

def list_status_tree(request,path):
    path = os.path.realpath("%s%s" % (os.path.sep, path))
    hdfs = HDFS()
    baseData = hdfs.list_status(path, request)
    #filter is_dir 1
    result = {}
    try: 
        if baseData:
            data=[{
                     "name":k["name"],
                     "isParent":"true",
                   } for k in baseData["data"]["totalList"]
                     if k["is_dir"]==1 ]
        else:
            data=[]
        hdfs_logger.info("liststatustree:%s" %data)
        result["code"] =  StatusCode["GET_SUCCESS"]
        result["data"] = data
    except Exception,e:
        hdfs_logger.error("%s" %e)
        result["code"] = StatusCode["GET_FAILED"]
        result["data"] = "data is get error"  
    return result

def make_dir(request, path):
    hdfs_logger.info("make_dir")
    path = os.path.realpath("%s%s" % (os.path.sep, path))
    hdfs = HDFS()
    return hdfs.make_dir(path, request)

def copy_file(request, path):
    path = os.path.realpath("%s%s" % (os.path.sep, path))
    hdfs = HDFS()
    return hdfs.copy_file(path, request)

def upload(request, path):
    #path = os.path.realpath("%s%s" % (os.path.sep, path))
    hdfs = HDFS()
    return hdfs.upload(path, request)

def download(request, path):
    #path = os.path.realpath("%s%s" % (os.path.sep, path))
    hdfs = HDFS()
    return hdfs.download(path, request)

def showShare(request,path):
    try:
        shareId = request.GET.get("shareId","")
        result = {}
        dataShare = DataShare.objects.filter(proxy_path__icontains=shareId)[0]
        source_path = dataShare.source_path
        space_name = dataShare.space_name
        exec_user,space_path = getSpaceExecUserPath(space_name)
        hdfs_logger.info("space_path:{0}, source_path:{1},path:{2}".format(space_path,source_path,path))
        real_path = os.path.realpath("%s/%s/%s/%s" %(os.path.sep,space_path,source_path,path))
        hdfs_logger.info("real_path:{0}".format(real_path))
        #获取对应的子列表 从分享的目录开始返回。而不是子目录
        hdfs = HDFS()
        result =  hdfs.list_status_share(real_path)
        result["data"]["space_name"] = space_name
        return result;
    except Exception,e:
        hdfs_logger.error(traceback.format_exc())
        result["code"] = StatusCode["GET_FAILED"]
        result["data"] = "share failed"
        return result

def HostStateGET(request):
    dic = req()
    result = {}
    if not dic.has_key('status'):
        all_host = []
        unhealthy_host = []
        for i in dic['items']:
            for j in i['host_components']:
                all_host.append(j['HostRoles']['host_name']) #所有主机
                if j['HostRoles']['service_name'] == 'HDFS' and j['HostRoles']['state'] == 'INSTALLED' and j['HostRoles']['component_name'] is not 'HDFS_CLIENT':
                    unhealthy_host.append(j['HostRoles']['host_name']) #不健康的主机
        healthy_host = [i for i in all_host if i not in unhealthy_host]
        a = list(set(all_host))
        result["code"] = StatusCode["GET_SUCCESS"]
        result["msg"]="OK"
        data = {}
        data["healthy"] = list(set(healthy_host))
        data["except"] = list(set(unhealthy_host))
        data["all"] = a
        result["data"] = data
    else:
        result["code"] = StatusCode["GET_FAILED"]
        result["msg"] = "error"
    ac_logger.info('result........:%s'%result)
    return result

def RelationGET(request, host_name):
    dic = req()
    relation = []
    result = {}
    allhost = []
    if not dic.has_key('status'):
        for i in dic['items']:
            for j in i['host_components']:
                allhost.append(j['HostRoles']['host_name'])
                if host_name in allhost:
                    if j['HostRoles']['service_name'] == 'HDFS' and j['HostRoles']['component_name'] is not 'HDFS_CLIENT' and j['HostRoles']['host_name'] == host_name:
                         relation.append({"component": j['HostRoles']['component_name'], "state": j['HostRoles']['state']})
                         result["code"] = StatusCode["GET_SUCCESS"]
                         result["msg"]="OK"
                         result["data"] = relation
                else:
                    result["code"] = StatusCode["GET_FAILED"]
                    result["msg"] = "Host name ERROR"
                    result["data"] = ''
    else:
        result["code"] = StatusCode["GET_FAILED"]
        result["msg"] = "error"
    ac_logger.info('result........:%s'%result)
    return result

def OperateServicePOST(request, command, params):
    import requests
    from requests.auth import HTTPBasicAuth
    result = {}
    url = 'http://172.24.3.64:8080/api/v1/clusters/hlg_ambari/requests'
    files = '{"RequestInfo":{"context":"Execute %s By Sirius","command":"ARCHIVE","parameters/path":"/%s"},"Requests/resource_filters":[{"service_name":"HDFS","component_name":"HDFS_CLIENT","hosts":"hlg3p64-lupan"}]}' %(command, params)
    r = requests.post(url, files, auth=HTTPBasicAuth('admin','admin'))
    a = eval(r.text.encode('ascii'))
    if a.has_key('Requests') and a['Requests']['status'] == 'Accepted':
        result["code"] = StatusCode["POST_SUCCESS"]
        result["msg"] = "OK"
    else:
        result["code"] = StatusCode["POST_FAILED"]
        result["msg"] = "ERROR"
    ac_logger.info('result........:%s'%result)
    return result

def OperateComponentPOST(request, host_name, component_name, operate):
    import requests
    from requests.auth import HTTPBasicAuth
    result = {}
    url = 'http://172.24.3.64:8080/api/v1/clusters/hlg_ambari/requests'
    files = '{"RequestInfo":{"command":"RESTART","context":"Restart %s via Sirius","operation_level":{"level":"HOST","cluster_name":"hlg_ambari"}}, "Requests/resource_filters":[{"service_name":"HDFS","component_name":"%s","hosts":"%s"}]}' %(component_name, component_name, host_name)
    r = requests.post(url, files, auth=HTTPBasicAuth('admin','admin'))
    a = eval(r.text.encode('ascii'))
    if a.has_key('Requests') and a['Requests']['status'] == 'Accepted':
        result["code"] = StatusCode["POST_SUCCESS"]
        result["msg"] = "OK"
    else:
        result["code"] = StatusCode["POST_FAILED"]
        result["msg"] = "ERROR"
    ac_logger.info('result........:%s'%result)
    return result
         
def OperateComponentPUT(request, host_name, component_name, operate):
    import requests
    from requests.auth import HTTPBasicAuth
    result = {}
    url = 'http://172.24.3.64:8080/api/v1/clusters/hlg_ambari/hosts/%s/host_components/%s' %(host_name, component_name)
    if operate == 'STOP':
        files = '{"RequestInfo": {"context" :"STOP %s via Sirius"}, "HostRoles": {"state": "INSTALLED"}}'%component_name
    else:
        files = '{"RequestInfo": {"context" :"START %s via Sirius"}, "HostRoles": {"state": "STARTED"}}'%component_name
    r = requests.put(url, files, auth=HTTPBasicAuth('admin','admin'))
    a = eval(r.text.encode('ascii'))
    if a.has_key('Requests') and a['Requests']['status'] == 'Accepted':
        result["code"] = StatusCode["POST_SUCCESS"]
        result["msg"] = "OK"
    else:
        result["code"] = StatusCode["POST_FAILED"]
        result["msg"] = "ERROR"
    return result

def req():
    import requests
    from requests.auth import HTTPBasicAuth
    r = requests.get('http://172.24.3.64:8080/api/v1/clusters/hlg_ambari/hosts?fields=host_components/HostRoles/state,host_components/HostRoles/service_name', auth=HTTPBasicAuth('admin', 'admin'))
    dic = eval(r.text)
    return dic

OP_DICT={
    "GET":{
        "DELETE":delete,
        "SHARE":share,
        "CAPACITYRECOVERY":capacityRecovery,
        "SUM":sumSpace,
        "LISTSTATUS": list_status,
        "DOWNLOAD": download,
        "LISTSTATUSTREE":list_status_tree,
    },
    "POST":{
        "SHARE":share,
        "CAPACITYRECOVERY":capacityRecovery,
        "UPLOAD": upload,
        "MKDIRS":make_dir,
    },
    "PUT":{
        "RECOVERY":recovery,
        "CAPACITYRECOVERY":capacityRecovery,
        "UPSET":upSet,
        "RENAME":renameDir,
        "CP": copy_file,
        "MKDIRS": make_dir,
    },
    "DELETE":{
        "DELETE":delete,
        "CAPACITYRECOVERY":capacityRecovery,
        "SHARE":share,
    }
}