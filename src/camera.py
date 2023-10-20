#!/usr/bin/env python

import fcntl 
import os
import math
import time
import glob
import subprocess
import re
import time
import traceback
import exifread
import itertools
import gphoto2

USBDEVFS_RESET = ord('U') << (4*2) | 20

def canon_path():
    #dev_re = re.compile("Bus (\d+) Device (\d+): ID 04a9:319a Canon, Inc. EOS 7D")
    dev_re = re.compile("Bus (\d+) Device (\d+):.*Canon, Inc..*")
    output = subprocess.check_output(["lsusb"]).decode().split('\n')
    for line in output:
        m = dev_re.match(line)
        if m:
            return "/dev/bus/usb/%s/%s" % m.groups()

def reset_usb(port):
    fd = open(port, 'w')
    fcntl.ioctl(fd.fileno(), USBDEVFS_RESET)
    time.sleep(0.5)

class InterfaceWrapper(object):
    def __init__(self, obj):
        self.obj = obj

    def wrap_call(self, func):
        print(func)
        def wrapper(*args, **kw):
            result = func(*args, **kw)
            if not isinstance(result, (tuple, list)):
                error = result
            elif len(result) == 2:
                (error, result) = result
            else:
                error = result[0]
                result = result[1:]
            if type(error) is not int:
                return result
            if error >= gphoto2.GP_OK:
                return result
            #msg = '[%d] %s' % (error, gphoto2.gp_result_as_string(error))
            raise gphoto2.GPhoto2Error(error)
        return wrapper

    def __getattr__(self, name):
        if not hasattr(self.obj, name):
            name = "gp_%s" % name
        attr = getattr(self.obj, name)
        if callable(attr):
            attr = self.wrap_call(attr)
        return attr

class Camera(object):
    @classmethod
    def list_cameras(cls):
        camlist = self.api.gp_camera_autodetect()
        camlist = [it[0] for it in camlist]
        return camlist

    @property
    def api(self):
        return InterfaceWrapper(gphoto2)

    def cb_idle(self, context, data):
        print('cb_idle', data)

    def cb_error(self, context, text, data):
        print('cb_error', text, data)

    def cb_status(self, context, text, data):
        print('cb_status', text, data)

    def cb_message(self, context, text, data):
        print('cb_message', text, data)

    def cb_question(self, context, text, data):
        print('cb_question', text, data)
        return gphoto2.GP_CONTEXT_FEEDBACK_OK

    def cb_cancel(self, context, data):
        #print('cb_cancel', data)
        return gphoto2.GP_CONTEXT_FEEDBACK_OK

    def cb_progress_start(self, context, target, text, data):
        #print('cb_progress_start', target, text, data)
        self.state = "busy"
        return 123

    def cb_progress_update(self, context, id_, current, data):
        #print('cb_progress_update', id_, current, data)
        self.state = "busy"

    def cb_progress_stop(self, context, id_, data):
        #print('cb_progress_stop', id_, data)
        self.state = "idle"

    def new_context(self):
        self.callbacks = []
        context = self.api.Context()
        self.callbacks = []
        self.callbacks.append(context.set_idle_func(self.cb_idle, "idle"))
        self.callbacks.append(context.set_error_func(self.cb_error, "error"))
        self.callbacks.append(context.set_status_func(self.cb_status, "status"))
        self.callbacks.append(context.set_message_func(self.cb_message, "message"))
        self.callbacks.append(context.set_question_func(self.cb_question, "question"))
        self.callbacks.append(context.set_cancel_func(self.cb_cancel, "cancel"))
        self.callbacks.append(context.set_progress_funcs(
            self.cb_progress_start, self.cb_progress_update, self.cb_progress_stop, "progress"))
        return context

    def open(self, name=None):
        camlist = list(self.api.camera_autodetect())
        print(camlist)
        if len(camlist) == 0:
            raise ValueError("no cameras found")
        if name is None:
            addr = camlist[0][1]
        else:
            for (cam_name, cam_port) in camlist:
                if name.lower() in cam_name.lower():
                    addr = cam_port
                    break
            else:
                raise ValueError("camera with name '%s' not found" % name)
        port_info_list = self.api.PortInfoList()
        port_info_list.load()
        idx = port_info_list.lookup_path(addr)
        self.camera = self.api.Camera()
        self.camera.set_port_info(port_info_list[idx])
        self.context = self.new_context()
        self.camera.init(self.context)
        frontend = CameraFrontend(self)
        self.camera_api = InterfaceWrapper(self.camera)
        self.state = "idle"
        return frontend
    
    def wait_on(self, state, timeout=0):
        while True:
            if self.state == state:
                break
            print("waiting...")
            time.sleep(0.1)
            #break

    def __getattr__(self, name):
        def wait_on(func, state="idle", timeout=0):
            def _wrapper(*args, **kw):
                self.wait_on(state, timeout)
                return func(*args, **kw)
            return _wrapper
        obj = getattr(self.camera_api, name)
        if callable(obj):
            obj = wait_on(obj)
        return obj

