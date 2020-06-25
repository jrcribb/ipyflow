#!/usr/bin/env python
#
# Copyright 2017 TWO SIGMA OPEN SOURCE, LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# smacke: this was originally copied. license + copyright preserved as originally stated.
# ref: https://github.com/twosigma/beakerx/

import os
import sys
import subprocess
import signal


def kill_processes(name):
    try:
        pidlist = map(int, subprocess.check_output(['pgrep', '-f', name]).split())
    except subprocess.CalledProcessError:
        pidlist = []
    for pid in pidlist:
        os.kill(pid, signal.SIGKILL)


# create handler for Ctrl+C
def make_signal_handler(nbsafety):
    def _signal_handler(sgnl, frame):
        os.killpg(os.getpgid(nbsafety.pid), signal.SIGKILL)
        kill_processes('jupyter')
        kill_processes('webdriver')
        sys.exit(20)
    return _signal_handler


def main():
    # update environment
    subprocess.call('yarn install', shell=True)

    # start jupyter notebook
    nb_command = f'jupyter lab --no-browser --notebook-dir="{os.path.abspath("..")}" --NotebookApp.token=""'
    nbsafety = subprocess.Popen(
        nb_command,
        shell=True,
        executable="/bin/bash",
        preexec_fn=os.setsid,
        stderr=subprocess.STDOUT,
        stdout=subprocess.PIPE
    )
    # wait for notebook server to start up
    while 1:
        line = nbsafety.stdout.readline().decode('utf-8').strip()
        if not line:
            continue
        print(line)
        if 'The Jupyter Notebook is running' in line:
            break

    signal.signal(signal.SIGINT, make_signal_handler(nbsafety))
    #start webdriverio
    result = subprocess.call('yarn run test', shell=True)

    # Send the signal to all the process groups
    os.killpg(os.getpgid(nbsafety.pid), signal.SIGKILL)

    if result:
        return 20


if __name__ == '__main__':
    sys.exit(main())