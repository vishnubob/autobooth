#!/usr/bin/env python3
import sys, time, subprocess
import requests


class PiwigoConnector(object):
    def __init__(self, base_url, user, password, docker_container="piwigo"):
        self.base_url = base_url
        self.user = user
        self.password = password
        self.docker_container = docker_container
        
    def sync(self):
        time_start = time.time()
        response, duration = self.sync_single()
        print("Status: {}, Duration: {}".format(response.status_code, duration))
        if response.status_code == 504:
            self.wait_for_sync()
        time_end = time.time()
        print("Total Duration: {}".format(time_end - time_start))
        
    def sync_single(self):
        login_data = {}
        login_data["method"] = "pwg.session.login"
        login_data["username"] = self.user
        login_data["password"] = self.password

        session = requests.Session()
        print("Login: ...")
        login_response = session.post(self.base_url + "/ws.php?format=json", data=login_data)
        if login_response.status_code != 200:
            print(login_response)
            raise Exception("Login Failed!")
        print("Login: OK!")

        sync_data = {}
        sync_data["sync"] = "files"
        sync_data["display_info"] = 1
        sync_data["add_to_caddie"] = 1
        sync_data["privacy_level"] = 0
        sync_data["sync_meta"] = 1
        sync_data["simulate"] = 0
        sync_data["subcats-included"] = 1
        sync_data["submit"] = 1

        time_start = time.time()
        sync_response = session.post(self.base_url + "/admin.php?page=site_update&site=1", data=sync_data)
        time_end = time.time()
        session.close()
        print("Connection closed")       
        
        return sync_response, (time_end - time_start)
        
    def wait_for_sync(self, delay_time=10.0):
        command = "docker stats " + self.docker_container + " --no-stream --format \"{{.CPUPerc}}\""
        result = subprocess.check_output(command.split(" "))
        cpu_percentage = float(result[1:-3])
        while cpu_percentage > 2.0:
            print(".", end="")
            sys.stdout.flush()
            time.sleep(delay_time)
            result = subprocess.check_output(command.split(" "))
            cpu_percentage = float(result[1:-3])
        print()
        return


if __name__ == '__main__':
    base_url = "http://localhost"
    user = "admin"
    password = "admin"
    
    PiwigoConnector(base_url, user, password).sync()
