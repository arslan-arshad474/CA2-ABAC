import socket
import json
import datetime

def start_server():
    host = '127.0.0.1'
    port = 9999
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        # Avoid bind already in use error
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((host, port))
        sock.listen()
        print("ABAC Monitoring Server is running on port 9999. Listening for alerts...\n")
        
        while True:
            con, addr = sock.accept()
            data = con.recv(4096)
            if not data:
                con.close()
                continue
                
            try:
                alert_data = json.loads(data.decode())
                alert_type = alert_data.get('type')
                
                print(f"[{alert_type}]")
                print("Details Below:")
                print(f"Username: {alert_data.get('username')}")
                print(f"Email id: {alert_data.get('email')}")
                print(f"Location: {alert_data.get('location')}")
                
                if 'failed_attempts' in alert_data:
                    print(f"No. of failed attempts: {alert_data.get('failed_attempts')}")
                
                if 'account_locked' in alert_data:
                    print(f"Account locked out: {alert_data.get('account_locked')}")
                    
                if 'timestamp' in alert_data:
                    print(f"Timestamp/Failed login timestamps in real time: {alert_data.get('timestamp')}")
                    
                if alert_data.get('account_locked') == 'Yes' or 'lockout_timestamp' in alert_data:
                    ts = alert_data.get('lockout_timestamp', datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                    print(f"Account lockout time stamp: {ts}")
                    
                if alert_type == 'ALERT: ACCOUNT LOCKED - ADMIN RELEASE PENDING':
                    print("Message for Security Admin: User has been locked out from their account. Kindly wait for user to contact Security Team to release or you can proactively reach out to user to release and unlock account after verification.\n")
                
                print("-" * 50)
                
            except json.JSONDecodeError as e:
                print("Error parsing socket data:", e)
            finally:
                con.close()
                
    except OSError as e:
        print("Server error:", e)
    except KeyboardInterrupt:
        print("\nMonitor server closed.")
    finally:
        sock.close()

if __name__ == '__main__':
    print("\n - - - - ABAC TCP Monitor Server - - - - \n")
    start_server()
