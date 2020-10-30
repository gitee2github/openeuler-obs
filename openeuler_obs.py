 #/bin/env python3
# -*- encoding=utf8 -*-
"""
main script for openeuler-obs
"""
import argparse
import os
import sys
from common.log_obs import log
from core.runner import Runner


#ArgumentParser
par = argparse.ArgumentParser()
par.add_argument("-o", "--obs", default=None,
        help="Local path of obs_meta repository", required=False)
par.add_argument("-r", "--repository",
        help="gitee repository name", required=True)
par.add_argument("-b", "--branch", default="master",
        help="gitee repository branch name", required=False)
par.add_argument("-p", "--project", default=None,
        help="obs project name", required=False)
par.add_argument("-ip", "--source_server_ip", default=None,
        help="ip of obs source server machine", required=False)
par.add_argument("-sport", "--source_server_port", default=None,
        help="ip of obs source server machine", required=False)
par.add_argument("-suser", "--source_server_user", default=None,
        help="user of obs source server machine", required=False)
par.add_argument("-spwd", "--source_server_pwd", default=None,
        help="password of obs source server machine user", required=False)
par.add_argument("-guser", "--gitee_user", default=None,
        help="user of gitee", required=False)
par.add_argument("-gpwd", "--gitee_pwd", default=None,
        help="password of gitee", required=False)
par.add_argument("-c", "--check", default=False,
        help="check obs package", required=False)
args = par.parse_args()

#apply
kw = {
        "obs_meta_path": args.obs,
        "repository": args.repository,
        "branch": args.branch,
        "project": args.project,
        "source_server_ip": args.source_server_ip,
        "source_server_port": args.source_server_port,
        "source_server_user": args.source_server_user,
        "source_server_pwd": args.source_server_pwd,
        "gitee_user": args.gitee_user,
        "gitee_pwd": args.gitee_pwd,
        "check_flag": args.check
        }
log.info(kw)
run = Runner(**kw)
run.run()
