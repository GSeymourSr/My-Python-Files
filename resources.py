import psutil

def list_heavy_processes():
    # List processes using more than 1% CPU
    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent']):
        if proc.info['cpu_percent'] > 1:
            print(f"PID: {proc.info['pid']}, Name: {proc.info['name']}, CPU: {proc.info['cpu_percent']}%")

if __name__ == "__main__":
    list_heavy_processes()
