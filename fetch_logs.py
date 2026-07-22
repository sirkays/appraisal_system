import paramiko
import sys

def main():
    host = '137.184.156.11'
    user = 'root'
    password = '@5304Kaynetwork'
    
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        client.connect(host, username=user, password=password)
        
        # Get recent gunicorn logs
        command = 'journalctl -u appraisalsystem -n 100 --no-pager'
        stdin, stdout, stderr = client.exec_command(command)
        out = stdout.read().decode()
        
        with open('server_logs.txt', 'w', encoding='utf-8') as f:
            f.write(out)
            
        print("Logs downloaded successfully to server_logs.txt")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        client.close()

if __name__ == '__main__':
    main()
