#!/usr/bin/python3
#import pyshark
import os,sys,time,re
import pexpect
import requests

#tshark_path = '/opt/wireshark/wireshark-3.0.3-built/tshark'
#capture = pyshark.LiveCapture(output_file="./debug/test.pcap",interface="any",tshark_path=tshark_path)
#capture.sniff(TIMEOUT=120)

prompt = 'diag> '
cmd = 'dcomp exec gnb sh'
os.system('rm text')
ue_ip = ""

#index 
print('start sim-gnb docker')
child = pexpect.spawn(cmd)
index = child.expect(['/ #',pexpect.EOF,pexpect.TIMEOUT])
if index != 0:
    print('enter docker failure')
    child.close()
else:
    print('enter docker gnb successful!')

    #start sim gnb and kill old process
    print('run---sim-gnb -h 38412 -p 38412 -d  10.27.0.1 -n 1 -u 1 -B 65501 -a 172.24.14.9')
    child.sendline('killall sim-gnb')
    time.sleep(1)
    child.sendline('\nsim-gnb -h 38412 -p 38412 -d  10.27.0.1 -n 1 -u 1 -B 65501 -a 172.24.14.9')
    time.sleep(1)
    index1 = child.expect([' diag> create cpe raw socket success on interface:eth0',pexpect.EOF,pexpect.TIMEOUT])
    if index1 != 0:
        print('start sim-gnb cmd failure>>>')
        child.close()
    else:
        print('start sim-gnb cmd successful!')

        #set imsi
        print('set imsi 450051234000000')
        child.sendline('\nset imsi mcc 450 mnv 05 msin 1234000000')
        time.sleep(1)
        #index = child.expect(['[Ii]nvalid',pexpect.EOF,pexpect.TIMEOUT])
        index = child.expect(['[Ii]nvalid',' diag>'])
        if index == 0:
            print('set imsi failure')
            print('enter diag and check the setting')
            child.interact()
        else:
            print('set imst successful')
            time.sleep(1)

            #send ngap setup request cmd
            print('send ngap setup request and ue register')
            child.sendline('r a')
            time.sleep(5)
            index = child.expect(['diag> .',pexpect.EOF,pexpect.TIMEOUT])
            if index != 0:
                print('send ngap request failure and check the setting!')
                child.interact()
            else:
                print('send ngap request successful!')
                print('wait for time 5s.............')
                time.sleep(5)

                #send supi session pdu establishment request cmd
                print('send session pdu establishment request cmd:ule 0 0 7 1 inet1')
                child.sendline('ule 0 0 7 1 inet1')
                time.sleep(5)
                index = child.expect([' diag> .',pexpect.EOF,pexpect.TIMEOUT])
                if index != 0:
                    print('send pdu establishment request failure and check the setting!')
                    child.interact()
                else:
                    print('send pdu establishment request successful!')
                    print('wait for time 5s.............')
                    time.sleep(5)

                    child.expect(' diag> ')
                    child.buffer
                    child.sendline('show stat')
                    time.sleep(1)
                    child.expect(' diag> ')
                    time.sleep(1)
                    result=child.before
                    #result1=child.after
                    cli= result.decode(encoding='utf-8')
                    #cli1= result1.decode(encoding='utf-8')
                    print(cli)
                    child.buffer
                    #print(1)
                    #print(cli1)
                    time.sleep(3)


                    #check pdu session
                    print('check pdu session in the smfsm')
                    smfsm = os.popen("docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' root-test_smfsm_1")
                    smfsm_ip = smfsm.read().replace('\n',"")
                    supi = 'imsi-450051234000000'
                    pdu_id = 7
                    url = 'http://{}:80/mgmt/v1/session/{}/{}'.format(smfsm_ip,supi,pdu_id)
                    headers = {"Accept": "application/json","Content-type": "application/json"}
                    r = requests.get(url,headers=headers)
                    print('get '+r.url)
                    print('The options respose code is:',r.status_code)
                    if r.status_code != 200:
                        print('The response failure!')
                        print('Get pdu session failure!')
                    else:
                        pass
                        #print(r.text)
                        print(r.json())
                        with open('text','w') as f:
                            f.write(r.json())
                        #get ue ip
                        ue_ip=os.popen("awk '/ipaddr/' text | awk -F \"\\\"\" '{print $4}'").read().replace('\n',"")
                        print('>>>>>ue ip is :',ue_ip)
                        time.sleep(1)

                    #connect to upf
                    upf_login = "ssh test@172.0.5.38"
                    child_upf = pexpect.spawn(upf_login)
                    index_upf = child_upf.expect(['password: ',pexpect.EOF,pexpect.TIMEOUT])
                    if index_upf !=0:
                        print('connect to upf failure!')
                        child_upf.close()
                    else:
                        #check pfcp modify numbers
                        print('check upf pdu session information:')
                        child_upf.sendline('testcasa')
                        time.sleep(1)
                        child_upf.expect('CASA-MOBILE>')
                        time.sleep(1)
                        child_upf.sendline("page-off")
                        time.sleep(1)
                        child_upf.expect('CASA-MOBILE>')
                        time.sleep(1)
                        print('login upf successful!')

                        if ue_ip:
                            #check far
                            child_upf.buffer
                            time.sleep(1)
                            child_upf.sendline("show upf session ue-ip {} far".format(ue_ip))
                            time.sleep(1)
                            index_ue = child_upf.expect(['session not found','CASA-MOBILE>'])
                            time.sleep(1)
                            if index_ue == 0:
                                print('upf can not find the session')
                            else:
                                print(child_upf.before.decode(encoding='utf-8')) 
                                with open('text','a') as f:
                                    f.write(child_upf.before.decode(encoding='utf-8'))
                            #check pdr
                            child_upf.buffer
                            time.sleep(1)
                            child_upf.sendline("show upf session ue-ip {} pdr".format(ue_ip))
                            time.sleep(1)
                            index_ue = child_upf.expect(['session not found','CASA-MOBILE>'])
                            time.sleep(1)
                            if index_ue == 0:
                                print('upf can not find the session')
                            else:
                                print(child_upf.before.decode(encoding='utf-8')) 
                                with open('text','a') as f:
                                    f.write(child_upf.before.decode(encoding='utf-8'))
                            #check qer
                            child_upf.buffer
                            time.sleep(1)
                            child_upf.sendline("show upf session ue-ip {} qer".format(ue_ip))
                            time.sleep(1)
                            index_ue = child_upf.expect(['session not found','CASA-MOBILE>'])
                            time.sleep(1)
                            if index_ue == 0:
                                print('upf can not find the session')
                            else:
                                print(child_upf.before.decode(encoding='utf-8')) 
                                with open('text','a') as f:
                                    f.write(child_upf.before.decode(encoding='utf-8'))
                        else:
                            print('ue ip can not find from smf!')
                            time.sleep(1)


                    print("please enter string to continue!")
                    print("enter 'y' to enter sim-gnb cli!")
                    print("enter 'u' to run pdu session update!")
                    print("enter other to run release session!")
                    i = input(">>>>>please input: ")
                    print(i)
                    if i=='xterm-256colory' or i=='y':
                        child.sendline('\n')
                        child.interact()
                    elif i=='xterm-256coloru' or i=='u':
                        #send pdu session update
                        if child_upf:
                            #check pfcp modify numbers
                            print('check pfcp modify stats')
                            child_upf.sendline('show system')
                            time.sleep(1)
                            child_upf.expect('CASA-MOBILE>')
                            child_upf.buffer
                            child_upf.sendline("show upf stats pfcp msg | include SESS_MOD_RSP")
                            time.sleep(1)
                            child_upf.expect('CASA-MOBILE>')
                            cli = child_upf.before
                            num = cli.decode(encoding='utf8')
                            num_before = re.search('\d+',num,re.M)
                            print('pfcp before modify message number is:',num_before.group())
                        else:
                            pass


                        print('send pdu session update!')
                        child.sendline('ulm 0 0 7 1 inet1')
                        time.sleep(5)
                        index = child.expect(['diag> .',pexpect.EOF,pexpect.TIMEOUT])
                        if index !=0:
                            print('send pdu session update failure!')
                            child.interact()
                        else:
                            print('send pdu session update successful!')
                            print('wait for time 5s.............')
                            time.sleep(5)

                            #check pfcp modify numbers
                            if child_upf:
                                child_upf.sendline('show system')
                                time.sleep(1)
                                child_upf.expect('CASA-MOBILE>')
                                child_upf.buffer
                                child_upf.sendline("show upf stats pfcp msg | include SESS_MOD_RSP")
                                time.sleep(1)
                                child_upf.expect('CASA-MOBILE>')
                                cli1 = child_upf.before
                                num1 = cli1.decode(encoding='utf8')
                                num_after = re.search('\d+',num1,re.M)
                                print('pfcp after modify message number is:',num_after.group())

                                #juage 
                                if int(num_after.group())==int(num_before.group())+1:
                                    print('pdu session modify process successful!')
                                else:
                                    print('pdu session modify process failure!')

                                print('wait for time 5s.............')
                                time.sleep(5)
                                child_upf.close()
                            else:
                                pass


                            #go next
                            print("please enter string to continue!")
                            print("enter 'y' to enter sim-gnb cli!")
                            print("enter other to run release session!")
                            t = input(">>>>>please input: ")
                            if t=='y':
                                child.sendline('\n')
                                child.interact()
                            else:
                                #send session release
                                print('send pdu session release!')
                                child.sendline('\nuld all')
                                time.sleep(5)
                                index = child.expect(['diag> .',pexpect.EOF,pexpect.TIMEOUT])
                                if index !=0:
                                    print('send pdu session release fauilure and check the setting!')
                                    child.interact()
                                else:
                                    print('send pdu session release successful!')
                                    print('wait for time 5s.............')
                                    child.close()

                    else:
                        #send session release
                        print('send pdu session release!')
                        child.sendline('\nuld all')
                        time.sleep(5)
                        index = child.expect(['diag> .',pexpect.EOF,pexpect.TIMEOUT])
                        if index !=0:
                            print('send pdu session release fauilure and check the setting!')
                            child.interact()
                        else:
                            print('send pdu session release successful!')
                            print('wait for time 5s.............')
                            child.close()
