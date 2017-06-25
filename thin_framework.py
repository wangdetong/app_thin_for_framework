#!/usr/bin/python
# -*- coding: UTF-8 -*-

import re
import os
import sys
import commands
import shutil

def back_to_super_dir():
	super_dir = os.path.dirname(os.getcwd())
	os.chdir(super_dir)

def filter_catogory(filename):
	return '+' not in filename

def safe_remove_path(path):
	if os.path.exists(path):
		if os.path.isfile(path):
			os.remove(path)
		else :
			shutil.rmtree(path)

def safe_rename_path(origal_path,new_path):
	if os.path.exists(origal_path):
		os.rename(origal_path,new_path)

def safe_do_shell_cmd(cmd):

	(status,info) = commands.getstatusoutput(cmd)
	if status != 0:
		safe_log('error msg:')
		safe_log('cmd:'+cmd+' status: '+str(status))
		# print 'info: '+info
	return (status,info)

def safe_log(info):
	content = ''
	if type(info) == str:
		content = info
	elif type(info) == list:
		content = '['
		for name in info:
			content = content + name + ','
		# 删除最后一个 ','
		content = content[:-1]
		content = content + ']'

	content = content + '\n'
	log_info_list.append(content)

def write_into_log():
	log_path = os.path.join(project_path,'log.txt')
	fo = open(log_path, "a+")
	fo.writelines(log_info_list)
	fo.close()

# 获得所有的 mach-o 文件，category除外
def get_mach_o_list_at_framework(fpath):
	mach_o_list = []
	filelist = os.listdir(fpath)
	for filename in filelist:
		filepath = os.path.join(fpath,filename)
		if os.path.isfile(filepath):
			re_result_list = re.findall(r'^(\w+)\.o',filename)
			if len(re_result_list) > 0:
				mach_o_list.append(re_result_list[0])
	return mach_o_list

# category 除外
def get_mach_o_filename_list_from_arch(path,one_arch_name):
	framework_name = get_framework_name_with_path(path)
	tmp_name = one_arch_name+'_count'
	cmd_split = 'lipo '+framework_name+' -thin '+one_arch_name+' -output '+tmp_name
	(status,info) = safe_do_shell_cmd(cmd_split)
	if status != 0:
		return []

	cmd_find_all_mach_o_name = 'ar -t '+tmp_name
	(status,info) = safe_do_shell_cmd(cmd_find_all_mach_o_name)
	if status != 0:
		return []
	safe_remove_path(tmp_name)
	all_names = re.findall(r'(.*).o',info) #这里包括category
	return filter(filter_catogory,all_names)

def create_new_arch_with_remove_mach_o_list(path,arch_name,remove_file_list):

	if len(remove_file_list) == 0:
		return
	remove_file_name = remove_file_list[0]

	# 确保当前操作在 *.framework 文件夹下
	os.chdir(path)
	framework_name = get_framework_name_with_path(path)
	# 2,把fat 拆成 单个架构：比如 armv7, 并生成文件夹armv7_dir
	one_arch_name = arch_name+'_'+remove_file_name
	one_arch_dir_name = one_arch_name+'_dir'
	cmd_split = 'lipo '+framework_name+' -thin '+arch_name+' -output '+one_arch_name
	(status,info) = safe_do_shell_cmd(cmd_split)

	# 确保没有改dir 不存在
	safe_remove_path(one_arch_dir_name)
	os.mkdir(one_arch_dir_name)
	shutil.move(one_arch_name,one_arch_dir_name)

	os.chdir(one_arch_dir_name)
	# 3,将armv7 拆成 mach-o集合
	cmd_arch_to_mach_o = 'ar xv '+one_arch_name
	(status,info) = safe_do_shell_cmd(cmd_arch_to_mach_o)

	# 传来的removefile 是否在 新生成的文件夹存在
	mach_o_list = get_mach_o_list_at_framework(os.getcwd())
	
	# 防止 remove_file_name 不存在，需要把上面添加的dir 删除掉
	if remove_file_name not in mach_o_list:
		back_to_super_dir()
		safe_remove_path(one_arch_dir_name)
		return

	# 4, 删除 指定的.o文件
	for filename in remove_file_list:
		safe_remove_path(filename+".o")
	
	# 5,ar 生成新的 arch
	back_to_super_dir()
	cmd_gather_to_new_arch = 'ar rcs '+one_arch_name+' '+one_arch_dir_name+'/*.o'
	(status,info) = safe_do_shell_cmd(cmd_gather_to_new_arch)
	safe_remove_path(one_arch_dir_name)

