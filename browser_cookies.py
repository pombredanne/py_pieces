#coding=utf-8

'''
the file shows how to get cookies from Chrome browser installed machine.

pycookiecheat 只支持 macOS linux 只支持 python3+

'''

import os


def _get_chrome_cookies_files():
  '''
  the cookies paths recorded in module browsercookie is older.
  newer Chrome's cookies is this.
  '''
  import glob
  p1 = os.getenv('APPDATA', '')
  fullpath_chrome_cookies = os.path.join(p1,r'..\Local\Google\Chrome\User Data\Profile 1\Cookies')
  for e in glob.glob(fullpath_chrome_cookies):
    yield e


def _get_chrome_cookies():
  '''
  return type is RequestsCookieJar
  on macOS, may need use authority check

  使用这个库需要修改 这个库的__init__.py
  fh = tempfile.NamedTemporaryFile(mode='wb', delete=False) # delete=False 不要关闭就删除文件
  # NamedTemporaryFile 就已经打开文件了 不要再次打开文件 会打开失败
  tmp_cookie_file = fh.name
  ...
  fh.close() # 要关闭是为了后面 sqlite 能打开

  这个库会丢到 cookie ，能在chrome中看到的cookie 到这里就看不到了

  '''
  import browsercookie
  from itertools import chain

  a = browsercookie.Chrome()
  files_old = a.find_cookie_files()
  files = chain(_get_chrome_cookies_files(), files_old)
  return browsercookie.chrome(files)
