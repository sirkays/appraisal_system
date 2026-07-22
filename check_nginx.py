import paramiko

def run_cmd(client, cmd):
    print(f"\n>>> {cmd}")
    stdin, stdout, stderr = client.exec_command(cmd, timeout=60)
    out = stdout.read().decode()
    err = stderr.read().decode()
    if out: print(out)
    if err: print(f"STDERR: {err}")
    return out

def main():
    host = '137.184.156.11'
    user = 'root'
    password = '@5304Kaynetwork'
    
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        client.connect(host, username=user, password=password, timeout=10)
        
        # Upload and run the reset script directly
        script = """
import os, django
os.environ['DJANGO_SETTINGS_MODULE'] = 'core.settings'
django.setup()
from accounts.models import CustomUser
users = CustomUser.objects.all()
count = 0
for user in users:
    user.set_password('pass123')
    user.save(update_fields=['password'])
    count += 1
    print(f'  ok {user.username} ({user.staff_id})')
print(f'\\nDone. Reset {count} user passwords to pass123.')
"""
        run_cmd(client, f"cd /var/www/appraisalsystem && source .venv/bin/activate && python -c \"{script.strip()}\"")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        client.close()

if __name__ == '__main__':
    main()
