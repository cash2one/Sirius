# coding:utf-8
import sys
import time
from Aries.openstack.middleware.flavor.flavor import Flavor
from Aries.openstack.middleware.login.login import Login
from Aries.openstack.middleware.vm.vm import Vm_manage, Vm_control, Vm_snap
from Aries.openstack.middleware.volume.volume import Volume
from Aries.openstack.middleware.image.image import Image
from Aries.openstack.middleware.common.common import run_in_thread
import json


def prints(msg):
    print json.dumps(msg, indent=4)


class Test_Module():
    def test_login(self):
        '''
        测试登入
        :return:
        '''
        login = Login("openstack", "baifendian2016")
        login.user_token_login()
        login.proid_login()
        login.token_login()

    def test_list_image(self):
        self.test_login()
        image = Image()
        msg = image.list()
        prints(msg)

    def test_create_volume(self):
        '''
        创建volume
        :return:
        '''
        self.test_login()
        volume = Volume()
        volume.create(10, name="test_a")

    def test_list_volume(self):
        '''
        :return:
        '''
        self.test_login()
        volume = Volume()
        msg = volume.list()
        prints(msg)

    def test_show_volume(self):
        '''
        :return:
        '''
        self.test_login()
        volume_id = ""
        volume = Volume()
        msg = volume.show_detail(volume_id)
        prints(msg)

    def test_create_flavor(self):
        '''
        :return:
        '''
        self.test_login()

    def test_list_flavor(self):
        self.test_login()
        flavor = Flavor()
        msg = flavor.list()
        prints(msg)

    def test_list_vm(self):
        self.test_login()
        vm = Vm_manage()
        msg = vm.list()
        prints(msg)

    def test_list_vm_detail(self):
        self.test_login()
        vm = Vm_manage()
        query = {"name": "ddd"}
        msg = vm.list_detail(query)
        prints(msg)

    def test_create_vm(self):
        '''
        :return:
        '''
        self.test_login()
        vm = Vm_manage()
        disk = [{"name": "disk_test2", "size": "10", "dev_name": "/dev/sdb"},
                {"name": "disk_test3", "size": "10", "dev_name": "/dev/sdc"}]
        msg = vm.create("test_zd3", "1", "222e2074-65e0-4ef2-b40e-a48e41181bce", "123456", disk)
        prints(msg)

    def test_create_vm_multiple(self):
        '''
        :return:
        '''
        self.test_login()
        vm = Vm_manage()
        disk = [{"name": "disk_test2", "size": "10", "dev_name": "/dev/sdb"},
                {"name": "disk_test3", "size": "10", "dev_name": "/dev/sdc"}]
        msg = vm.create_multiple("test_zd3", "1", "222e2074-65e0-4ef2-b40e-a48e41181bce", "123456", 3, 10, disk)
        prints(msg)

    # def test_create_image(self):
    #     self.test_login()
    #     vm_id = "abbd4d3f-3483-41b3-97eb-ee59898191cf"
    #     vm = Vm_snap(vm_id)
    #     image_name = "test_snap_1"
    #     ret = vm.create(vm_id,image_name)

    def test_create_snap(self):
        self.test_login()
        vm_id = "abbd4d3f-3483-41b3-97eb-ee59898191cf"
        vm = Vm_snap(vm_id)
        image_name = "test_snap_1"
        ret = vm.create(vm_id, image_name)

    def test_rebuild(self):
        self.test_login()
        vm_id = ""
        vm = Vm_snap(vm_id)
        image_name = ""
        ret = vm.rebuild(image_name)

    def test_getinfo_snap(self):
        self.test_login()
        vm_id = ""
        vm = Vm_snap(vm_id)
        image_name = ""
        ret = vm.getinfo_node(image_name)
        print ret

    def test_change_snap(self):
        self.test_login()
        vm_id = ""
        vm = Vm_snap(vm_id)
        image_name = ""
        image_name_new = ""
        ret = vm.change_node(image_name, image_name_new)
        print ret

    def test_del_snap(self):
        self.test_login()
        vm_id = ""
        vm = Vm_snap(vm_id)
        image_name = ""
        ret = vm.delete_node(image_name)
        print ret

    def test_vm_resize(self):
        self.test_login()
        vm_id = ""
        vm = Vm_control()
        flavor = ""
        vm.resize(vm_id,flavor)

    def test_thread(self):
        def test_t(a):
            print a
            time.sleep(a)
            return 0

        a = run_in_thread(test_t, (10,), timeout=10)
        print a

    def no_found(self):
        """
        出错返回函数
        :return:
        """
        print "not found params"


if __name__ == "__main__":
    assert sys.argv[1], "missing params"
    test_sec = "test_%s" % sys.argv[1]
    test = Test_Module()
    test.test_login()
    test_func = getattr(test, test_sec, test.no_found)
    test_func()