class CameraFrontend(object):
    def __init__(self, camera=None):
        self.camera = camera
        self.last_image = None

    def __setitem__(self, name, value):
        cfg = self.config.lookup(name)
        cfg.value = value

    def __getitem__(self, name):
        return self.config.lookup(name).value

    @property
    def summary(self):
        return self.camera.get_summary()

    @property
    def config(self):
        widget = self.camera.get_config()
        return CameraConfig(widget, self.camera)
         
    def capture(self, copy=False, fn_target=None, prefix=""):
        file_path = self.camera.capture(gphoto2.GP_CAPTURE_IMAGE)
        if copy:
            return self.copy_file(file_path, fn_target=fn_target, prefix=prefix)
        return file_path

    def get_thumbnail(self, filename=None, refresh=False):
        filename = filename if filename != None else self.last_image
        if refresh or filename == None:
            fn = self.capture(copy=True)
            filename = fn
        with open(filename, 'rb') as fh:
            if filename.lower().endswith("cr2"):
                exif = exifread.process_file(fh)
                jpeg = exif["JPEGThumbnail"]
            else:
                jpeg = fh.read()
        return jpeg

    def walk(self, root=None):
        root = root if root != None else "/"
        dirs = [name[0] for name in self.camera.folder_list_folders(root)]
        files = [name[0] for name in self.camera.folder_list_files(root)]
        yield (root, dirs, files)
        for directory in dirs:
            new_root = os.path.join(root, directory)
            for result in self.walk(root=new_root):
                yield result

    @property
    def default_path(self):
        dirs = [os.path.join(fs[0], dirname) for fs in self.walk() for dirname in fs[1]]
        return dirs[-1]

    def reset(self):
        self._camera = None
        reset_usb(self.port)

    def list_files(self, path=None):
        path = path if path is not None else self.default_path
        res = self.camera.folder_list_files(path)
        res = [os.path.join(path, x[0]) for x in res]
        return res

    def delete_all(self, path):
        res = self.camera.folder_delete_all(path)
        return res

    def copy_file(self, file_path, fn_target=None, prefix="", stubfn=""):
        if fn_target is None:
            fn_target = file_path.name
            fn_target = os.path.splitext(fn_target)
            fn_target = fn_target[0] + stubfn + fn_target[1]
            fn_target = os.path.join(prefix, fn_target)
        print('Copying image to %s' % fn_target)
        camera_file = self.camera.file_get(file_path.folder, file_path.name, gphoto2.GP_FILE_TYPE_NORMAL)
        self.camera.api.file_save(camera_file, fn_target)
        self.last_image = fn_target
        return fn_target
    
    def download_all(self, prefix='', stubfn=''):
        pics = self.list_files()
        files = []
        for path in pics:
            (path, fn) = os.path.split(path)
            if fn.lower().endswith("cr2"):
                _type = gphoto2.GP_FILE_TYPE_RAW
            else:
                _type = gphoto2.GP_FILE_TYPE_NORMAL
            target_fn = os.path.splitext(fn)
            target_fn = target_fn[0] + stubfn + target_fn[1]
            target_fn = os.path.join(prefix, target_fn)
            camera_file = self.camera.file_get(path, fn, _type)
            self.camera.api.file_save(camera_file, target_fn)

    def dump(self, prefix='', stubfn=''):
        self.download_all(prefix=prefix, stubfn=stubfn)
        self.delete_all()

class ConfigNode(object):
    def __init__(self, config):
        self.config = config

class CameraConfig(object):
    WidgetTypes = {getattr(gphoto2, name): name for name in dir(gphoto2) if name.startswith("GP_WIDGET")}

    def __init__(self, widget, camera):
        self.widget = widget
        self.camera = camera
        self.widget_id = widget.get_id()

    def lookup(self, name):
        parts = name.split('.')
        if parts[0] == self.name:
            parts = parts[1:]
        if len(parts) == 0:
            return self
        lookup = parts[0]
        remainder = str.join('.', parts[1:])
        for child in self.children:
            if child.name == lookup:
                if remainder:
                    return child.lookup(remainder)
                return child

    def dict(self, name='', choices=False):
        if name:
            name = "%s.%s" % (name, self.name)
        else:
            name = self.name
        res = {}
        if self.type in ("GP_WIDGET_SECTION", "GP_WIDGET_MENU", "GP_WIDGET_WINDOW"):
            for child in self.children:
                res.update(child.dict(name, choices))
        else:
            if choices:
                if self.type in ("GP_WIDGET_MENU", "GP_WIDGET_RADIO"):
                    res[name] = list(self.choices)
                elif self.type == "GP_WIDGET_TOGGLE":
                    res[name] = [1, 0]
                else:
                    res[name] = self.type
            else:
                res[name] = self.value
        return res

    @property
    def count_children(self):
        return self.widget.count_children()

    @property
    def count_choices(self):
        return self.widget.count_choices()

    @property
    def id(self):
        return self.widget.get_id()

    @property
    def type(self):
        return self.WidgetTypes[self.widget.get_type()]

    @property
    def label(self):
        return self.widget.get_label()

    @property
    def name(self):
        return self.widget.get_name()

    @property
    def parent(self):
        return self.__class__(self.widget.get_parent(), self.camera)

    @property
    def root(self):
        return self.__class__(self.widget.get_root(), self.camera)

    @property
    def children(self):
        for child_idx in range(self.count_children):
            child = self.widget.get_child(child_idx)
            yield self.__class__(child, self.camera)

    @property
    def choices(self):
        for choice_idx in range(self.count_choices):
            choice = self.widget.get_choice(choice_idx)
            yield choice

    def get_value(self):
        try:
            return self.widget.get_value()
        except:
            return None
    def set_value(self, val):
        self.widget.set_value(val)
        self.set_config()
    value = property(get_value, set_value)

    def get_range(self):
        return self.widget.get_range()
    def set_range(self, val):
        self.widget.set_range(val)
    range = property(get_range, set_range)

    def get_info(self):
        return self.widget.get_info()
    def set_info(self, val):
        self.widget.set_info(val)
    info = property(get_info, set_info)

    def get_readonly(self):
        return self.widget.get_readonly()
    def set_readonly(self, val):
        self.widget.set_readonly(val)
    readonly = property(get_readonly, set_readonly)

    def set_config(self):
        self.camera.set_config(self.root.widget)
