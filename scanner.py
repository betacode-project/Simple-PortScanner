# -*- coding: utf-8 -*-

import os, sys, math
import socket, ipaddress
import threading, time

CONNECTION = [] # 接続できるホストのリスト一覧 [(IP, Port, Ping), ]
RECEIVE_DATA = {} # 受信したデータ(辞書型): キー:[str(IP:Port)]

class PortScan(threading.Thread):

    def __init__(self, ip, port, timeout=2.0, send_bytes = bytes()):
        super(PortScan, self).__init__()
        self.ip = ip
        self.port = port
        self.timeout = timeout
        self.send_data = send_bytes

    # 四捨五入関数
    def new_round(self,x, d=0):
        p = 10 ** d
        return float(math.floor((x * p) + math.copysign(0.5, x)))/p

    def run(self):
        global CONNECTION
        global RECEIVE_DATA
        try:
            # ネットワークソケットの作成
            while True:
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(self.timeout)
                    break
                except:
                    time.sleep(1)

            timer_start = time.time() # 応答時間計測開始
            sock.connect((self.ip, self.port)) # 接続
            conn_time = time.time() - timer_start # 応答時間の取得

            # 接続完了
            CONNECTION.append((self.ip, self.port, self.new_round(conn_time*1000, 2)))

            sock.send(bytes(self.send_data)) # データ送信

            # データ受信
            data = bytes()
            while True:
                got_data = sock.recv(1024 * 1024)
                if len(got_data) == 0: break
                data += got_data # 取得したデータの蓄積

            # 取得したデータは、[IP:Port]のキーで辞書に登録
            RECEIVE_DATA[self.ip +':' + str(self.port)] = data.decode('utf-8')
            sock.close()

        except:
            pass

class ScanSettings(object):
    
    def __init__(self):
        self.ip_list = ()
        self.port_list = ()
        self.timeout = 2.0

    # リスト内データの重複を削除
    def remove_duplication(self, seq):
        seen = set()
        seen_add = seen.add
        return [ x for x in seq if x not in seen and not seen_add(x)]   

    # IPアドレスのリスト作成
    def set_ip_list(self, hosts):
        ip_list = []
        for sp_host in hosts.split(','):
            try:
                try:
                    # サブネットマスク一覧取得
                    for addr in ipaddress.IPv4Network(sp_host):
                        ip_list.append(str(addr))
                except:
                    ip_list.append(socket.gethostbyname(sp_host))
            except:
                pass
        self.ip_list = tuple(self.remove_duplication(ip_list))

    # ポート番号リスト作成
    def set_port_list(self, ports):
        port_list = []
        for sp_port in ports.split(','):
            hy_port = sp_port.split('-')
            hy_num = len(hy_port)

            try:
                if hy_num > 1: # ハイフンあり
                    port_list.extend(range(int(hy_port[0]), int(hy_port[hy_num - 1])))
                else: # ハイフンなし
                    port_list.append(int(hy_port[0]))
            except:
                pass

        self.port_list = tuple(sorted(self.remove_duplication(port_list)))

    # 送信データをバイト型に変換
    def set_send_data(self, data):
        self.send_data = bytes(data.replace('\\r', '\r').replace('\\n', '\n').encode('utf-8'))

    # タイムアウト設定
    def set_timeout(self, data):
        self.timeout = float(data)


if __name__ == '__main__':
    show_all = False # 受信したデータすべて表示するか
    hide = False # 受信したデータを表示するか
    scan = ScanSettings()
    i = 0
    wait = 0.001

    for argv in sys.argv:
        try:
            if (argv == '-hosts'):  scan.set_ip_list(sys.argv[i + 1]) # ホスト設定
            elif (argv == '-ports'):  scan.set_port_list(sys.argv[i + 1]) # ポート設定
            elif (argv == '-data'):  scan.set_send_data(sys.argv[i + 1]) # 送信データ設定
            elif (argv == '-time'): scan.set_timeout(sys.argv[i + 1]) # タイムアウト設定
            elif (argv == '-wait'): wait = float(sys.argv[i + 1]) # スキャン速度調整設定
            elif (argv == '--show-all'): show_all = True
            elif (argv == '--hide'): hide = True
            i += 1
        except:
            pass

    # IP/ホストが入力されていなかったら表示
    if len(scan.ip_list) == 0:
        print('\n### Simple Port Scanner Argument ###')
        print('netscan.py -hosts [SCAN_HOSTS] (-ports [SCAN_PORTS]) (--wait [WAIT_TIME])')
        print('           (-data [SEND_DATA]) (-time [SET_TIMEOUT]) (--show-all) (--hide)\n')
        sys.exit()  
    elif len(scan.port_list) == 0: # ポート指定されていなかったら、すべてのポートにする
        scan.set_port_list('0-65535')

    # ポートスキャン実行
    print('\n### Simple Port Scanner ###\n')
    try:
        for host in scan.ip_list:      
            for port in scan.port_list:
                portscan = PortScan(host, port, scan.timeout, scan.send_data)
                portscan.setDaemon(True)
                portscan.start()
                time.sleep(wait)
                sys.stdout.write('\r[*] Scanning Host: '+ host +":"+ str(port) +" "*10)
    except KeyboardInterrupt: # Ctrl+Cで強制終了
        pass
    
    portscan.join(60)

    print('\n\a')
    for data in sorted(CONNECTION):
        ip = data[0]
        port = data[1]
        ping = data[2]

        # データ表示
        print('[+] '+ ip + ':' + str(port).ljust(5, ' ') +' - '+ str(ping) +'ms: TCP/IP Open')
        
        if (hide): continue
        if (show_all):
            try:    
                # HTTPヘッダーのみ表示する 
                recv_data = RECEIVE_DATA[ip +':'+ str(port)]
                for data in recv_data.split('\n'):
                    print(data)
                print('')
            except:
                pass
        else:
            try:     
                # 全てのデータを表示する
                recv_data = RECEIVE_DATA[ip +':'+ str(port)]
                for data in recv_data[0:recv_data.find('\r\n\r\n')].split('\n'):
                    print('... '+ data)
                print('')
            except:
                pass