def do_one_framework(path):
	framework_name = get_framework_name_with_path(path)
	# 备份一下framework 
	framework_file = os.path.join(path,framework_name)
	backup_framework_file = os.path.join(path,framework_name+'_backup')
	if os.path.exists(backup_framework_file):
		safe_log(framework_name+':current framework have existed that has been checked')
		return
	else:
		safe_log(framework_name+':will be checked')
		shutil.copyfile(framework_file,backup_framework_file)

	# 跳转到 framework文件夹
	os.chdir(path)

	# 1,得到framework支持的架构：armv7 arm64
	cmd_arch_info = 'lipo -info '+framework_name
	(status,info) = safe_do_shell_cmd(cmd_arch_info)
	framework_support_archs = re.findall(r'(arm\w+)',info)

	all_mach_o_names = []
	if len(framework_support_archs) > 0:
		first_arch_name = framework_support_archs[0]
		all_mach_o_names = get_mach_o_filename_list_from_arch(path,first_arch_name)
	
	if len(all_mach_o_names) == 0:
		return

	can_remove_mach_o_list = []
	for remove_file_name in all_mach_o_names:
		safe_log("remove file list:")
		safe_log([remove_file_name])
		create_new_framework_with_remove_file_list(path,framework_support_archs,[remove_file_name])
		is_build_success = xcode_build()
		safe_log('xcodebuild ' + str(is_build_success))
		if is_build_success:
			# 当前.o文件可以移除
			if remove_file_name not in can_remove_mach_o_list:
				can_remove_mach_o_list.append(remove_file_name)
		else:
			# 当前.o文件不能可以移除
			if remove_file_name in can_remove_mach_o_list:
				can_remove_mach_o_list.remove(remove_file_name)

		# 由于 跳转到`xcode_build()`会 python的当前路径，这里需要跳转回来
		os.chdir(path) 

		# 恢复 backup
		safe_remove_path(framework_name)
		shutil.copyfile(framework_name+'_backup',framework_name)

	if len(can_remove_mach_o_list) == 0:
		safe_log('current framework can not be thin: '+framework_name)
	elif all_mach_o_names == can_remove_mach_o_list:
		safe_log('current framework that the project did not used: '+framework_name)
		safe_log('*************** please remove️ '+framework_name+' manually ***************')
	else:
		safe_log('current framework can be removed list:')
		safe_log(can_remove_mach_o_list)
		create_new_framework_with_remove_file_list(path,framework_support_archs,can_remove_mach_o_list)


def create_new_framework_with_remove_file_list(path,framework_support_archs,remove_file_list):

	if len(remove_file_list) == 0:
		return
	remove_file_name = remove_file_list[0]

	framework_name = get_framework_name_with_path(path)
	arch_list_str_name_for_cmd = ''
	for arch_name in framework_support_archs:
		one_arch_name = arch_name+'_'+remove_file_name
		arch_list_str_name_for_cmd = arch_list_str_name_for_cmd+' '+one_arch_name
		create_new_arch_with_remove_mach_o_list(path,arch_name,remove_file_list)

	# 6, 把所有新生成的arch 重组成framework: Test_Fra_except_Person
	new_framework_name = framework_name+'_except_'+remove_file_name
	cmd_gather_arch_to_new_framework = 'lipo -create'+arch_list_str_name_for_cmd+' -output '+new_framework_name
	(status,info) = safe_do_shell_cmd(cmd_gather_arch_to_new_framework)
	
	# 判断是否 合并为fat 成功了
	safe_remove_path(framework_name)
	if status == 0:
		safe_rename_path(new_framework_name,framework_name)

	# 7, 删除所有的新生成的 arch file
	for arch_name in framework_support_archs:
		one_arch_name = arch_name+'_'+remove_file_name
		safe_remove_path(one_arch_name)

def get_framework_name_with_path(path):
	framework_name = ''
	re_result_list = re.findall(r'/(\w+).framework',path)
	if len(re_result_list) > 0:
		framework_name = re_result_list[0]
	return framework_name

def current_dir_framework_list(path):
	result = []
	for filename in os.listdir(path):
		filepath = os.path.join(path,filename)
		if os.path.isdir(filepath):
			_dirname_list = re.findall(r'^(\w+)\.framework',filename)
			if len(_dirname_list) > 0:
				result.append(filepath)
	return result

def all_dir_framework_list(path):
	result = []
	for path,dirs,fils in os.walk(path):
		for dir in dirs:
			if dir.endswith('.framework'):
				dirpath = os.path.join(path,dir)
				result.append(dirpath)
	return result

def xcode_build():
	os.chdir(project_path)
	(status,info) = safe_do_shell_cmd('xcodebuild')
	return status == 0


# python  thin_framework.py   project_path   target_folder_path
# 		   	argv[0] 		   argv[1]		   	argv[2]   	     
# 0 : python_script_path 【必填】
# 1 : project_path 		 【必填】
# 2 : target_folder_path 【选填】需要检查 Framework的文件夹，默认为 project_path

# 全局变量
log_info_list = []
project_path = ''

if len(sys.argv) >= 2:
	project_path = sys.argv[1] 

	if len(sys.argv) > 2:
		target_folder_path = sys.argv[2]
	else:
		target_folder_path = project_path

	framework_path_list = all_dir_framework_list(target_folder_path)

	for framework in framework_path_list:
		safe_log('---  start  ---')
		do_one_framework(framework)
		safe_log('---  finished  ---')

	write_into_log()