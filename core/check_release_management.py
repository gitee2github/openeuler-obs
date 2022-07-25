#!/bin/env python3
# -*- encoding=utf8 -*-
#******************************************************************************
# Copyright (c) Huawei Technologies Co., Ltd. 2020-2020. All rights reserved.
# licensed under the Mulan PSL v2.
# You can use this software according to the terms and conditions of the Mulan PSL v2.
# You may obtain a copy of Mulan PSL v2 at:
#     http://license.coscl.org.cn/MulanPSL2
# THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND, EITHER EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT, MERCHANTABILITY OR FIT FOR A PARTICULAR
# PURPOSE.
# See the Mulan PSL v2 for more details.
# Author: yaokai
# Create: 2021/8/04
# ******************************************************************************
"""
check the software package for the corresponding project of thecorresponding branch of source
"""
import os
import sys
import yaml
import requests
import datetime
Now_path = os.path.join(os.path.split(os.path.realpath(__file__))[0])
sys.path.append(os.path.join(Now_path, ".."))
from common.log_obs import log
from collections import Counter
from common.common import git_repo_src

class CheckReleaseManagement(object):
    """
    The entrance check for release-management
    """
    def __init__(self, **kwargs):
        """
        kawrgs: dict,init dict by 'a': 'A' style
        prid: the pullrequest id
        meta_path: The path for obs_meta
        manage_path : The path for release_management_path
        """
        self.kwargs = kwargs
        self.prid = self.kwargs['pr_id']
        self.current_path = os.getcwd()
        self.meta_path = self.kwargs['obs_meta_path']
        self.manage_path = self.kwargs['release_management_path']
        self.giteeuser = self.kwargs['gitee_user']
        self.giteeuserpwd = self.kwargs['gitee_pwd']

    def _clean(self, pkgname):
        """
        remove the useless pkg dir
        """
        cmd = "if [ -d {0} ];then rm -rf {0} && echo 'Finish clean the {0}';fi".format(pkgname)
        rm_result = os.popen(cmd).readlines()
        log.info(rm_result)

    def _get_latest_git_repo(self, owner, pkgname):
        """
        get the latest git repo
        """
        os.chdir(self.current_path)
        rpm_url = "https://gitee.com/{0}/{1}".format(owner, pkgname)
        pkg_path = git_repo_src(rpm_url, self.giteeuser, self.giteeuserpwd)
        if pkg_path:
            log.info("{0}:{1}".format(pkgname, pkg_path))
            return pkg_path
        else:
            raise SystemExit("Error:{0} Clone-error,Please check yournet.".format(pkgname))

    def _get_repo_change_file(self, owner=None, pkgname=None, repo_path=None):
        """
        Obtain the change for latest commit
        """
        changed_file_cmd = "git diff --name-status HEAD~1 HEAD~0"
        fetch_cmd = "git fetch origin pull/%s/head:thispr" % self.prid
        checkout_cmd = "git checkout thispr"
        get_fetch = None
        if not repo_path:
            self._clean(pkgname)
            release_path = self._get_latest_git_repo(owner, pkgname)
            self.manage_path = release_path
            os.chdir(release_path)
        else:
            os.chdir(repo_path)
        for x in range(5):
            fetch_result = os.system(fetch_cmd)
            checkout_result = os.system(checkout_cmd)
            log.debug("STATUS:{0} and {1}".format(fetch_result, checkout_result))
            if fetch_result == 0 and checkout_result == 0:
                get_fetch = True
                break
            else:
                os.chdir(self.current_path)
                self._clean(pkgname)
                path_release = self._get_latest_git_repo(owner, pkgname)
                os.chdir(path_release)
                self.manage_path = os.path.join(self.current_path, pkgname)
        changed_file = os.popen(changed_file_cmd).readlines()
        if get_fetch and changed_file:
            log.info(changed_file)
            return changed_file
        else:
            raise SystemExit("Error:can not obtain the content for this commit")

    def _rollback_get_msg(self, repo_path):
        """
        rollback to last commit
        """
        os.chdir(repo_path)
        roll = os.system("git reset --hard HEAD^")
        if roll == 0:
            log.info("Already rollback to last commit")
        else:
            raise SystemExit("Error: fail to rollback to last commit")

    def _parse_commit_file(self, change_file):
        """
        get the change file for latest commit
        """
        new_file_path = []
        new_versin_file_path = []
        master_new_file_path = []
        multi_version_file_path = []
        for line in change_file:
            log.info("line:%s" % line)
            log_list = list(line.split())
            temp_log_type = log_list[0]
            if len(log_list) == 3:
                if "pckg-mgmt.yaml" in log_list[2]:
                    if 'master' in log_list[2]:
                        master_new_file_path.append(log_list[2])
                    elif 'multi_version' in log_list[2]:
                        master_new_file_path.append(log_list[2])
                    else:
                        branch_infos = log_list[2].split('/')
                        if len(branch_infos) == 3:
                            new_versin_file_path.append(log_list[2])
                        else:
                            new_file_path.append(log_list[2])
            elif len(log_list) == 2:
                if temp_log_type != "D" and "pckg-mgmt.yaml" in log_list[1]:
                    if 'master' in log_list[1]:
                        master_new_file_path.append(log_list[1])
                    elif 'multi_version' in log_list[1]:
                        master_new_file_path.append(log_list[1])
                    else:
                        branch_infos = log_list[1].split('/')
                        if len(branch_infos) == 3:
                            new_versin_file_path.append(log_list[1])
                        else:
                            new_file_path.append(log_list[1])
        if new_file_path or master_new_file_path or new_versin_file_path:
            return new_file_path,master_new_file_path,new_versin_file_path
        else:
            log.info("There are no file need to check!!!")
            sys.exit()

    def _get_yaml_msg(self, yaml_path_list, manage_path, rollback=None):
        """
        get the pkg msg in pckg-mgmt.yaml
        """
        error_pkg = {}
        error_flag = False
        if rollback == True:
            self._rollback_get_msg(manage_path)
        all_pack_msg = {}
        for yaml_path in yaml_path_list:
            file_path = os.path.join(manage_path, yaml_path)
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8')as f:
                    result = yaml.load(f, Loader=yaml.FullLoader)
                if "natural" in result['packages'].keys():
                    all_pack_msg[yaml_path] = result['packages']['natural'] + \
                            result['packages']['recycle'] + result['packages']['delete']
                else:
                    all_pack_msg[yaml_path] = result['packages']['everything']['baseos'] + \
                            result['packages']['everything']['other'] + result['packages']['epol'] + \
                            result['packages']['recycle'] + result['packages']['delete']
            else:
                all_pack_msg[yaml_path] = []
            error_pkg[yaml_path] = []
            for pkg_info in all_pack_msg[yaml_path]:
                if ' ' in pkg_info['name']:
                    error_name = pkg_info['name']
                    error_flag = True
                    error_pkg[yaml_path].append(error_name)
        if error_flag:
            log.error("as follows pkgs {0} space in name".format(error_pkg))
            raise SystemExit("ERROR: Please check yaml pkg name")
        return all_pack_msg

    def _check_rpms_integrity(self, old_pack_msg, new_pack_msg, yaml_path_list):
        """
        ensure the rpms exist in all the tags
        """
        old_pkg = {}
        new_pkg = {}
        error_pkg = {}
        log.info("rpms exists check")
        for change_file in yaml_path_list:
            old_pkg[change_file] = []
            new_pkg[change_file] = []
            for msg in old_pack_msg[change_file]:
                old_pkg[change_file].append(msg['name'])
            for msg in new_pack_msg[change_file]:
                new_pkg[change_file].append(msg['name'])
        for change_file in yaml_path_list:
            error_pkg[change_file] = []
            for pkg in old_pkg[change_file]:
                if pkg not in new_pkg[change_file]:
                    error_pkg[change_file].append(pkg)
            if not error_pkg[change_file]:
                del error_pkg[change_file]
        if error_pkg:
            log.error("May be {0} should not be delete".format(error_pkg))
            raise SystemExit("ERROR: Please check your PR")

    def _check_key_in_yaml(self, all_pack_msg, change_file):
        """
        check the key in your yaml compliance with rules
        """
        error_flag = ""
        keylist = ['branch_from', 'obs_from', 'name', 'branch_to', 'obs_to', 'date', 'change_pr']
        for change in change_file:
            log.info("{0} key check".format(change))
            for msg in all_pack_msg[change]:
                if len(msg.keys()) == 7 or len(msg.keys()) == 6:
                    for key in msg.keys():
                        if key not in keylist:
                            error_flag = True
                            log.error(msg)
                            log.error("ERROR:<<<<<<{0}:>>>>>> should not in there".format(key))
                else:
                    error_flag = True
                    log.error("Please check {0}".format(msg))
        if error_flag:
            raise SystemExit("ERROR: Please ensure the following key values in your yaml")

    def _check_date_time(self, yaml_msg, change_file):
        """
        check date and ensure the date to the same day as the commit time
        """
        error_flag = False
        date = datetime.date.today()
        today = date.day
        for change in change_file:
            log.info("{0} date check".format(change))
            for msg in yaml_msg[change]:
                yaml_date = int(msg['date'].split('-')[2])
                if today != yaml_date:
                    error_flag = True
                    log.error(msg)
                    log.error("Wrong Date: <date:{0}>!!!".format(msg['date']))
        if error_flag:
            log.error("Please set your date to the same day as the commit time!!!")
        return error_flag

    def _check_pkg_from(self, meta_path, yaml_msg, change_file, yaml_all_msg):
        """
        Detects the existence of file contents
        """
        error_flag = False
        for change in change_file:
            log.info("{0} pkg_from check".format(change))
            for msg in yaml_msg[change]:
                delete_tag = self._check_delete_tag(msg, yaml_all_msg[change])
                if delete_tag:
                    continue
                msg_path = os.path.join(meta_path, msg['branch_from'],msg['obs_from'], msg['name'])
                if not os.path.exists(msg_path):
                    yaml_key = os.path.join(msg['branch_from'],
                            msg['obs_from'], msg['name'])
                    log.error("The {0} not exist in obs_meta".format(yaml_key))
                    error_flag = True
        return error_flag

    def _check_delete_tag(self, msg, yaml_msg):
        """
        ensure the change msg in the delete
        """
        del_name = []
        del_msg = yaml_msg['packages']['delete']
        if del_msg:
            for pkg in yaml_msg['packages']['delete']:
                del_name.append(pkg['name'])
            if msg['name'] in del_name:
                return True
        return False

    def _get_allkey_msg(self, change_file, manage_path):
        """
        get all the msg in yaml
        """
        all_msg = {}
        for path in change_file:
            yaml_path = os.path.join(manage_path, path)
            with open(yaml_path, 'r', encoding='utf-8')as f:
                result = yaml.load(f, Loader=yaml.FullLoader)
            all_msg[path] = result
        return all_msg

    def _get_diff_msg(self, old_msg, new_msg, change_file_list):
        """
        Get the content of this submission
        """
        change_list = {}
        for change in change_file_list:
            change_list[change] = []
            for new in new_msg[change]:
                if new not in old_msg[change]:
                    change_list[change].append(new)
        for change in change_file_list:
            if change_list[change]:
                log.debug("Change in {0}:".format(change))
                for msg in change_list[change]:
                    log.debug(msg)
            else:
                del change_list[change]
                log.info("The are no new msg in {0}!!!".format(change))
        if change_list:
            return change_list
        else:
            log.info("The are no new msg in your yaml!!!")
            sys.exit()

    def _check_yaml_format(self, yaml_path_list, manage_path):
        """
        check the format for the yaml file
        """
        for yaml_path in yaml_path_list:
            manage_yaml_path = os.path.join(manage_path, yaml_path)
            try:
                with open(manage_yaml_path, 'r', encoding='utf-8') as f:
                    result = yaml.load(f, Loader=yaml.FullLoader)
                    log.info("{0} format check".format(yaml_path))
            except Exception as e:
                log.error("**********FORMAT ERROR***********")
                log.error("%s format bad Because:%s" % (yaml_path, e))
                raise SystemExit("May be %s has a bad format" % yaml_path)

    def _check_same_pckg(self, change_file_path, yaml_msg):
        """
        check the repeat pkg for the yaml file
        """
        all_pkg_name = {}
        for change_file in change_file_path:
            pkg_name = []
            log.info("{0} repeat pkg check".format(change_file))
            for msg in yaml_msg[change_file]:
                pkg_name.append(msg['name'])
            dict_pkg_name = dict(Counter(pkg_name))
            repeat_pkg = [key for key, value in dict_pkg_name.items() if value > 1]
            if repeat_pkg:
                all_pkg_name[change_file] = repeat_pkg
        if all_pkg_name:
            log.error("The following packages are duplicated in the YAML files")
            log.error(all_pkg_name)
            return True
        else:
            return False

    def _check_branch_msg(self, change_msg, yaml_path_list, manage_path):
        """
        check the branch msg in your commit
        """
        error_msg = {}
        branch_msg_path = os.path.join(manage_path, "valid_release_branches.yaml")
        with open(branch_msg_path, 'r', encoding='utf-8') as f:
            branch_result = yaml.load(f, Loader=yaml.FullLoader)
        for yaml_path in yaml_path_list:
            log.info("{0} branch check".format(yaml_path))
            error_msg[yaml_path] = []
            yaml_branch = yaml_path.split("/")[-2]
            for msg in change_msg[yaml_path]:
                if msg['branch_to'] == yaml_branch and \
                        msg['branch_from'] in branch_result['branch'].keys() and \
                        msg['branch_to'] in branch_result['branch'][msg['branch_from']]:
                    continue
                else:
                    error_msg[yaml_path].append(msg)
            if not error_msg[yaml_path]:
                del error_msg[yaml_path]
            else:
                log.error("Wrong branch msg in there:")
                for msg in error_msg[yaml_path]:
                    log.error(msg)
        if error_msg:
            return True
        else:
            return False

    def _ensure_delete_tags(self, change_msg, yaml_old_msg, yaml_all_msg):
        """
        verify the rpm added to delete tag exists in the previous file
        """
        del_tag_rpm = {}
        all_msg_rpm = {}
        error_flag = False
        change_file = change_msg.keys()
        for change in change_file:
            del_tag_rpm[change] = []
            all_msg_rpm[change] = []
            for msg in change_msg[change]:
                if self._check_delete_tag(msg, yaml_all_msg[change]):
                    del_tag_rpm[change].append(msg['name'])
            if not del_tag_rpm[change]:
                del del_tag_rpm[change]
            for msg in yaml_old_msg[change]:
                all_msg_rpm[change].append(msg['name'])
        if not del_tag_rpm:
            return
        log.info("The Pr contain the rpm change in delete tag for {0}".format(del_tag_rpm))
        info_dict = {}
        for change in del_tag_rpm.keys():
            info_dict[change] = []
            for rpm in del_tag_rpm[change]:
                if rpm not in all_msg_rpm[change]:
                    error_flag = True
                    info_dict[change].append(rpm)
            if not info_dict[change]:
                del info_dict[change]
        if error_flag:
            log.error("Check the delete group in the {0}!!!".format(info_dict))
            raise SystemExit("ERROR:Please check your PR")

    def _get_move_and_add(self,old_msg,new_msg):
        '''
        get master project add and delete pkgs by compare old and new
        '''
        add_infos = {}
        delete_infos = {}
        for branch,old_pkgs in old_msg.items():
            if old_pkgs:
                new_pkgs = new_msg[branch]
                old_pkgs_names = [info['name'] for info in old_pkgs]
                new_pkgs_names = [info['name'] for info in new_pkgs]
                del_names = list(set(old_pkgs_names).difference(set(new_pkgs_names)))
                add_names = list(set(new_pkgs_names).difference(set(old_pkgs_names)))
                if del_names:
                    for old in old_pkgs:
                        if old['name'] in del_names:
                            if delete_infos.get(branch,[]):
                                delete_infos[branch].append(old)
                            else:
                                delete_infos[branch] = [old]
                if add_names:
                    for new in new_pkgs:
                        if new['name'] in add_names:
                            if add_infos.get(branch,[]):
                                add_infos[branch].append(new)
                            else:
                                add_infos[branch] = [new]
            else:
                add_infos[branch] = new_msg[branch]
        return add_infos,delete_infos

    def _check_master_add_rules(self, add_infos, move_infos):
        '''
        check master add or internal move pkgs rules
        '''
        if add_infos:
            log.info("master add pkgs obs_from check")
        error_infos = {}
        error_flag = False
        for branch,pkgs in add_infos.items():
            log.info('check branch:{} add pkgs obs_from check running...'.format(branch))
            for pkg in pkgs:
                branch = branch.replace("-",":")
                if pkg['obs_from']:
                    if 'Multi-Version' in branch:
                        from_result = self._find_master_meta_path(pkg, ctype='multi-from')
                    else:
                        from_result = self._find_master_meta_path(pkg)
                    if from_result:
                        error_flag = True
                        if error_infos.get(branch,[]):
                            error_infos[branch].append(pkg)
                        else:
                            error_infos[branch] = [pkg]
                if pkg['obs_to'] != branch:
                    error_flag = True
                    log.error("pkg name:{2} Wrong obs_to: <obs_to:{0}> in <project:{1}>!!!".format(pkg['obs_to'],branch,pkg['name']))
                    if error_infos.get(branch,[]):
                        error_infos[branch].append(pkg)
                    else:
                        error_infos[branch] = [pkg]
        if error_infos:
            log.error("some errors in your commit,please check: {}".format(error_infos))
        return error_flag

    def _check_master_del_rules(self, old_msg, new_msg):
        '''
        check master delete pckg-mgmt.yaml pkgs is exist in obs_meta
        '''
        error_flag = False
        log.info("master delete pkgs check")
        for branch,old_pkgs in old_msg.items():
            new_pkgs = new_msg[branch]
            old_pkgs_names = [info['name'] for info in old_pkgs]
            new_pkgs_names = [info['name'] for info in new_pkgs]
            del_names = list(set(old_pkgs_names).difference(set(new_pkgs_names)))
            add_names = list(set(new_pkgs_names).difference(set(old_pkgs_names)))
            if add_names:
                branch_dir = os.path.join(self.meta_path, 'master')
                for root, dirs, files in os.walk(branch_dir, True):
                    for name in dirs:
                        c_path = os.path.join(root, name)
                        if name in add_names and 'bringInRely' not in c_path and 'RISC-V' not in c_path:
                            add_names.remove(name)
            if add_names:
                error_flag = True
                log.error("master branch pkg name:{} you want delete not exist in obs_meta!!!".format(add_names))
        return error_flag


    def _find_master_meta_path(self, pkg, ctype='from'):
        '''
        find obs_form or obs_to in obs_meta path
        '''
        if ctype == 'from':
            pkg_from_path = os.path.join(self.meta_path, 'master', pkg['obs_from'], pkg['name'])
            if not os.path.exists(pkg_from_path):
                yaml_key = os.path.join('master',pkg['obs_from'], pkg['name'])
                log.error("The {0} not exist in obs_meta".format(yaml_key))
                return True
            return False
        elif ctype == 'multi-from':
            if 'Multi-Version' in pkg['source_dir']:
                dir_name = '{}/{}'.format(pkg['source_dir'], pkg['obs_from'])
                pkg_from_path = os.path.join(self.meta_path, 'multi_version', dir_name, pkg['name'])
                yaml_key = os.path.join('multi_version', dir_name, pkg['name'])
            else:
                pkg_from_path = os.path.join(self.meta_path, pkg['source_dir'], pkg['obs_from'], pkg['name'])
                yaml_key = os.path.join(pkg['source_dir'], pkg['obs_from'], pkg['name'])
            if not os.path.exists(pkg_from_path):
                log.error("The {0} not exist in obs_meta".format(yaml_key))
                return True
            return False
        elif ctype == 'multi-to':
            if 'Multi-Version' in pkg['destination_dir']:
                dir_name = '{}/{}'.format(pkg['destination_dir'],pkg['obs_to'])
                pkg_to_path = os.path.join(self.meta_path, 'multi_version', dir_name, pkg['name'])
                yaml_key = os.path.join('multi_version', dir_name, pkg['name'])
            else:
                pkg_to_path = os.path.join(self.meta_path, pkg['destination_dir'], pkg['obs_to'], pkg['name'])
                yaml_key = os.path.join(pkg['destination_dir'], pkg['obs_to'], pkg['name'])
            if not os.path.exists(pkg_to_path):
                log.error("The pkg {0} you want delete not exist in obs_meta".format(yaml_key))
                return True
            return False
        else:
            pkg_to_path = os.path.join(self.meta_path, 'master', pkg['obs_to'], pkg['name'])
            yaml_key = os.path.join('master', pkg['obs_to'], pkg['name'])
            if not os.path.exists(pkg_to_path):
                log.error("The pkg {0} you want move not exist in obs_meta".format(yaml_key))
                return True
            return False

    def _check_master_move_rules(self, delete_infos):
        '''
        check master branch internal move pkgs rule
        '''
        if delete_infos:
            log.info("master internal move pkgs check")
        error_infos = {}
        error_flag = False
        for branch,pkgs in delete_infos.items():
            log.info('check branch:{} internal move pkgs running...'.format(branch))
            log.info('pkgs:{}'.format(pkgs))
            for pkg in pkgs:
                if 'Multi-Version' in branch:
                    branch = branch.replace("_",":")
                    to_result = self._find_master_meta_path(pkg, ctype='multi-to')
                else:
                    branch = branch.replace("-",":")
                    to_result = self._find_master_meta_path(pkg, ctype='to')
            if to_result:
                error_flag = True
                if error_infos.get(branch,[]):
                    error_infos[branch].append(pkg)
                else:
                    error_infos[branch] = [pkg]
        if error_infos:
            log.error("some errors in your commit,please check: {}".format(error_infos))
        return error_flag

    def _check_master_date_rules(self, infos):
        '''
        check date is today
        '''
        error_infos = {}
        error_flag = False
        date = datetime.date.today()
        today = date.day
        log.info("master pkgs date check")
        for branch,pkgs in infos.items():
            if branch != 'delete':
                log.info("check branch:{} pkgs date check running...".format(branch))
                for pkg in pkgs:
                    yaml_date = int(pkg['date'].split('-')[2])
                    if today != yaml_date:
                        error_flag = True
                        log.error(pkg)
                        log.error("Wrong Date: <date:{0}>!!!".format(pkg['date']))
                        if error_infos.get(branch,[]):
                            error_infos[branch].append(pkg)
                        else:
                            error_infos[branch] = [pkg]
        if error_infos:
            log.error("some errors in your commit,please check: {}".format(error_infos))
        return error_flag

    def _check_master_repeat(self, old_msgs, new_msgs):
        '''
        check master branch pkg duplicate
        '''
        error_flag = False
        log.info("master pkgs repeat check")
        old_pkgs = [old['name'] for old in old_msgs]
        pkgs = [new['name'] for new in new_msgs]
        seen = set()
        duplicated = set()
        for pkg in pkgs:  
            if pkg not in seen:  
                seen.add(pkg)
            else:
                duplicated.add(pkg)
        error_master_pkgs = list(set(old_pkgs).difference(set(pkgs)))
        if error_master_pkgs:
            error_flag = True
            log.error("The following {0} packages should not deleted in the master YAML files".format(error_master_pkgs))
        if duplicated:
            error_flag = True
            log.error("The following {0} packages are duplicated in the master YAML files".format(duplicated))
        if error_flag:
            raise SystemExit("ERROR: Please check your PR")

    def _check_pkg_from_new(self, meta_path, change_info):
        """
        check add pkg obs_from exist in obs_meta
        """
        correct_from_check = {}
        error_from_check = {}
        error_flag = False
        for branch,change in change_info.items():
            log.info("{} pkg obs_from check".format(branch))
            for msg in change:
                msg_path = os.path.join(meta_path, msg['source_dir'],msg['obs_from'], msg['name'])
                yaml_key = os.path.join(msg['source_dir'],msg['obs_from'], msg['name'])
                if not os.path.exists(msg_path):
                    error_from_check.setdefault(branch,[]).append(msg)
                else:
                    correct_from_check.setdefault(branch,[]).append(msg)
        return correct_from_check,error_from_check

    def _check_pkg_delete_new(self, meta_path, change_info):
        """
        check delete pkg exist in obs_meta
        """
        error_flag = False
        for branch,change in change_info.items():
            log.info("{} pkg obs_from check".format(branch))
            if change:
                pkgs = [msg['name'] for msg in change]
                log.info("The {0} exist in obs_meta dir {1} check".format(pkgs,branch))
                branch_dir = os.path.join(meta_path,branch)
                for root, dirs, files in os.walk(branch_dir, True):
                    for name in dirs:
                        c_path = os.path.join(root, name)
                        if name in pkgs and 'Bak' not in c_path:
                            pkgs.remove(name)
                if pkgs:
                    log.error("The {0} not exist in obs_meta dir {1}".format(pkgs,branch))
                    error_flag = True
        return error_flag


    def _check_pkg_parent_from(self, change_info, correct_from, error_from, add_infos):
        '''
        re-check error pkg_from and find in parent branch add
        '''
        error_flag = False
        branch_msg_path = os.path.join(self.manage_path, "valid_release_branches.yaml")
        with open(branch_msg_path, 'r', encoding='utf-8') as f:
            branch_result = yaml.load(f, Loader=yaml.FullLoader)
        all_master_add = {}
        if add_infos:
            for master_branch, master_pkgs in add_infos.items():
                master_pkgnames = [line['name'] for line in master_pkgs]
                all_master_add[master_branch] = master_pkgnames
        if error_from:
            for branch, pkgs in error_from.items():
                error_names = [pkg['name'] for pkg in pkgs]
                for pkg in pkgs:
                    master_branch_name = pkg['obs_from'].replace(":",'-')
                    if branch in branch_result['branch']['master'] and all_master_add.get(master_branch_name,''):
                        temps = all_master_add[master_branch_name]
                        if pkg['name'] in temps:
                            error_names.remove(pkg['name'])
                    else:
                        parent_branch = ''
                        for valied_parent,child_branchs in branch_result['branch'].items():
                            if branch in child_branchs:
                                parent_branch = valied_parent
                                break
                        if parent_branch:
                            if correct_from.get(parent_branch,''):
                                correct_branch_names = [line['name'] for line in correct_from[parent_branch]]
                                if pkg['name'] in correct_branch_names:
                                    error_names.remove(pkg['name'])
                                    break
                if error_names:
                    error_flag =True
                    for pkg in pkgs:
                        if pkg['name'] in error_names:
                            log.error("branch:{}:The {} not exist in obs_meta from dir {}/{}".format(branch, pkg['name'], pkg['source_dir'], pkg['obs_from']))
        return error_flag


    def _check_key_in_yaml_new(self, change_info):
        """
        check the key and brach from in your yaml compliance with rules
        """
        error_flag = False
        keylist = ['source_dir', 'obs_from', 'name', 'destination_dir', 'obs_to', 'date']
        for branch,info in change_info.items():
            if info:
                log.info("branch:{} yaml key check".format(branch))
                for msg in info:
                    if len(msg.keys()) == 7 or len(msg.keys()) == 6:
                        for key in msg.keys():
                            if key not in keylist:
                                error_flag = True
                                log.error(msg)
                                log.error("ERROR:<<<<<<{0}:>>>>>> should not in there".format(key))
                    else:
                        error_flag = True
                        log.error("Please check {0}".format(msg))
        if error_flag:
            raise SystemExit("ERROR: Please ensure the following key values in your yaml")

    def _check_valid_release_branch(self, change_info):
        """
        check the source_dir and destination_dir in your yaml compliance with rules
        """
        error_flag = False
        branch_msg_path = os.path.join(self.manage_path, "valid_release_branches.yaml")
        with open(branch_msg_path, 'r', encoding='utf-8') as f:
            branch_result = yaml.load(f, Loader=yaml.FullLoader)
        for branch,msg in change_info.items():
            log.info("{} source_dir and destination_dir valid check".format(branch))
            for pkg in msg:
                if pkg['destination_dir'] == branch and \
                        pkg['source_dir'] in branch_result['branch'].keys() and \
                        pkg['destination_dir'] in branch_result['branch'][pkg['source_dir']]:
                    continue
                else:
                    error_flag = True
                    log.error("pkg:{} souce_dir or destination_dir valid check error".format(pkg['name']))
        if error_flag:
            raise SystemExit("ERROR: Please ensure the source_dir and destination_dir adapt rules")

    def _check_pkg_date(self, change_info):
        '''
        check new version pkgs date
        '''
        error_flag = False
        date = datetime.date.today()
        today = date.day
        for branch,msg in change_info.items():
            log.info("{0} date check".format(branch))
            for pkg in msg:
                yaml_date = int(pkg['date'].split('-')[2])
                if today != yaml_date:
                    error_flag = True
                    log.error("Wrong Date: <date:{0}>!!!".format(pkg['date']))
        return error_flag


    def _ensure_delete_infos(self, del_old_msg, del_new_msg):
        '''
        check new version delete pkgs
        '''
        del_new_pkg = {}
        del_old_pkg = {}
        ensure_delete_pkg = {}
        for branch,del_new_msgs in del_new_msg.items():
            del_change_pkgs = []
            del_new_pkg[branch] = [new['name'] for new in del_new_msgs]
            del_old_pkg[branch] = [old['name'] for old in del_old_msg[branch]]
            delete_pkgs = list(set(del_new_pkg[branch]).difference(set(del_old_pkg[branch])))
            if delete_pkgs:
                for del_new in del_new_msgs:
                    if del_new['name'] in delete_pkgs:
                        del_change_pkgs.append(del_new)
                    ensure_delete_pkg[branch] = del_change_pkgs
            for branch,branch_del_pkgs in ensure_delete_pkg.items():
                if branch_del_pkgs:
                    log.info("branch:{},delete pkgs:{}".format(branch,branch_del_pkgs))
        return ensure_delete_pkg

    def _check_rpms_complete_and_repeat(self, old_msg, new_msg):
        '''
        compare with old and new yaml msg, make sure package exist
        '''
        old_pkg = {}
        new_pkg = {}
        same_pkg = {}
        error_pkg = {}
        change_infos = {}
        error_pkg_flag = False
        same_pkg_flag = False
        log.info("rpms exists and repeat check")
        for branch,new_msgs in new_msg.items():
            if old_msg.get(branch, []):
                old_pkg[branch] = []
                new_pkg[branch] = []
                same_pkg[branch] = []
                change_pkgs = []
                old_msgs = old_msg[branch]
                for old in old_msgs:
                    old_pkg[branch].append(old['name'])
                for new in new_msgs:
                    if new['name'] in new_pkg[branch]:
                        same_pkg_flag = True
                        same_pkg[branch].append(new['name'])
                    new_pkg[branch].append(new['name'])
                error_branch_pkgs = list(set(old_pkg[branch]).difference(set(new_pkg[branch])))
                if error_branch_pkgs:
                    error_pkg[branch] = error_branch_pkgs
                    error_pkg_flag = True
                add_pkgs = list(set(new_pkg[branch]).difference(set(old_pkg[branch])))
                for new in new_msgs:
                    if new['name'] in add_pkgs:
                        change_pkgs.append(new)
                change_infos[branch] = change_pkgs
            else:
                new_pkg[branch] = []
                for new in new_msgs:
                    if new['name'] in new_pkg[branch]:
                        same_pkg_flag = True
                        same_pkg[branch].append(new['name'])
                    new_pkg[branch].append(new['name'])
                change_infos[branch] = new_msgs
        for branch,pkgs in change_infos.items():
            if pkgs:
                log.info("change in:{}".format(branch))
                for pkg in pkgs:
                    log.info(pkg)
        if error_pkg_flag:
            log.error("May be {0} should not be delete".format(error_pkg))
            raise SystemExit("ERROR: Please check your PR")
        if same_pkg_flag:
            log.error("The following {0} packages are duplicated in the YAML files".format(same_pkg))
            raise SystemExit("ERROR: Please check your PR")
        return change_infos

    def _get_new_version_yaml_msg(self, yaml_path_list, manage_path,vtype='master'):
        '''
        get new version yaml msg content
        '''
        all_pack_msg = {}
        all_del_msg = {}
        for yaml_path in yaml_path_list:
            result = {}
            file_path = os.path.join(manage_path, yaml_path)
            if vtype == 'master':
                branch_infos = yaml_path.split('/')
                branch = branch_infos[1]
                if os.path.exists(file_path):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        result = yaml.load(f, Loader=yaml.FullLoader)
                        yaml_packages = [pkg for pkg in result['packages']]
                    if 'delete' in branch_infos:
                        all_del_msg[branch] = yaml_packages
                    else:
                        if all_pack_msg.get(branch,''):
                            full_packags = all_pack_msg[branch] + yaml_packages
                            all_pack_msg[branch] = full_packags
                        else:
                            all_pack_msg[branch] = yaml_packages
                else:
                    if 'delete' in branch_infos:
                        all_del_msg[branch] = []
                    else:
                        all_pack_msg[branch] = []
            else:
                branch_infos = yaml_path.split('/')
                branch = branch_infos[0]
                if 'delete' in branch_infos:
                    if os.path.exists(file_path):
                        with open(file_path, 'r', encoding='utf-8') as f:
                            result = yaml.load(f, Loader=yaml.FullLoader)
                            yaml_packages = [pkg for pkg in result['packages']]
                        all_del_msg[branch] = yaml_packages
                    else:
                        all_del_msg[branch] = []
                else:
                    if not all_pack_msg.get(branch,''):
                        all_branch_pkgs = self._get_complete_yaml_pkgs(branch)
                        if all_branch_pkgs:
                            all_pack_msg[branch] = all_branch_pkgs
        return all_pack_msg,all_del_msg

    def _get_complete_yaml_pkgs(self, branch):
        all_branch_pkgs = []
        if os.path.exists(os.path.join(self.manage_path, branch)):
            standard_dirs = os.listdir(os.path.join(self.manage_path, branch))
            for standard_dir in standard_dirs:
                file_path = os.path.join(self.manage_path, branch, standard_dir)
                if not os.path.isdir(file_path) or standard_dir == 'delete':
                    standard_dirs.remove(standard_dir)
            for c_dir in standard_dirs:
                release_path = os.path.join(self.manage_path,branch, c_dir, 'pckg-mgmt.yaml')
                if os.path.exists(release_path):
                    with open(release_path, 'r', encoding='utf-8') as f:
                        result = yaml.load(f, Loader=yaml.FullLoader)
                        all_branch_pkgs.extend(result['packages'])
        return all_branch_pkgs

    def _get_master_yaml_msg(self, path_list, manage_path):
        all_master_pkgs = []
        if path_list:
           all_master_pkgs = self._get_complete_yaml_pkgs('master')
        return all_master_pkgs

    def check_pckg_yaml(self):
        """
        check the obs_from branch_from in pckg-mgmt.yaml
        """
        change = self._get_repo_change_file('openeuler',
                'release-management', self.manage_path)
        change_file,master_change_file,new_version_change_file = self._parse_commit_file(change)
        all_change_files = [*change_file, *master_change_file, *new_version_change_file]
        self._check_yaml_format(all_change_files, self.manage_path)
        all_yaml_msg = self._get_allkey_msg(change_file, self.manage_path)
        change_yaml_msg = self._get_yaml_msg(change_file, self.manage_path)
        all_master_yaml_msg = self._get_allkey_msg(master_change_file, self.manage_path)
        master_change_yaml_msg,del_master_change_yaml_msg = self._get_new_version_yaml_msg(master_change_file, self.manage_path)
        all_master_msg = self._get_master_yaml_msg(master_change_file, self.manage_path)
        new_version_change_msg,del_new_version_change_msg = self._get_new_version_yaml_msg(new_version_change_file, self.manage_path,vtype='newversion')
        self._rollback_get_msg(self.manage_path)
        old_yaml_msg = self._get_yaml_msg(change_file, self.manage_path)
        old_master_yaml_msg,del_old_master_yaml_msg = self._get_new_version_yaml_msg(master_change_file, self.manage_path)
        old_all_master_msg = self._get_master_yaml_msg(master_change_file, self.manage_path)
        old_new_version_msg,del_old_new_version_msg = self._get_new_version_yaml_msg(new_version_change_file, self.manage_path,vtype='newversion')
        add_infos = {}
        if master_change_file:
            log.info(master_change_file)
            add_infos,move_infos= self._get_move_and_add(old_master_yaml_msg, master_change_yaml_msg)
            self._check_master_repeat(old_all_master_msg, all_master_msg)
            add_flag = self._check_master_add_rules(add_infos, move_infos)
            move_flag = self._check_master_move_rules(move_infos)
            del_flag = self._check_master_del_rules(del_old_master_yaml_msg, del_master_change_yaml_msg)
            date_flag = self._check_master_date_rules(add_infos)
            if add_flag or move_flag or date_flag or del_flag:
                raise SystemExit("Please check your commit")
        if new_version_change_file:
            log.info(new_version_change_file)
            change_infos = self._check_rpms_complete_and_repeat(old_new_version_msg, new_version_change_msg)
            change_delete_infos = self._ensure_delete_infos(del_old_new_version_msg, del_new_version_change_msg)
            self._check_key_in_yaml_new(change_infos)
            self._check_valid_release_branch(change_infos)
            date_flag = self._check_pkg_date(change_infos)
            correct_from, error_from = self._check_pkg_from_new(self.meta_path, change_infos)
            error_flag_add = self._check_pkg_parent_from(change_infos, correct_from, error_from, add_infos)
            error_flag_del = self._check_pkg_delete_new(self.meta_path, change_delete_infos)
            if error_flag_add or error_flag_del or date_flag:
                raise SystemExit("Please check your commit")
        if change_file:
            log.info(change_file)
            self._check_rpms_integrity(old_yaml_msg, change_yaml_msg, change_file)
            change_msg_list = self._get_diff_msg(old_yaml_msg, change_yaml_msg, change_file)
            self._ensure_delete_tags(change_msg_list, old_yaml_msg, all_yaml_msg)
            self._check_key_in_yaml(change_msg_list, change_file)
            error_flag1 = self._check_pkg_from(self.meta_path, change_msg_list, change_file, all_yaml_msg)
            error_flag2 = self._check_date_time(change_msg_list, change_file)
            error_flag3 = self._check_same_pckg(change_file, change_yaml_msg)
            error_flag4 = self._check_branch_msg(change_msg_list, change_file, self.manage_path)
            if error_flag1 or error_flag2 or error_flag3 or error_flag4:
                raise SystemExit("Please check your commit")

if __name__ == "__main__":
    kw = {"branch":"master",
            "gitee_user":"",
            "gitee_pwd":"",
            "pr_id":"",
            "obs_meta_path":"***",
            "release_management_path":"***"}
    check = CheckReleaseManagement(**kw)
    check.check_pckg_yaml()