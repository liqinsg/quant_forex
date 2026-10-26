# 2. 一条命令重启低配机进程
ssh -i ~/.ssh/oracle.pem  ubuntu@10.0.0.90 "pkill -f keep_alive_and_monitor; nohup python3 ~/forex_shared/keep_alive_and_monitor.py > ~/forex_monitor.out 2>&1 &"
sleep 5
ssh -i ~/.ssh/oracle.pem  ubuntu@10.0.0.90 "tail ~/forex_monitor.out"
